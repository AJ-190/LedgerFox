from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

class Settings(BaseSettings):
    DATABASE_URL: str
    REFRESH_TOKEN_TIME_MINUTES: int = 60 * 24 * 7
    ACCESS_TOKEN_TIME_MINUTES: int = 60
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / "src" / ".env",
        extra="ignore",
        env_file_encoding="utf-8"
        
    )
    
settings = Settings()