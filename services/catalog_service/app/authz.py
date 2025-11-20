from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from .config import settings


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_admin(token: str = Depends(oauth2_scheme)):
    payload = _decode(token)
    role = payload.get("role")
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    return payload

