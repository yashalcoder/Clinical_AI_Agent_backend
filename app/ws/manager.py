from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()

        user_id = str(user_id)

        self.active_connections.setdefault(user_id, []).append(websocket)

        print(
            f"🔌 WebSocket connected | user_id={user_id} | "
            f"connections={len(self.active_connections[user_id])}"
        )

        print(
            "👥 Active WebSocket users:",
            list(self.active_connections.keys())
        )

    def disconnect(self, user_id: str, websocket: WebSocket):
        user_id = str(user_id)

        connections = self.active_connections.get(user_id, [])

        if websocket in connections:
            connections.remove(websocket)

        if not connections:
            self.active_connections.pop(user_id, None)

        print(f"❌ WebSocket disconnected | user_id={user_id}")

    async def send_to_user(self, user_id: str, message: dict):
        user_id = str(user_id)

        connections = self.active_connections.get(user_id, [])

        print(
            f"📨 Sending notification | user_id={user_id} | "
            f"active_connections={len(connections)}"
        )

        if not connections:
            print(
                f"⚠️ NO ACTIVE WEBSOCKET for user_id={user_id}"
            )
            print(
                "👥 Currently connected users:",
                list(self.active_connections.keys())
            )
            return

        for ws in connections.copy():
            try:
                await ws.send_json(message)

                print(
                    f"✅ Notification sent to user_id={user_id}"
                )

            except Exception as error:
                print(
                    f"❌ Failed to send notification "
                    f"to user_id={user_id}: {error}"
                )
                self.disconnect(user_id, ws)


manager = ConnectionManager()