from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from src.config import settings


Base = declarative_base()

engine = create_async_engine(
    url=settings.DATABASE_URL,
    echo=False,
    connect_args={"statement_cache_size": 0},
    pool_size=5,
    pool_pre_ping=True,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, autoflush=False, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()