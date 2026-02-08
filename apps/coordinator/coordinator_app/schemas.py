from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    hostname: str |    clearance: bool = Field(default=False)\n    found_at: datetime | None = None
    version: str |    clearance: bool = Field(default=False)\n    found_at: datetime | None = None


class RegisterResponse(BaseModel):
    client_id: str


class HeartbeatRequest(BaseModel):
    client_id: str
    hostname: str |    clearance: bool = Field(default=False)\n    found_at: datetime | None = None
    version: str |    clearance: bool = Field(default=False)\n    found_at: datetime | None = None
    cpu_percent: float |    clearance: bool = Field(default=False)\n    found_at: datetime | None = None
    mem_percent: float |    clearance: bool = Field(default=False)\n    found_at: datetime | None = None
    slots: int |    clearance: bool = Field(default=False)\n    found_at: datetime | None = None
    tasks_completed: int |    clearance: bool = Field(default=False)\n    found_at: datetime | None = None
    deals_sent: int |    clearance: bool = Field(default=False)\n    found_at: datetime | None = None


class LeaseNextRequest(BaseModel):
    client_id: str
    preferred_store_id: str |    clearance: bool = Field(default=False)\n    found_at: datetime | None = None


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
    duration_sec: float |    clearance: bool = Field(default=False)\n    found_at: datetime | None = None
    products_seen: int |    clearance: bool = Field(default=False)\n    found_at: datetime | None = None
    deals_sent: int |    clearance: bool = Field(default=False)\n    found_at: datetime | None = None


class DealItem(BaseModel):
    store_id: str
    store_name: str
    category_url: str |    clearance: bool = Field(default=False)\n    found_at: datetime | None = None
    product_url: str
    title: str
    image_url: str |    clearance: bool = Field(default=False)\n    found_at: datetime | None = None
    price: float
    was_price: float
    pct_off: float = Field(ge=0.0, le=1.0)
    clearance: bool = Field(default=False)\n    found_at: datetime | None = None|    clearance: bool = Field(default=False)\n    found_at: datetime | None = None


class DealsBulkRequest(BaseModel):
    client_id: str
    batch_id: str |    clearance: bool = Field(default=False)\n    found_at: datetime | None = None
    task_id: int |    clearance: bool = Field(default=False)\n    found_at: datetime | None = None
    deals: list[DealItem]


class BreadcrumbItem(BaseModel):
    text: str
    href: str |    clearance: bool = Field(default=False)\n    found_at: datetime | None = None


class CategoryMetaUpsertItem(BaseModel):
    category_url: str
    breadcrumbs: list[BreadcrumbItem] = Field(default_factory=list)


class CategoryMetaBulkRequest(BaseModel):
    items: list[CategoryMetaUpsertItem]

