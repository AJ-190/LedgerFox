from passlib.context import CryptContext
from typing import Optional
from datetime import timedelta, datetime, timezone
import uuid
from src.config import settings
import jwt
from jwt.exceptions import InvalidTokenError

pwd = CryptContext(schemes=["argon2"], deprecated="auto")

def hash(password):
    return pwd.hash(password)

def verify(password, hashed_password):
    return pwd.verify(password, hashed_password)


def TokenGen(user: dict, expire: Optional[timedelta] = None, refresh: bool = False) -> str:
    now = datetime.now(timezone.utc)

    if expire is None:
        minutes = settings.REFRESH_TOKEN_TIME_MINUTES if refresh else settings.ACCESS_TOKEN_TIME_MINUTES
        expire_delta = timedelta(minutes=minutes)
    elif isinstance(expire, timedelta):
        expire_delta = expire
    elif isinstance(expire, (int, float)):
        expire_delta = timedelta(minutes=expire)
    else:
        raise TypeError("expire must be a timedelta, a number of minutes, or None")
    sub = user.get("sub")

    payload = {
        "sub": str(sub),
        "refresh": refresh,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + expire_delta,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def TokenDecode(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    