from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as airedis

from src.auth import utils
from src.db.database import get_db
from src.users import model as um

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_redis(request: Request) -> airedis.Redis:
    client = getattr(request.app.state, "redis", None)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Verification service is unavailable",
        )
    try:
        await client.ping()
    except RedisError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Verification service is unavailable",
        )
    return client


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
) -> um.Users:
    try:
        payload = utils.TokenDecode(token)
    except InvalidTokenError:
        raise _unauthorized("Could not validate credentials")

    if payload.get("refresh"):
        raise _unauthorized("Refresh token cannot be used to authorize a request")

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise _unauthorized("Could not validate credentials")

    user = await session.get(um.Users, user_id)
    if not user:
        raise _unauthorized("User no longer exists")

    return user
