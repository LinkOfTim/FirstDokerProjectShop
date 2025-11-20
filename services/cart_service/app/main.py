from __future__ import annotations

from typing import Dict
import json

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from redis import asyncio as aioredis

from .config import settings


app = FastAPI(title=settings.app_name)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e


def get_cart_key(identity: str) -> str:
    return f"cart:{identity}"


@app.on_event("startup")
async def on_startup():
    app.state.redis = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)


@app.on_event("shutdown")
async def on_shutdown():
    r = app.state.redis
    if r:
        await r.close()


@app.get("/health")
async def health():
    try:
        pong = await app.state.redis.ping()
    except Exception:
        pong = False
    return {"status": "ok", "redis": bool(pong)}


@app.get("/cart")
async def get_cart(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token subject")
    key = get_cart_key(sub)
    items: Dict[str, str] = await app.state.redis.hgetall(key)
    # Convert values to int
    return {pid: int(qty) for pid, qty in items.items()}


@app.post("/cart/add")
async def cart_add(body: dict, token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token subject")
    pid = str(body.get("product_id") or "").strip()
    qty = int(body.get("qty") or 0)
    if not pid or qty <= 0:
        raise HTTPException(status_code=422, detail="Invalid input")
    key = get_cart_key(sub)
    await app.state.redis.hincrby(key, pid, qty)
    return {"ok": True}


@app.post("/cart/remove")
async def cart_remove(body: dict, token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token subject")
    pid = str(body.get("product_id") or "").strip()
    if not pid:
        raise HTTPException(status_code=422, detail="Invalid input")
    key = get_cart_key(sub)
    await app.state.redis.hdel(key, pid)
    return {"ok": True}


@app.post("/cart/set")
async def cart_set(body: dict, token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token subject")
    pid = str(body.get("product_id") or "").strip()
    if not pid:
        raise HTTPException(status_code=422, detail="Invalid input")
    try:
        qty = int(body.get("qty"))
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid qty")
    key = get_cart_key(sub)
    if qty <= 0:
        await app.state.redis.hdel(key, pid)
    else:
        await app.state.redis.hset(key, pid, qty)
    return {"ok": True}


@app.post("/cart/clear")
async def cart_clear(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token subject")
    key = get_cart_key(sub)
    # delete entire cart hash key
    await app.state.redis.delete(key)
    return {"ok": True}


# Orders storage in Redis
# keys: orders:{sub} -> list(JSON), order:{id} -> JSON


@app.get("/orders")
async def list_orders(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token subject")
    key = f"orders:{sub}"
    items = await app.state.redis.lrange(key, 0, -1)
    return [json.loads(x) for x in items]


@app.get("/orders/{oid}")
async def get_order(oid: str, token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token subject")
    raw = await app.state.redis.get(f"order:{oid}")
    if not raw:
        raise HTTPException(status_code=404, detail="Order not found")
    data = json.loads(raw)
    if data.get("user") != sub:
        raise HTTPException(status_code=403, detail="Forbidden")
    return data


@app.post("/orders/add")
async def add_order(body: dict, token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token subject")
    order = dict(body)
    order["user"] = sub
    oid = order.get("id")
    if not oid:
        raise HTTPException(status_code=422, detail="Order id required")
    raw = json.dumps(order, ensure_ascii=False)
    await app.state.redis.set(f"order:{oid}", raw)
    await app.state.redis.lpush(f"orders:{sub}", raw)
    return {"ok": True, "id": oid}
