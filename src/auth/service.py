from fastapi import status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth import schemas
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from src.users import model as um
from src.auth import utils
from src.auth import utils
from fastapi.security.oauth2 import OAuth2PasswordRequestForm

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