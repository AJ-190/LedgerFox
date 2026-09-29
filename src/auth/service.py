from src.config import settings
from fastapi import status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth import otp
from src.auth import schemas
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from src.notify import utils as notify
from src.users import model as um
from src.auth import utils
from src.auth import utils
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
import redis.asyncio as airedis

async def sign_up(credentials: schemas.RegisterAccount, session: AsyncSession):
    user = um.Users(
        phone=credentials.phone,
        name= f"{credentials.first_name} {credentials.last_name}",
        email=credentials.email,
        password=utils.hash(credentials.password.get_secret_value()),
    )
    session.add(user)
    try:
        await session.commit()
        await session.refresh(user)
        return user
    except IntegrityError:
        await session.rollback()             
        raise HTTPException(409, "User already exists")
    
    
    
async def login(credentials, session: AsyncSession):
    exist = (
        await session.execute(
            select(um.Users)
            .where((um.Users.phone == credentials.username) | (um.Users.email == credentials.username))
        )
    ).scalar_one_or_none()
    
    if not exist:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account with email or phone does not exist")
    
    if not utils.verify(credentials.password, exist.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials")
    
    access_token = utils.TokenGen(
        {"sub": exist.user_id}, refresh=False
    )
    refresh_token = utils.TokenGen(
        {"sub": exist.user_id}, refresh=True
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


async def request_otp(email: str, session: AsyncSession, redis: airedis.Redis) -> dict:
    recipient = email.strip().lower()

    if await otp.in_cooldown(redis, recipient):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Please wait before requesting another code",
        )

    user = (
        await session.execute(select(um.Users).where(um.Users.email == recipient))
    ).scalar_one_or_none()

    if not user:
        await otp.start_cooldown(redis, recipient)
        return {
            "message": "If an account exists for that address, a verification code has been sent.",
            "expires_in": settings.OTP_EXPIRY_SECONDS,
        }

    code = await otp.issue_code(redis, recipient)

    try:
        await notify.send_otp_code(recipient, code, name=user.name)
    except Exception as e:
        await redis.delete(otp.CODE_PREFIX + recipient)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not send the verification email, try again later: {e}",
        )

    return {
        "message": "If an account exists for that address, a verification code has been sent.",
        "expires_in": settings.OTP_EXPIRY_SECONDS,
    }


async def verify_otp(
    email: str, code: str, session: AsyncSession, redis: airedis.Redis
) -> um.Users:
    claimant = email.strip().lower()
    await otp.verify_code(redis, claimant, code)

    user = (
        await session.execute(select(um.Users).where(um.Users.email == claimant))
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account no longer exists"
        )

    user.is_verified = True
    await session.commit()
    await session.refresh(user)
    return user
