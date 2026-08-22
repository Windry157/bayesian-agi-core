import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24


def create_token(user_id: str, role: str = "user") -> Optional[str]:
    try:
        from jose import jwt
        payload = {
            "sub": user_id,
            "role": role,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    except ImportError:
        logger.warning("python-jose not installed. Run: pip install python-jose[cryptography]")
        return None


def verify_token(token: str) -> Optional[dict]:
    try:
        from jose import jwt, JWTError
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except ImportError:
        logger.warning("python-jose not installed.")
        return None
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        return None


async def auth_middleware(request: Request, call_next):
    public_paths = {"/health", "/health/detailed", "/metrics", "/"}
    if request.url.path in public_paths:
        return await call_next(request)
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "Missing or invalid Authorization header"})
    token = auth_header.split(" ", 1)[1]
    payload = verify_token(token)
    if payload is None:
        return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})
    request.state.user = payload
    return await call_next(request)
