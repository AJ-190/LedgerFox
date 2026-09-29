from pydantic import BaseModel, ConfigDict,EmailStr, field_validator, SecretStr
from datetime import datetime
from typing import Optional
import re

from src.config import settings


class RegisterAccount(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: SecretStr
    phone: str
    
    
    @field_validator("password")
    @classmethod
    def validate(cls, value):
        
        SPECIAL = re.compile(r"[!@#$%^&*(),.?\":{}|<>\-_=+\[\]/\\;'`~]")

        pwd = value.get_secret_value() if isinstance(value, SecretStr) else value
        if len(pwd) < 8:
            raise ValueError("Password length must be greater than or equal to 8 characters")
        if not any(ch.isdigit() for ch in pwd):
            
            raise ValueError("Password must at least contain one digit")
        if not any(ch.islower() for ch in pwd):
            raise ValueError("Password must contain at least on lower case letter")
        if not any(ch.isupper() for ch in pwd):
            raise ValueError("Password must contain at least one upper case letter")
        if not SPECIAL.search(pwd):
            raise ValueError("Password must contain at least one special character")
        
        return value
    
class RegisterAccountResponse(BaseModel):
    name: str
    email: EmailStr
    phone: str
    is_verify: Optional[bool] = False
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
    

class Login(BaseModel):
    phone_or_email: str
    password: str
    
    
class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    
    model_config = ConfigDict(from_attributes=True)


class OTPRequest(BaseModel):
    email: EmailStr


class OTPRequestResponse(BaseModel):
    message: str
    expires_in: int


class OTPVerify(BaseModel):
    email: EmailStr
    code: str

    @field_validator("code")
    @classmethod
    def validate(cls, value):
        if not value.isdigit() or len(value) != settings.OTP_LENGTH:
            raise ValueError(f"Code must be exactly {settings.OTP_LENGTH} digits")
        return value


class OTPVerifyResponse(BaseModel):
    email: EmailStr
    is_verified: bool

    model_config = ConfigDict(from_attributes=True)
