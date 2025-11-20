from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from .. import models, schemas
from ..auth import (
    create_access_token,
    hash_password,
    verify_password,
    get_user_by_email,
    get_current_user,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserOut)
async def register(payload: schemas.UserCreate, session: AsyncSession = Depends(get_session)):
    existing = await get_user_by_email(session, payload.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = models.User(email=payload.email, password_hash=hash_password(payload.password), role="user")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/login", response_model=schemas.TokenResponse)
async def login(response: Response, form: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_session)):
    user = await get_user_by_email(session, form.username)
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(email=user.email, role=user.role)
    response.set_cookie("access_token", token, httponly=True, secure=False, samesite="lax")
    return schemas.TokenResponse(access_token=token)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"detail": "logged out"}


@router.post("/change_password")
async def change_password(
    payload: schemas.ChangePassword,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user.password_hash = hash_password(payload.new_password)
    session.add(user)
    await session.commit()
    return {"ok": True}
