# app/routes/ws_notifications.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.security import decode_token  # aapka existing JWT decode function
from app.ws.manager import manager

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.Notification import Notification
from app.core.security import get_current_user

router = APIRouter()
@router.websocket("/ws/notifications")
async def notifications_ws(
    websocket: WebSocket,
    token: str = Query(...)
):
    user = decode_token(token)

    if not user:
        await websocket.close(code=4001)
        return

    user_id = user.get("sub")

    if not user_id:
        await websocket.close(code=4001)
        return

    await manager.connect(str(user_id), websocket)

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(str(user_id), websocket)
# app/routes/notifications.py



def serialize_notification(notification: Notification):
    return {
        "id": str(notification.id),
        "user_id": str(notification.user_id),
        "clinic_id": notification.clinic_id,
        "type": notification.type,
        "title": notification.title,
        "body": notification.body,
        "link": notification.link,
        "is_read": notification.is_read,
        "created_at": (
            notification.created_at.isoformat()
            if notification.created_at
            else None
        ),
    }


# -----------------------------------
# GET: Current user's notifications
# -----------------------------------
@router.get("/")
def get_notifications(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(100)
        .all()
    )

    unread_count = sum(
        1 for notification in notifications
        if not notification.is_read
    )

    return {
        "notifications": [
            serialize_notification(notification)
            for notification in notifications
        ],
        "unread_count": unread_count,
    }


# -----------------------------------
# PATCH: Mark one notification read
# -----------------------------------
@router.patch("/{notification_id}/read")
def mark_notification_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
        .first()
    )

    if not notification:
        raise HTTPException(
            status_code=404,
            detail="Notification not found",
        )

    notification.is_read = True
    db.commit()
    db.refresh(notification)

    return {
        "message": "Notification marked as read",
        "notification": serialize_notification(notification),
    }


# -----------------------------------
# PATCH: Mark all notifications read
# -----------------------------------
@router.patch("/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).update(
        {Notification.is_read: True},
        synchronize_session=False,
    )

    db.commit()

    return {
        "message": "All notifications marked as read",
    }