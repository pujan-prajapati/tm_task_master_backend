from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.dependencies.websocket_is_authenticated import websocket_is_authenticated
from src.websocket.manager import manager

websocket_routes = APIRouter(prefix="/ws", tags=["WebSockets"])


@websocket_routes.websocket("/notifications")
async def websocket_notifications(websocket: WebSocket):
    try:
        user_id = await websocket_is_authenticated(websocket)

    except Exception:
        await websocket.close(code=1008)
        return

    await manager.connect(user_id, websocket)

    try:
        while True:
            message = await websocket.receive_text()

            await manager.send_to_user(
                user_id=user_id, message=f"User {user_id} received: {message}"
            )

    except WebSocketDisconnect:
        manager.disconnect(user_id)
