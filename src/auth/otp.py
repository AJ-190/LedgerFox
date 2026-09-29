import hashlib
import hmac
import secrets

import redis.asyncio as airedis
from fastapi import status, HTTPException

from src.config import settings

CODE_PREFIX = "otp:code:"
ATTEMPT_PREFIX = "otp:attempts:"
COOLDOWN_PREFIX = "otp:cooldown:"


def generate_code() -> str:
    return str(secrets.randbelow(10 ** settings.OTP_LENGTH)).zfill(settings.OTP_LENGTH)


def digest(email: str, code: str) -> str:
    payload = f"{email}:{code}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), payload, hashlib.sha256).hexdigest()


def _keys(email: str) -> tuple[str, str]:
    return CODE_PREFIX + email, ATTEMPT_PREFIX + email


async def issue_code(redis: airedis.Redis, email: str) -> str:
    code = generate_code()
    code_key, attempt_key = _keys(email)
    pipe = redis.pipeline()
    pipe.set(code_key, digest(email, code), ex=settings.OTP_EXPIRY_SECONDS)
    pipe.delete(attempt_key)
    pipe.set(COOLDOWN_PREFIX + email, 1, ex=settings.OTP_RESEND_COOLDOWN)
    await pipe.execute()
    return code


async def in_cooldown(redis: airedis.Redis, email: str) -> bool:
    return bool(await redis.exists(COOLDOWN_PREFIX + email))


async def start_cooldown(redis: airedis.Redis, email: str) -> None:
    await redis.set(COOLDOWN_PREFIX + email, 1, ex=settings.OTP_RESEND_COOLDOWN)


async def verify_code(redis: airedis.Redis, email: str, code: str) -> None:
    code_key, attempt_key = _keys(email)
    stored = await redis.get(code_key)

    if not stored:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired or was never requested",
        )

    if not hmac.compare_digest(stored, digest(email, code)):
        pipe = redis.pipeline()
        pipe.incr(attempt_key)
        pipe.expire(attempt_key, settings.OTP_EXPIRY_SECONDS, nx=True)
        attempts, _ = await pipe.execute()
        if attempts >= settings.OTP_MAX_ATTEMPTS:
            await redis.delete(code_key, attempt_key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many incorrect attempts, request a new code",
            )
        remaining = settings.OTP_MAX_ATTEMPTS - attempts
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Incorrect code, {remaining} attempt(s) remaining",
        )

    await redis.delete(code_key, attempt_key)
