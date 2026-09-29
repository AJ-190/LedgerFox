from fastapi import Request, status
from fastapi.responses import JSONResponse
from src.db.redis import auth_rate_limiter
from src.config import settings


RATE_LIMITED_PATHS = [
    '/auth/register_account',
    "/auth/login",
    "/auth/send_otp",
    "/auth/verify_otp",
]


async def auth_rate_limiter_mid(request: Request, call_next):
    if request.url.path not in RATE_LIMITED_PATHS:
        response = await call_next(request)
        return response
    
    client_ip = request.client.host if request.client else None
    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            content={"msg": "Rate limit service is unavailable"})
    if client_ip and await auth_rate_limiter(redis, client_ip,settings.REQUEST_LIMIT_EXPIRY):
        return JSONResponse(status_code=status.HTTP_429_TOO_MANY_REQUESTS, 
                           content={"msg": "Too many request, try again later"})
    
    response = await call_next(request)
    return response

