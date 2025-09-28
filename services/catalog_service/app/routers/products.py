from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

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
    result = await session.execute(stmt.options(selectinload(models.Product.images)))
    items = list(result.scalars().unique().all())
    out = [
        schemas.ProductOut(
            id=p.id,
            sku=p.sku,
            name=p.name,
            price=p.price,
            stock=p.stock,
            is_active=p.is_active,
            description=getattr(p, "description", None),
            attributes=getattr(p, "attributes", None),
            template_id=getattr(p, "template_id", None),
            images=[img.url for img in (p.images or [])],
        )
        for p in items
    ]
    return out


@router.get("/{product_id}", response_model=schemas.ProductOut)
async def get_product(product_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    product = await session.get(models.Product, product_id, options=[selectinload(models.Product.images)])
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return schemas.ProductOut(
        id=product.id,
        sku=product.sku,
        name=product.name,
        price=product.price,
        stock=product.stock,
        is_active=product.is_active,
        description=getattr(product, "description", None),
        attributes=getattr(product, "attributes", None),
        template_id=getattr(product, "template_id", None),
        images=[pi.url for pi in product.images],
    )


@router.get("/sku/{sku}", response_model=schemas.ProductOut)
async def get_product_by_sku(sku: str, session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(models.Product).options(selectinload(models.Product.images)).where(models.Product.sku == sku))
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return schemas.ProductOut(
        id=p.id,
        sku=p.sku,
        name=p.name,
        price=p.price,
        stock=p.stock,
        is_active=p.is_active,
        description=getattr(p, "description", None),
        attributes=getattr(p, "attributes", None),
        template_id=getattr(p, "template_id", None),
        images=[pi.url for pi in p.images],
    )


@router.post("/", response_model=schemas.ProductOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_admin)])
async def create_product(payload: schemas.ProductCreate, session: AsyncSession = Depends(get_session)):
    data = payload.model_dump()
    images = data.pop("images", [])
    product = models.Product(**data)
    session.add(product)
    try:
        await session.flush()
        # attach images (if any)
        for url in images or []:
            if url:
                session.add(models.ProductImage(product_id=product.id, url=str(url)))
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SKU must be unique")
    # load image URLs explicitly to avoid any lazy load in async context
    res = await session.execute(
        select(models.ProductImage.url).where(models.ProductImage.product_id == product.id)
    )
    urls = [row[0] for row in res.all()]
    return schemas.ProductOut(
        id=product.id,
        sku=product.sku,
        name=product.name,
        price=product.price,
        stock=product.stock,
        is_active=product.is_active,
        description=getattr(product, "description", None),
        attributes=getattr(product, "attributes", None),
        template_id=getattr(product, "template_id", None),
        images=urls,
    )


@router.patch("/{product_id}", response_model=schemas.ProductOut, dependencies=[Depends(get_current_admin)])
async def update_product(
    product_id: uuid.UUID, payload: schemas.ProductUpdate, session: AsyncSession = Depends(get_session)
):
    # Load product entity (no relationship lazy-loads in async context)
    product = await session.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    data = payload.model_dump(exclude_unset=True)
    images = data.pop("images", None)
    for field, value in data.items():
        setattr(product, field, value)
    # replace images if provided
    if images is not None:
        # delete old without triggering async lazy-load
        res = await session.execute(
            select(models.ProductImage).where(models.ProductImage.product_id == product.id)
        )
        for img in res.scalars().all():
            await session.delete(img)
        # add new
        for url in images:
            if url:
                session.add(models.ProductImage(product_id=product.id, url=str(url)))

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        # Unify message with create handler for better UX
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SKU must be unique")
    # load image URLs explicitly
    res = await session.execute(
        select(models.ProductImage.url).where(models.ProductImage.product_id == product.id)
    )
    urls = [row[0] for row in res.all()]
    return schemas.ProductOut(
        id=product.id,
        sku=product.sku,
        name=product.name,
        price=product.price,
        stock=product.stock,
        is_active=product.is_active,
        description=getattr(product, "description", None),
        attributes=getattr(product, "attributes", None),
        template_id=getattr(product, "template_id", None),
        images=urls,
    )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin)])
async def delete_product(product_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    product = await session.get(models.Product, product_id)
    if not product:
        return
    await session.delete(product)
    await session.commit()
    return
