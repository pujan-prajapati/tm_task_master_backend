import httpx
from fastapi import APIRouter, Cookie, Header, HTTPException, Response
from src.modules.auth_service import auth_client

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register")
async def register_user(user_data: dict):
    try:
        return await auth_client.register_user(user_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login_user(credentials: dict, response: Response):
    try:
        data, refresh_token = await auth_client.login_user(credentials)

        response.set_cookie(
            key="refreshToken",
            value=refresh_token,
            httponly=True,
            secure=False,
            samesite="strict",
            max_age=7 * 24 * 60 * 60,
        )

        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh-token")
async def refresh_token(
    response: Response, refresh_token: str = Cookie(None, alias="refreshToken")
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token not found")

    try:
        data, new_refresh_token = await auth_client.refresh_access_token(refresh_token)

        response.set_cookie(
            key="refreshToken",
            value=new_refresh_token,
            httponly=True,
            secure=False,
            samesite="strict",
            max_age=7 * 24 * 60 * 60,
        )

        return data

    except httpx.HTTPStatusError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")


@router.get("/get-user-profile")
async def get_user_profile(authorization: str = Header(...)):
    try:
        token = authorization.replace("Bearer ", "")
        return await auth_client.get_user_profile(token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
