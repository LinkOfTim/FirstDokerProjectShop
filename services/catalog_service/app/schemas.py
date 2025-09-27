from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class ProductBase(BaseModel):
    sku: str = Field(max_length=64)
    name: str = Field(max_length=255)
    price: Decimal
    stock: int = 0
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    sku: Optional[str] = Field(default=None, max_length=64)
    name: Optional[str] = Field(default=None, max_length=255)
    price: Optional[Decimal] = None
    stock: Optional[int] = None
    is_active: Optional[bool] = None


class ProductOut(ProductBase):
    id: uuid.UUID

    class Config:
        from_attributes = True

