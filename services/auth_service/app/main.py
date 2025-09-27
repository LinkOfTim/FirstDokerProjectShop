from __future__ import annotations

import os
from fastapi import FastAPI
from sqlalchemy import select

from .config import settings
from .db import health_check, AsyncSessionLocal
from .errors import add_exception_handlers, setup_logging
from .routers import auth
from .auth import hash_password
from .models import User


setup_logging()
app = FastAPI(title=settings.app_name)
add_exception_handlers(app)


@app.get("/health")
async def health():
    db_ok = await health_check()
    return {"status": "ok", "db": db_ok}


app.include_router(auth.router)


@app.on_event("startup")
async def ensure_admin():
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_email or not admin_password:
        return
    async with AsyncSessionLocal() as session:
        existing = (await session.execute(select(User).where(User.email == admin_email))).scalar_one_or_none()
        if existing:
            return
        user = User(email=admin_email, password_hash=hash_password(admin_password), role="admin")
        session.add(user)
        await session.commit()

