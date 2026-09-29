from fastapi import FastAPI
from src.db.database import Base, engine
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from src.auth.router import router as auth_router
from src.db.redis import get_redis_client
from src.middleware.auth_rate_limiter import auth_rate_limiter_mid

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        app.state.redis = await get_redis_client()
    yield


app = FastAPI(
    title="LedgerFox",
    description="is a backend payments and settlement engine",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(auth_rate_limiter_mid)
app.include_router(auth_router)

@app.get("/")
async def root():
    return "LedgerFox is running...."