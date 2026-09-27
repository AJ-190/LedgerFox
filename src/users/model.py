from src.db.database import get_db, Base
from sqlalchemy.orm import mapped_column, Mapped,relationship
from sqlalchemy import false, DateTime, func, Enum as SAEnum
from datetime import datetime
import enum

class LedgerRoleEnum(str, enum.Enum):
    owner = "owner" 
    admin = "admin" 
    operator = "operator"
    approver = "approver"
    viewer = "viewer"
    

class Users(Base):
    __tablename__ = "users"
    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(nullable=False, unique=True)
    phone: Mapped[str] = mapped_column(nullable=False, unique=True)
    password: Mapped[str] = mapped_column(nullable=False)
    is_verified: Mapped[bool] = mapped_column(nullable=True, server_default=false())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    

    