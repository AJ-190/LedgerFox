from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import EmailStr, SecretStr
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

class Settings(BaseSettings):
    DATABASE_URL: str
    REFRESH_TOKEN_TIME_MINUTES: int = 60 * 24 * 7
    ACCESS_TOKEN_TIME_MINUTES: int = 60
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    REDIS_URL: str
    REQUEST_LIMIT: int = 5
    REQUEST_LIMIT_EXPIRY: int = 60

    NOTIFIER_URL: str
    NOTIFIER_API_KEY: SecretStr
    NOTIFIER_FROM: EmailStr
    NOTIFIER_FROM_NAME: str = "LedgerFox"
    NOTIFIER_TIMEOUT: int = 10

    OTP_LENGTH: int = 6
    OTP_EXPIRY_SECONDS: int = 300
    OTP_MAX_ATTEMPTS: int = 5
    OTP_RESEND_COOLDOWN: int = 60

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / "src" / ".env",
        extra="ignore",
        env_file_encoding="utf-8"
        
    )
    
settings = Settings()