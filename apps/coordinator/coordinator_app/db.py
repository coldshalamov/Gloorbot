from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase


class Base(DeclarativeBase):
    pass


def _default_sqlite_path() -> Path:
    # Render: mount a persistent disk and set DATA_DIR=/var/data (recommended).
    data_dir = Path(os.getenv("DATA_DIR", "")).expanduser()
    if str(data_dir).strip():
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "coordinator.sqlite"

    # Local/dev fallback
    here = Path(__file__).resolve().parents[1]
    local_data = here / ".data"
    local_data.mkdir(parents=True, exist_ok=True)
    return local_data / "coordinator.sqlite"


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", f"sqlite:///{_default_sqlite_path().as_posix()}")


engine = create_engine(
    get_database_url(),
    connect_args={"check_same_thread": False} if get_database_url().startswith("sqlite") else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


@contextmanager
def db_session() -> Iterator[Session]:
    """Context manager for database sessions with automatic cleanup."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

