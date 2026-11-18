import httpx
from fastapi import HTTPException


def handle_auth_service_error(
    exc: httpx.HTTPStatusError,
    default_message: str,
):
    try:
        body = exc.response.json()

        if isinstance(body, dict):
            detail = body.get("message") or default_message
        else:
            detail = default_message

    except ValueError, TypeError:
        detail = default_message

    raise HTTPException(
        status_code=exc.response.status_code,
        detail=detail,
    )
