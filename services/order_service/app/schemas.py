from __future__ import annotations

import uuid
from decimal import Decimal
from pydantic import BaseModel
from typing import List


class OrderItemOut(BaseModel):
    product_id: uuid.UUID
    sku: str
    name: str
    price: Decimal
    qty: int
    subtotal: Decimal


class OrderOut(BaseModel):
    id: uuid.UUID
    user: str
    status: str
    total: Decimal
    items: List[OrderItemOut]
    created_at: str

