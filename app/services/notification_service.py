import redis
import json

from sqlalchemy.orm import Session

from app.models.Notification import Notification
from app.core.config import settings


def notify(
    user_id: str,
    type: str,
    title: str,
    body: str,
    link: str,
    db: Session,
    clinic_id=None,
):
    print("\n🔔 ===== NOTIFY CALLED =====")
    print(f"👤 user_id: {user_id}")
    print(f"📌 type: {type}")
    print(f"📝 title: {title}")

    # 1. Create notification
    notif = Notification(
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        link=link,
        clinic_id=clinic_id,
    )

    # 2. Save notification
    db.add(notif)
    db.flush()
    db.refresh(notif)

    print(f"💾 Notification created: {notif.id}")

    payload = {
        "id": str(notif.id),
        "user_id": str(notif.user_id),
        "type": notif.type,
        "title": notif.title,
        "body": notif.body,
        "link": notif.link,
        "clinic_id": notif.clinic_id,
        "is_read": notif.is_read,
        "created_at": (
            notif.created_at.isoformat()
            if notif.created_at
            else None
        ),
    }

    print("📦 Redis payload:")
    print(payload)

    try:
        r = redis.from_url(settings.REDIS_URL)

        print(f"🔴 Publishing to Redis: {settings.REDIS_URL}")

        result = r.publish(
            "notifications",
            json.dumps(payload),
        )

        print(f"📡 Redis publish result: {result}")

        r.close()

    except Exception as e:
        print(f"❌ REDIS ERROR: {e}")

    print("🔔 ===== NOTIFY FINISHED =====\n")