from __future__ import annotations

from typing import Dict
from datetime import datetime, timedelta, timezone
import uuid

import httpx
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .config import settings
from .db import get_session, health_check
from .models import Base, Order, OrderItem
from .schemas import OrderOut


app = FastAPI(title=settings.app_name)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e


def mint_admin_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    payload = {"sub": "order-service", "role": "admin", "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def require_admin(payload: dict):
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin required")


@app.get("/health")
async def health():
    return {"status": "ok", "db": await health_check()}


def serialize_order(o: Order) -> OrderOut:
    return OrderOut(
        id=o.id,
        user=o.user_email,
        status=o.status,
        total=o.total,
        created_at=o.created_at.isoformat() if o.created_at else datetime.now(timezone.utc).isoformat(),
        items=[
            {
                "product_id": it.product_id,
                "sku": it.sku,
                "name": it.name,
                "price": it.price,
                "qty": it.qty,
                "subtotal": it.subtotal,
            }
            for it in o.items
        ],
    )


@app.get("/orders")
async def list_orders(token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_session)):
    payload = decode_token(token)
    user = payload.get("sub")
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token subject")
    res = await session.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_email == user)
        .order_by(Order.created_at.desc())
    )
    orders = res.scalars().unique().all()
    return [serialize_order(o) for o in orders]


@app.get("/orders/{oid}")
async def get_order(oid: uuid.UUID, token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_session)):
    payload = decode_token(token)
    user = payload.get("sub")
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token subject")
    o = await session.get(Order, oid, options=[selectinload(Order.items)])
    if not o or o.user_email != user:
        raise HTTPException(status_code=404, detail="Order not found")
    return serialize_order(o)


@app.get("/admin/orders")
async def admin_list_orders(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
    status: str | None = Query(default=None),
    email: str | None = Query(default=None),
):
    payload = decode_token(token)
    require_admin(payload)
    stmt = select(Order).options(selectinload(Order.items)).order_by(Order.created_at.desc())
    if status:
        stmt = stmt.where(Order.status == status)
    if email:
        stmt = stmt.where(Order.user_email == email)
    res = await session.execute(stmt)
    orders = res.scalars().unique().all()
    return [serialize_order(o) for o in orders]


@app.patch("/orders/{oid}/cancel")
async def cancel_order(oid: uuid.UUID, token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_session)):
    payload = decode_token(token)
    require_admin(payload)
    o = await session.get(Order, oid)
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    if o.status == "canceled":
        return serialize_order(o)
    o.status = "canceled"
    session.add(o)
    await session.commit()
    await session.refresh(o)
    o = await session.get(Order, oid, options=[selectinload(Order.items)])
    return serialize_order(o)


@app.post("/orders/checkout")
async def checkout(token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_session)):
    payload = decode_token(token)
    user = payload.get("sub")
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token subject")
    admin_token = mint_admin_token()
    items = []
    total = 0.0
    async with httpx.AsyncClient(timeout=10.0) as client:
        # load cart
        cr = await client.get(f"{settings.cart_url}/cart", headers={"Authorization": f"Bearer {token}"})
        if cr.status_code != 200:
            raise HTTPException(status_code=cr.status_code, detail="cart unavailable")
        cart_map: Dict[str, int] = cr.json()
        if not cart_map:
            raise HTTPException(status_code=400, detail="Cart is empty")
        # validate, build items
        for pid, qty in cart_map.items():
            pr = await client.get(f"{settings.catalog_url}/products/{pid}")
            if pr.status_code != 200:
                raise HTTPException(status_code=404, detail=f"Product {pid} not found")
            p = pr.json()
            if not p.get("is_active", True):
                raise HTTPException(status_code=409, detail=f"{p.get('name')} not available")
            price = float(p.get("price", 0))
            stock = int(p.get("stock", 0))
            if qty > stock:
                raise HTTPException(status_code=409, detail=f"Not enough stock for {p.get('name')}")
            line_total = round(price * qty, 2)
            total += line_total
            items.append({
                "product_id": pid,
                "sku": p.get("sku"),
                "name": p.get("name"),
                "price": p.get("price"),
                "qty": qty,
                "subtotal": line_total,
            })
        # decrement stock
        for it in items:
            pid = it["product_id"]
            pr = await client.get(f"{settings.catalog_url}/products/{pid}")
            p = pr.json()
            new_stock = int(p.get("stock", 0)) - int(it["qty"]) 
            if new_stock < 0:
                raise HTTPException(status_code=409, detail=f"Not enough stock for {p.get('name')}")
            rpatch = await client.patch(
                f"{settings.catalog_url}/products/{pid}",
                json={"stock": new_stock},
                headers={"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"},
            )
            if rpatch.status_code not in (200, 201):
                raise HTTPException(status_code=rpatch.status_code, detail="Stock update failed")
        # persist order
        order = Order(user_email=user, status="paid", total=round(total, 2))
        session.add(order)
        await session.flush()
        for it in items:
            oi = OrderItem(
                order_id=order.id,
                product_id=uuid.UUID(it["product_id"]),
                sku=it["sku"],
                name=it["name"],
                price=it["price"],
                qty=int(it["qty"]),
                subtotal=it["subtotal"],
            )
            session.add(oi)
        await session.commit()
        # clear cart
        await client.post(f"{settings.cart_url}/cart/clear", headers={"Authorization": f"Bearer {token}"})
        # return order model from in-memory snapshot to avoid lazy loads
        return {
            "id": order.id,
            "user": user,
            "status": "paid",
            "total": round(total, 2),
            "items": items,
            "created_at": order.created_at.isoformat() if order.created_at else datetime.now(timezone.utc).isoformat(),
        }
