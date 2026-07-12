from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi import Query
from sqlalchemy.orm import Session
import json

from app.database import get_db
from app.core.config import settings
from app.core.security import decode_token
from app.models.user import User
from app.models.medical_record import MedicalRecord
from app.services.realtime_voice_service import RealtimeTranscriber

router = APIRouter()


def get_user_from_token(token: str, db: Session) -> User:
    """WebSocket mein JWT verify karo"""
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        user    = db.query(User).filter(User.id == user_id).first()
        if not user or user.role != "doctor":
            return None
        return user
    except:
        return None


# ── WebSocket /api/voice/stream ─────────────────────────────
@router.websocket("/stream")
async def voice_stream(
    websocket: WebSocket,
    token:     str     = Query(...),  # JWT token URL mein
    db:        Session = Depends(get_db)
):
    """
    Real-time voice streaming endpoint

    Frontend se:
    1. WebSocket connect karo: ws://localhost:8000/api/voice/stream?token=JWT
    2. Audio chunks bhejo (ArrayBuffer)
    3. Text receive karo real-time
    4. "stop" message bhejo → final text milega

    Backend:
    - Audio chunks AssemblyAI ko forward karta hai
    - Partial text wapas bhejta hai (live)
    - Final text wapas bhejta hai (confirmed)
    """

    # Token verify karo
    user = get_user_from_token(token, db)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    await websocket.send_json({
        "type":    "connected",
        "message": "Voice streaming started. Speak now..."
    })

    # Text store karne ke liye
    partial_text = {"text": ""}
    final_parts  = []

    # Callbacks
    async def on_partial(text: str):
        """Live preview — typing effect"""
        partial_text["text"] = text
        try:
            await websocket.send_json({
                "type": "partial",
                "text": text
            })
        except:
            pass

    async def on_final(text: str):
        """Confirmed text"""
        final_parts.append(text)
        try:
            await websocket.send_json({
                "type": "final",
                "text": text,
                "full": " ".join(final_parts)
            })
        except:
            pass

    async def on_error(error: str):
        try:
            await websocket.send_json({
                "type":    "error",
                "message": error
            })
        except:
            pass

    # Sync wrappers for callbacks
    import asyncio
    loop = asyncio.get_event_loop()

    def sync_partial(text):
        loop.call_soon_threadsafe(
            loop.create_task,
            on_partial(text)
        )

    def sync_final(text):
        final_parts.append(text)
        loop.call_soon_threadsafe(
            loop.create_task,
            on_final(text)
        )

    def sync_error(error):
        loop.call_soon_threadsafe(
            loop.create_task,
            on_error(error)
        )

    # Transcriber start karo
    transcriber = RealtimeTranscriber(
        on_text_callback=sync_partial,
        on_final_callback=sync_final,
        on_error_callback=sync_error
    )

    try:
        transcriber.start()

        while True:
            # Frontend se message/audio receive karo
            data = await websocket.receive()

            # Text message
            if "text" in data:
                msg = data["text"]

                if msg == "stop":
                    # Recording stop karo
                    full_transcript = transcriber.stop()
                    await websocket.send_json({
                        "type":       "completed",
                        "transcript": full_transcript,
                        "message":    "Recording complete. Ready to save."
                    })
                    break

            # Binary audio chunk
            elif "bytes" in data:
                audio_chunk = data["bytes"]
                transcriber.send_audio(audio_chunk)

    except WebSocketDisconnect:
        transcriber.stop()
        print(f"Doctor {user.full_name} disconnected")

    except Exception as e:
        await websocket.send_json({
            "type":    "error",
            "message": str(e)
        })
        transcriber.stop()


# ── POST /api/voice/save ────────────────────────────────────
@router.post("/save")
def save_transcript_to_record(
    record_id:  str,
    transcript: str,
    field:      str = "symptoms",  # symptoms ya diagnosis ya notes
    token:      str = Query(...),
    db:         Session = Depends(get_db)
):
    """
    Transcribed text ko medical record mein save karo

    field options:
    - symptoms   → symptoms column mein save
    - diagnosis  → diagnosis column mein save
    - notes      → notes (appointment) mein save
    """
    from uuid import UUID
    from app.models.doctor import Doctor

    user = get_user_from_token(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    record = db.query(MedicalRecord).filter(
        MedicalRecord.id        == UUID(record_id),
        MedicalRecord.doctor_id == doctor.id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    # Field mein save karo
    if field == "symptoms":
        record.symptoms = transcript
    elif field == "diagnosis":
        record.diagnosis = transcript
    else:
        raise HTTPException(status_code=400, detail="field must be 'symptoms' or 'diagnosis'")

    db.commit()
    return {"message": f"{field} saved successfully", "text": transcript}