from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_session
from .. import models
from ..authz import get_current_admin


router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("/", response_model=List[dict])
async def list_templates(session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(models.ProductTemplate).order_by(models.ProductTemplate.created_at.desc()))
    items = res.scalars().all()
    return [
        {"id": t.id, "name": t.name, "schema": t.schema, "created_at": t.created_at.isoformat() if t.created_at else None}
        for t in items
    ]


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_admin)])
async def create_template(payload: dict, session: AsyncSession = Depends(get_session)):
    name = str(payload.get("name") or "").strip()
    schema = payload.get("schema") or {}
    if not name:
        raise HTTPException(status_code=422, detail="name is required")
    tpl = models.ProductTemplate(name=name, schema=schema)
    session.add(tpl)
    await session.commit()
    await session.refresh(tpl)
    return {"id": tpl.id, "name": tpl.name, "schema": tpl.schema}


@router.get("/{tid}", response_model=dict)
async def get_template(tid: uuid.UUID, session: AsyncSession = Depends(get_session)):
    t = await session.get(models.ProductTemplate, tid)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"id": t.id, "name": t.name, "schema": t.schema}


@router.patch("/{tid}", response_model=dict, dependencies=[Depends(get_current_admin)])
async def update_template(tid: uuid.UUID, payload: dict, session: AsyncSession = Depends(get_session)):
    t = await session.get(models.ProductTemplate, tid)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    if "name" in payload:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=422, detail="invalid name")
        t.name = name
    if "schema" in payload:
        t.schema = payload.get("schema") or {}
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return {"id": t.id, "name": t.name, "schema": t.schema}


@router.delete("/{tid}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin)])
async def delete_template(tid: uuid.UUID, session: AsyncSession = Depends(get_session)):
    t = await session.get(models.ProductTemplate, tid)
    if not t:
        return
    await session.delete(t)
    await session.commit()
    return

