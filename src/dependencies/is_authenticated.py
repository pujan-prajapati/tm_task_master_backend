from fastapi import Request, HTTPException, status, Depends
import httpx

from src.modules.auth_service import auth_client


async def get_current_user(request: Request) -> dict:
    authorization = request.headers.get("Authorization")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )

    token = authorization.removeprefix("Bearer ").strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token is missing",
        )

    try:
        response = await auth_client.get_user_profile(token)
        user = response["data"]

        if not isinstance(user, dict) or not isinstance(user.get("id"), int):
            raise ValueError("Invalid user profile")

        return user

    except httpx.HTTPStatusError as error:
        if error.response.status_code in (401, 403):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token",
            )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service error",
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    except KeyError, TypeError, ValueError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid response from authentication service",
        )


async def is_authenticated(
    user: dict = Depends(get_current_user),
) -> int:
    return user["id"]
