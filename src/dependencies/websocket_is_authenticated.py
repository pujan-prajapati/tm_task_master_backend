from fastapi import WebSocket, WebSocketException, status
import httpx

from src.modules.auth_service import auth_client


# ===================== WEBSOCKET IS AUTHENTICATED =======================================
async def websocket_is_authenticated(websocket: WebSocket):
    token = websocket.query_params.get("token")

    if not token:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication token is missing",
        )

    try:
        user_response = await auth_client.get_user_profile(token)
        user = user_response["data"]

        return user["id"]

    except httpx.HTTPStatusError as error:
        if error.response.status_code in (401, 403):
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid or expired authentication token",
            )

        raise WebSocketException(
            code=status.WS_1011_INTERNAL_ERROR,
            reason="Authentication service error",
        )

    except httpx.RequestError:
        raise WebSocketException(
            code=status.WS_1011_INTERNAL_ERROR,
            reason="Authentication service unavailable",
        )
