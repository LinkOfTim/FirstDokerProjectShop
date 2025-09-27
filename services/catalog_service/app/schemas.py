from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional, Any, Dict

from pydantic import BaseModel, Field, AnyHttpUrl


class ProductBase(BaseModel):
    sku: str = Field(max_length=64)
    name: str = Field(max_length=255)
    price: Decimal
    stock: int = 0
    is_active: bool = True
    description: Optional[str] = None
    template_id: Optional[uuid.UUID] = None
    attributes: Optional[Dict[str, Any]] = None


class ProductCreate(ProductBase):
    images: list[AnyHttpUrl] = []


class ProductUpdate(BaseModel):
    sku: Optional[str] = Field(default=None, max_length=64)
    name: Optional[str] = Field(default=None, max_length=255)
    price: Optional[Decimal] = None
    stock: Optional[int] = None
    is_active: Optional[bool] = None
    images: Optional[list[AnyHttpUrl]] = None


class ProductOut(ProductBase):
    id: uuid.UUID
    images: list[str] = []

    class Config:
        from_attributes = True
