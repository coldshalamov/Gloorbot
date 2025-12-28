from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_hostname: Mapped[str | None] = mapped_column(String(256), nullable=True)
    last_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    last_cpu_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_mem_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_slots: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("store_id", "category_url", name="uq_task_store_category"),
        Index("idx_tasks_lease", "lease_expires_at"),
        Index("idx_tasks_last_done", "last_completed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    state: Mapped[str] = mapped_column(String(8), nullable=False)
    store_id: Mapped[str] = mapped_column(String(16), nullable=False)
    store_name: Mapped[str] = mapped_column(String(256), nullable=False)
    store_url: Mapped[str] = mapped_column(String(1024), nullable=False)

    category_url: Mapped[str] = mapped_column(String(2048), nullable=False)

    last_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_client_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    lease_client_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    completed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Deal(Base):
    __tablename__ = "deals"
    __table_args__ = (
        UniqueConstraint("store_id", "product_url", name="uq_deal_store_product"),
        Index("idx_deals_last_seen", "last_seen_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(String(16), nullable=False)
    store_name: Mapped[str] = mapped_column(String(256), nullable=False)
    category_url: Mapped[str] = mapped_column(String(2048), nullable=True)

    product_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str] = mapped_column(String(2048), nullable=False)

    price: Mapped[float] = mapped_column(Float, nullable=False)
    was_price: Mapped[float] = mapped_column(Float, nullable=False)
    pct_off: Mapped[float] = mapped_column(Float, nullable=False)

    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    seen_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_client_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

