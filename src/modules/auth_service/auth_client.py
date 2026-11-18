import httpx
from dotenv import load_dotenv
from src.modules.core.settings import settings

load_dotenv()

AUTH_SERVICE_URL = settings.AUTH_SERVICE_URL


async def register_user(user_data: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{AUTH_SERVICE_URL}/register", json=user_data)
        response.raise_for_status()
        return response.json()


async def login_user(credentials: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{AUTH_SERVICE_URL}/login",
            json=credentials,
        )

        response.raise_for_status()

        data = response.json()
        set_cookie_headers = response.headers.get_list("set-cookie")

        return data, set_cookie_headers


async def refresh_access_token(refresh_token: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{AUTH_SERVICE_URL}/refresh-token",
            cookies={"refreshToken": refresh_token},
        )

        response.raise_for_status()

        data = response.json()
        set_cookie_headers = response.headers.get_list("set-cookie")

        return data, set_cookie_headers


async def get_user_profile(token: str):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{AUTH_SERVICE_URL}/get-user-profile", headers=headers
        )
        response.raise_for_status()
        return response.json()


async def get_user_by_id(user_id: int):
    headers = {"x-service-secret": settings.FASTAPI_SERVICE_SECRET}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{AUTH_SERVICE_URL}/users/{user_id}",
            headers=headers,
        )

        response.raise_for_status()
        return response.json()
