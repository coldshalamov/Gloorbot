from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    hostname: str | None = None
    version: str | None = None


class RegisterResponse(BaseModel):
    client_id: str


class HeartbeatRequest(BaseModel):
    client_id: str
    hostname: str | None = None
    version: str | None = None
    cpu_percent: float | None = None
    mem_percent: float | None = None
    slots: int | None = None
    tasks_completed: int | None = None
    deals_sent: int | None = None


class LeaseNextRequest(BaseModel):
    client_id: str
    preferred_store_id: str | None = None


class LeaseResponse(BaseModel):
    task_id: int
    lease_seconds: int
    store_id: str
    store_name: str
    store_url: str
    category_url: str


class LeaseCompleteRequest(BaseModel):
    client_id: str
    task_id: int
    duration_sec: float | None = None
    products_seen: int | None = None
    deals_sent: int | None = None


class DealItem(BaseModel):
    store_id: str
    store_name: str
    category_url: str | None = None
    product_url: str
    title: str
    price: float
    was_price: float
    pct_off: float = Field(ge=0.0, le=1.0)
    found_at: datetime | None = None


class DealsBulkRequest(BaseModel):
    client_id: str
    batch_id: str | None = None
    task_id: int | None = None
    deals: list[DealItem]
