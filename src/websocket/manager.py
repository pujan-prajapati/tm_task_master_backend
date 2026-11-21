from fastapi import WebSocket


class ConnectionManager:

    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}

    # Connect a user (supports multiple devices)
    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = []

        self.active_connections[user_id].append(websocket)

    # Disconnect a specific WebSocket connection
    def disconnect(self, user_id: int, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)

            # Remove user if no connections remain
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    # Send a message to all connections of a specific user
    async def send_to_user(self, user_id: int, message: dict):
        connections = self.active_connections.get(user_id, [])

        for websocket in connections:
            await websocket.send_json(message)

    # Broadcast a message to all connected users
    async def broadcast(self, message: dict):
        for connections in self.active_connections.values():
            for websocket in connections:
                await websocket.send_json(message)


manager = ConnectionManager()
