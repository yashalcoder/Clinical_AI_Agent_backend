from datetime import datetime, timezone
import logging

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.reminder import Reminder, ReminderStatus
from app.services.reminder_service import build_reminder_payload
from app.services.whatsapp_service import get_whatsapp_service

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_reminder_task(self, reminder_id: str):
    db = SessionLocal()
    try:
        reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()

        if not reminder:
            logger.warning(f"Reminder {reminder_id} not found — skipping.")
            return

        # Safety check: only process reminders the scheduler actually claimed.
        # Prevents double-processing if a task somehow gets dispatched twice.
        if reminder.status != ReminderStatus.queued:
            logger.info(
                f"Reminder {reminder_id} is not queued (status={reminder.status}) — skipping."
            )
            return

        reminder.status = ReminderStatus.processing
        db.commit()

        try:
            phone, template_name, params = build_reminder_payload(reminder)
        except Exception as e:
            reminder.status = ReminderStatus.failed
            reminder.error_message = f"Failed to build message: {e}"
            reminder.attempt_count += 1
            db.commit()
            logger.error(f"Reminder {reminder_id} payload build failed: {e}")
            return

        result = get_whatsapp_service().send(phone, template_name, params)
        reminder.attempt_count += 1

        if result["success"]:
            reminder.status = ReminderStatus.sent
            reminder.sent_at = datetime.now(timezone.utc)
            reminder.provider_message_id = result["provider_message_id"]
            db.commit()
            logger.info(f"Reminder {reminder_id} sent successfully.")
        else:
            reminder.status = ReminderStatus.failed
            reminder.error_message = result["error"]
            db.commit()
            logger.warning(f"Reminder {reminder_id} failed: {result['error']}")

            if self.request.retries < self.max_retries:
                raise self.retry(exc=Exception(result["error"]))

    finally:
        db.close() 