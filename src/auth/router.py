from fastapi import APIRouter, Depends
from src.auth import schemas
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth import service as auth_service
from src.db.database import get_db
from fastapi.security.oauth2 import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=['Sign Up'])

@router.post("/register_account",response_model=schemas.RegisterAccountResponse, status_code=201)
async def sign_up(credentials: schemas.RegisterAccount, session = Depends(get_db)):
   return await auth_service.sign_up(credentials, session)
    
    
@router.post("/login", response_model=schemas.LoginResponse)
async def login(credentials:OAuth2PasswordRequestForm = Depends(), session = Depends(get_db)):
    return await auth_service.login(credentials, session)