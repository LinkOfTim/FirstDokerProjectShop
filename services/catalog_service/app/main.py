from __future__ import annotations

from fastapi import FastAPI

from .config import settings
from .db import health_check
from .errors import add_exception_handlers, setup_logging
from .routers import products, templates


setup_logging()
app = FastAPI(title=settings.app_name)
add_exception_handlers(app)


@app.get("/health")
async def health():
    db_ok = await health_check()
    return {"status": "ok", "db": db_ok}


app.include_router(products.router)
app.include_router(templates.router)
