"""Request/response models for the HTTP API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = Field(default=None, max_length=128)
    # No customer_id — identity always comes from the access token.


class ChatResponse(BaseModel):
    response: str
    session_id: str
    customer_id: str
    memories_stored: int


class MenuItem(BaseModel):
    id: int
    name: str
    category: str
    description: str
    price: float
    tags: list[str]
    is_available: bool
    image_url: str | None = None


class OrderItem(BaseModel):
    name: str
    quantity: int
    unit_price: float


class Order(BaseModel):
    id: str
    status: str
    subtotal: float
    tax: float
    total: float
    address: str | None
    notes: str | None
    created_at: datetime
    items: list[OrderItem]


class KitchenOrder(Order):
    """An order as the chef sees it — with who placed it and where it goes next."""

    updated_at: datetime
    customer_name: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None
    next_status: str | None = None


class MessageOut(BaseModel):
    role: str
    content: str


class OkResponse(BaseModel):
    ok: bool = True
    detail: str = ""
