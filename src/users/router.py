from fastapi import APIRouter, Depends
from src.auth import schemas
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth import service as auth_service
from src.db.database import get_db
from sqlalchemy import select
from src.users import model as um

router = APIRouter(prefix="/user", tags=['User'])

@router.get("/{user_id}", response_model=schemas.RegisterAccountResponse)
async def get_user(user_id: int,session: AsyncSession = Depends(get_db)):
    pass