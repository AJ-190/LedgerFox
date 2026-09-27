from fastapi import FastAPI
from src.db.database import Base, engine
from contextlib import asynccontextmanager
from src.auth.router import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="LedgerFox",
    description="is a backend payments and settlement engine",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth_router)

@app.get("/")
async def root():
    return "LedgerFox is running...."