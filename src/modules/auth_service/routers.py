import httpx
from fastapi import APIRouter, Cookie, Header, HTTPException, Response
from src.modules.auth_service import auth_client

from src.modules.auth_service.helpers import handle_auth_service_error

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register")
async def register_user(user_data: dict):
    try:
        return await auth_client.register_user(user_data)
    except httpx.HTTPStatusError as exc:
        handle_auth_service_error(exc, "User registration failed")
    except httpx.RequestError:
        raise HTTPException(
            status_code=503, detail="Authentication service unavailable"
        )


@router.post("/login")
async def login_user(credentials: dict, response: Response):
    try:
        data, set_cookie_headers = await auth_client.login_user(credentials)

        for cookie in set_cookie_headers:
            response.headers.append("Set-Cookie", cookie)

        return data

    except httpx.HTTPStatusError as exc:
        handle_auth_service_error(exc, "Login failed")
    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Authentication service unavailable",
        )


@router.post("/refresh-token")
async def refresh_token(
    response: Response,
    refresh_token: str = Cookie(None, alias="refreshToken"),
):
    if not refresh_token:
        raise HTTPException(
            status_code=401,
            detail="Refresh token not found",
        )

    try:
        data, set_cookie_headers = await auth_client.refresh_access_token(refresh_token)

        for cookie in set_cookie_headers:
            response.headers.append("Set-Cookie", cookie)

        return data

    except httpx.HTTPStatusError as exc:
        handle_auth_service_error(exc, "Invalid or expired refresh token")
    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Authentication service unavailable",
        )


@router.get("/get-user-profile")
async def get_user_profile(authorization: str = Header(...)):
    try:
        token = authorization.replace("Bearer ", "")
        return await auth_client.get_user_profile(token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
