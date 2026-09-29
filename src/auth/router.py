from fastapi import APIRouter, Depends
from src.auth import dependencies
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


@router.post("/send_otp", response_model=schemas.OTPRequestResponse, status_code=202)
async def send_otp(credentials: schemas.OTPRequest, session = Depends(get_db), redis = Depends(dependencies.get_redis)):
    return await auth_service.request_otp(credentials.email, session, redis)


@router.post("/verify_otp", response_model=schemas.OTPVerifyResponse)
async def verify_otp(credentials: schemas.OTPVerify, session = Depends(get_db), redis = Depends(dependencies.get_redis)):
    return await auth_service.verify_otp(credentials.email, credentials.code, session, redis)
