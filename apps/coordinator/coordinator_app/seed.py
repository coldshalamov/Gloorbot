from __future__ import annotations

import os
import re
from pathlib import Path

from sqlalchemy import select, inspect, text, delete, func
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .db import Base, engine, db_session
from .models import Task


_STORE_RE = re.compile(r"/store/([A-Z]{2})-([^/]+)/(\d+)")


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)

    # Lightweight SQLite migrations (Render often reuses an existing persistent DB).
    # We avoid a full migration framework here and only do additive schema updates.
    try:
        if not str(engine.url).startswith("sqlite"):
            return
        inspector = inspect(engine)
        if not inspector.has_table("deals"):
            return
        deal_cols = {c.get("name") for c in inspector.get_columns("deals")}
        if "image_url" not in deal_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE deals ADD COLUMN image_url VARCHAR(2048)"))
        if "category_name" not in deal_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE deals ADD COLUMN category_name VARCHAR(256)"))
        # Keep indexes best-effort as well (CREATE INDEX is idempotent in SQLite
        # when using IF NOT EXISTS).
        with engine.begin() as conn:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_deals_category_name ON deals(category_name)"))

        # category_meta table was added later; ensure it exists on older persistent DBs.
        if not inspector.has_table("category_meta"):
            Base.metadata.create_all(bind=engine)
    except Exception:
        # Never crash startup due to a best-effort migration.
        return


def _load_urls_file(path: Path) -> tuple[list[dict], list[str]]:
    stores: list[dict] = []
    categories: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "/store/" in line:
            match = _STORE_RE.search(line)
            if match:
                state, city_slug, store_id = match.groups()
                stores.append(
                    {
                        "url": line,
                        "store_id": store_id,
                        "city": city_slug.replace("-", " "),
                        "state": state,
                        "name": f"{city_slug.replace('-', ' ').title()}, {state} (#{store_id})",
                    }
                )
        elif "/pl/" in line and "the-back-aisle" not in line.lower():
            categories.append(line)
    return stores, categories


def seed_tasks_from_parallel_urls(repo_root: Path) -> int:
    """
    Seed tasks for stores x category URLs.
    Idempotent: only inserts missing (store_id, category_url) pairs.
    """
    # 1. Check for explicit path override (set by admin config saver)
    env_path = os.environ.get("LOCAL_URLS_PATH")
    if env_path and Path(env_path).exists():
        urls_path = Path(env_path)
    else:
        # 2. Check persistent data directory (Render/Docker)
        data_dir = os.getenv("DATA_DIR", "").strip()
        if data_dir:
            persist_urls = Path(data_dir).expanduser() / "urls.txt"
        else:
            # Sibling to code in Render context often works
            persist_urls = Path(__file__).resolve().parents[1] / "data" / "urls.txt"
            
        if persist_urls.exists():
            urls_path = persist_urls
        else:
            # 3. Fallback to repository root (local dev)
            urls_path = repo_root / "PARALLEL" / "urls.txt"
    
    if not urls_path.exists():
        # Final fallback - maybe we are inside the app directory
        alt_path = Path(__file__).resolve().parents[1] / "PARALLEL" / "urls.txt"
        if alt_path.exists():
            urls_path = alt_path
        else:
            raise FileNotFoundError(f"Expected urls.txt at {urls_path} or {repo_root / 'PARALLEL' / 'urls.txt'}")
    

    stores, categories = _load_urls_file(urls_path)
    # The list is now filtered by the Admin store selector before being written to urls.txt,
    # so we can accept whatever is in the file.

    create_tables()

    chunk_size = max(100, int(os.getenv("SEED_INSERT_CHUNK_SIZE", "1000")))
    with db_session() as db:
        # Safety: purge any legacy /c/ category tasks (they are non-listing pages and will
        # cause workers to spin/retry forever when the pickup filter UI doesn't match).
        try:
            pruned_c = db.execute(delete(Task).where(Task.category_url.like("%/c/%"))).rowcount
            if pruned_c:
                print(f"[seed] pruned_tasks_c_category={pruned_c}")
        except Exception:
            pass

        before_insert_total = db.scalar(select(func.count(Task.id))) or 0
        # Memory-safe seeding: avoid loading all existing task keys into Python
        # (this can OOM small Render instances on large persistent DBs).
        insert_stmt = sqlite_insert(Task).prefix_with("OR IGNORE")
        rows: list[dict] = []

        # Insert category-major (not store-major) to prevent store clustering.
        for category_url in categories:
            for store in stores:
                rows.append(
                    {
                        "state": store["state"],
                        "store_id": store["store_id"],
                        "store_name": store["name"],
                        "store_url": store["url"],
                        "category_url": category_url,
                    }
                )
                if len(rows) >= chunk_size:
                    db.execute(insert_stmt, rows)
                    rows.clear()

        if rows:
            db.execute(insert_stmt, rows)
        after_insert_total = db.scalar(select(func.count(Task.id))) or 0
        inserted = max(0, int(after_insert_total - before_insert_total))
        # Optional safety: if the seed list changes (e.g. we remove confirmed 404 categories),
        # purge tasks that can never succeed so workers stop getting handed dead URLs.
        prune_flag = os.getenv("PRUNE_TASKS_NOT_IN_SEED", "true").strip().lower() not in {"0", "false", "no", "off"}
        if prune_flag and categories:
            keep = set(categories)
            # Prune tasks that are no longer in our seed list (helps if category URLs change)
            pruned = db.execute(
                delete(Task).where(~Task.category_url.in_(keep))
            ).rowcount
            if pruned:
                # Prints are OK here; Render captures stdout and this is a rare, high-signal event.
                print(f"[seed] pruned_tasks_not_in_seed={pruned}")
        db.commit()
    return inserted
