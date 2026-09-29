import httpx

from src.config import settings


def build_otp_payload(to: str, code: str, name: str | None = None) -> dict:
    return {
        "to": to,
        "name": name or "there",
        "code": code,
        "subject": f"{settings.NOTIFIER_FROM_NAME} verification code",
        "from": settings.NOTIFIER_FROM,
        "from_name": settings.NOTIFIER_FROM_NAME,
        "expires_in_seconds": settings.OTP_EXPIRY_SECONDS,
    }


async def send_otp_code(to: str, code: str, name: str | None = None) -> None:
    headers = {
        "Authorization": f"Bearer {settings.NOTIFIER_API_KEY.get_secret_value()}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=settings.NOTIFIER_TIMEOUT) as client:
        response = await client.post(
            settings.NOTIFIER_URL, json=build_otp_payload(to, code, name), headers=headers
        )
        response.raise_for_status()
