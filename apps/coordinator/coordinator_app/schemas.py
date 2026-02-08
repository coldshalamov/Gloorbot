from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    hostname: str
    version: str


class RegisterResponse(BaseModel):
    client_id: str


class HeartbeatRequest(BaseModel):
    client_id: str
    hostname: str
    version: str
    cpu_percent: float
    mem_percent: float
    slots: int
    tasks_completed: int
    deals_sent: int


class LeaseNextRequest(BaseModel):
    client_id: str
    preferred_store_id: str


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
    duration_sec: float
    products_seen: int
    deals_sent: int


class DealItem(BaseModel):
    store_id: str
    store_name: str
    category_url: str
    product_url: str
    title: str
    image_url: str
    price: float
    was_price: float
    pct_off: float = Field(ge=0.0, le=1.0)
    clearance: bool = Field(default=False)
    found_at: datetime | None = None


class DealsBulkRequest(BaseModel):
    client_id: str
    batch_id: str
    task_id: int
    deals: list[DealItem]


class BreadcrumbItem(BaseModel):
    text: str
    href: str


class CategoryMetaUpsertItem(BaseModel):
    category_url: str
    breadcrumbs: list[BreadcrumbItem] = Field(default_factory=list)


class CategoryMetaBulkRequest(BaseModel):
    items: list[CategoryMetaUpsertItem]


