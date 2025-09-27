from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.exc import IntegrityError

from ..db import get_session
from .. import models, schemas
from ..authz import get_current_admin


router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=List[schemas.ProductOut])
async def list_products(
    q: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    is_active: Optional[bool] = None,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(models.Product)
    conds = []
    if q:
        like = f"%{q}%"
        conds.append(or_(models.Product.name.ilike(like), models.Product.sku.ilike(like)))
    if min_price is not None:
        conds.append(models.Product.price >= min_price)
    if max_price is not None:
        conds.append(models.Product.price <= max_price)
    if is_active is not None:
        conds.append(models.Product.is_active == is_active)
    if conds:
        stmt = stmt.where(and_(*conds))
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{product_id}", response_model=schemas.ProductOut)
async def get_product(product_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    product = await session.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.post("/", response_model=schemas.ProductOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_admin)])
async def create_product(payload: schemas.ProductCreate, session: AsyncSession = Depends(get_session)):
    product = models.Product(**payload.model_dump())
    session.add(product)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SKU must be unique")
    await session.refresh(product)
    return product


@router.patch("/{product_id}", response_model=schemas.ProductOut, dependencies=[Depends(get_current_admin)])
async def update_product(
    product_id: uuid.UUID, payload: schemas.ProductUpdate, session: AsyncSession = Depends(get_session)
):
    product = await session.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Integrity error")
    await session.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin)])
async def delete_product(product_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    product = await session.get(models.Product, product_id)
    if not product:
        return
    await session.delete(product)
    await session.commit()
    return
