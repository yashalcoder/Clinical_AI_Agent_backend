import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import text

from app.database import SessionLocal
from app.models.reminder import Reminder, ReminderStatus
from app.tasks.reminder_tasks import send_reminder_task

logger = logging.getLogger(__name__)

BATCH_SIZE = 50
TICK_INTERVAL_SECONDS = 30


def dispatch_due_reminders():
    """
    Runs every TICK_INTERVAL_SECONDS.

    1. Finds pending reminders that are due, using FOR UPDATE SKIP LOCKED so
       that if this ever runs from more than one process, each reminder is
       only claimed by exactly one of them.
    2. Marks the claimed rows as 'queued'.
    3. Hands each one off to Celery via Redis.
    """
    db = SessionLocal()
    try:
        due_rows = db.execute(
            text("""
                SELECT id FROM reminders
                WHERE status = :pending_status
                  AND scheduled_at <= :now
                FOR UPDATE SKIP LOCKED
                LIMIT :batch_size
            """),
            {
                "pending_status": ReminderStatus.pending.value,
                "now": datetime.now(timezone.utc),
                "batch_size": BATCH_SIZE,
            },
        ).fetchall()

        if not due_rows:
            db.commit()
            return

        reminder_ids = [row[0] for row in due_rows]

        db.query(Reminder).filter(Reminder.id.in_(reminder_ids)).update(
            {"status": ReminderStatus.queued}, synchronize_session=False
        )
        db.commit()

        for reminder_id in reminder_ids:
            send_reminder_task.delay(str(reminder_id))

        logger.info(f"Dispatched {len(reminder_ids)} reminder(s) to Celery.")

    except Exception as e:
        db.rollback()
        logger.error(f"Scheduler tick failed: {e}")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        dispatch_due_reminders,
        "interval",
        seconds=TICK_INTERVAL_SECONDS,
        id="dispatch_due_reminders",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Reminder scheduler started.")
    return scheduler