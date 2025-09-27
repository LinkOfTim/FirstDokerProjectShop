from __future__ import annotations

import os
import logging
from fastapi import FastAPI
from sqlalchemy import select

from .config import settings
from .db import health_check, AsyncSessionLocal
from .errors import add_exception_handlers, setup_logging
from .routers import auth
from .auth import hash_password
from .models import User


setup_logging()
logger = logging.getLogger("auth")
app = FastAPI(title=settings.app_name)
add_exception_handlers(app)


@app.get("/health")
async def health():
    db_ok = await health_check()
    return {"status": "ok", "db": db_ok}


app.include_router(auth.router)


@app.on_event("startup")
async def ensure_admin():
    admin_email = os.getenv("ADMIN_EMAIL") or "admin@example.com"
    admin_password = os.getenv("ADMIN_PASSWORD") or "admin123"
    async with AsyncSessionLocal() as session:
        # if any user exists, ensure_admin is idempotent: create only if not found
        existing = (await session.execute(select(User).where(User.email == admin_email))).scalar_one_or_none()
        if existing:
            logger.info("Admin user already exists: %s", admin_email)
            return
        # If no explicit ADMIN_* provided and there are already users, do nothing
        # Otherwise, if there are no users at all, create default admin
        any_user = (await session.execute(select(User).limit(1))).scalar_one_or_none()
        if any_user and (os.getenv("ADMIN_EMAIL") is None or os.getenv("ADMIN_PASSWORD") is None):
            return
        user = User(email=admin_email, password_hash=hash_password(admin_password), role="admin")
        session.add(user)
        await session.commit()
        logger.info("Admin user created: %s", admin_email)
