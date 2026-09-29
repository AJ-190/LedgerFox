import redis.asyncio  as airedis
from src.config import settings
from fastapi import status, HTTPException


async def get_redis_client() -> airedis.Redis | None:
    url = settings.REDIS_URL
    if not url:
        print("[REDIS]: redis url not set")
        return None
    try:
        client = airedis.from_url(url, decode_responses=True)
        await client.ping()
        print("[REDIS]: redis connected successfully")
        return client
    except Exception as e:
        print(f"[REDIS]: failed when connecting to redis: {e}")
        return None
    
async def auth_rate_limiter(redis: airedis.Redis, ip: str, expire: int) -> bool:
    client_ip = f"ip_{ip}"

    try:
        count = int(await redis.hget(client_ip, "count"))
    except (TypeError, ValueError):
        count = 0

    if count >= settings.REQUEST_LIMIT:
        return True

    pipe = redis.pipeline()
    pipe.hincrby(client_ip, "count", 1)
    pipe.expire(client_ip, expire, nx=True)   
    await pipe.execute()
    return False

async def block_jti(redis: airedis.Redis, jti: str, expire: int):
    await redis.set(f"jti:{jti}", 1, ex=expire)
    return

async def check_jti(redis: airedis.Redis, jti: str, expire: int):
    if not await redis.get(f"jti:{jti}"):
        return False
    return True
    
    