import asyncio
import json
import redis.asyncio as redis

from app.ws.manager import manager
from app.core.config import settings


async def listen_for_notifications():

    print("🚀 Redis notification listener starting...")
    print("🔴 Redis URL:", settings.REDIS_URL)

    r = None
    pubsub = None

    try:

        r = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )

        pubsub = r.pubsub()

        await pubsub.subscribe("notifications")

        print("✅ Subscribed to Redis channel: notifications")

        async for message in pubsub.listen():

            print("📨 RAW REDIS MESSAGE:", message)

            if message["type"] != "message":
                continue

            try:

                print("📥 Redis notification received")

                data = json.loads(message["data"])

                user_id = str(data["user_id"])

                print("👤 Target user:", user_id)
                print("📝 Notification:", data.get("title"))

                await manager.send_to_user(
                    user_id,
                    data
                )

                print(
                    "📤 Notification forwarded to WebSocket manager"
                )

            except json.JSONDecodeError as error:

                print(
                    "❌ Invalid notification JSON:",
                    error
                )

            except Exception as error:

                print(
                    "❌ Notification processing error:",
                    error
                )

    except asyncio.CancelledError:

        print("🛑 Redis listener cancelled")

        raise

    except Exception as error:

        print(
            "❌ Redis listener error:",
            error
        )

    finally:

        print("🧹 Closing Redis listener...")

        if pubsub:
            try:
                await pubsub.aclose()
            except Exception as error:
                print(
                    "❌ PubSub close error:",
                    error
                )

        if r:
            try:
                await r.aclose()
            except Exception as error:
                print(
                    "❌ Redis close error:",
                    error
                )

        print("✅ Redis listener cleanup complete")