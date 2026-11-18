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
        response = await client.post(f"{AUTH_SERVICE_URL}/login", json=credentials)

        response.raise_for_status()

        data = response.json()
        refresh_token = response.cookies.get("refreshToken")

        return data, refresh_token


async def get_user_profile(token: str):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{AUTH_SERVICE_URL}/get-user-profile", headers=headers
        )
        response.raise_for_status()
        return response.json()


async def refresh_access_token(refresh_token: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{AUTH_SERVICE_URL}/refresh-token",
            cookies={"refreshToken": refresh_token},
        )

        response.raise_for_status()

        data = response.json()

        new_refresh_token = response.cookies.get("refreshToken")

        return data, new_refresh_token
