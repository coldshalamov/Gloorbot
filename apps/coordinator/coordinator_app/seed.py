from __future__ import annotations

import os
import re
from pathlib import Path

from sqlalchemy import select, inspect, text, delete

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
        # 2. Fallback to standard locations
        # Render builds often use `apps/coordinator` as the build context, so ship a copy here.
        local_urls = Path(__file__).resolve().parents[1] / "data" / "urls.txt"
        urls_path = local_urls if local_urls.exists() else (repo_root / "PARALLEL" / "urls.txt")
    
    if not urls_path.exists():
        raise FileNotFoundError(f"Expected urls.txt at {urls_path} or {repo_root / 'PARALLEL' / 'urls.txt'}")

    stores, categories = _load_urls_file(urls_path)
    # The list is now filtered by the Admin store selector before being written to urls.txt,
    # so we can accept whatever is in the file.

    create_tables()

    inserted = 0
    with db_session() as db:
        # Safety: purge any legacy /c/ category tasks (they are non-listing pages and will
        # cause workers to spin/retry forever when the pickup filter UI doesn't match).
        try:
            pruned_c = db.execute(delete(Task).where(Task.category_url.like("%/c/%"))).rowcount
            if pruned_c:
                print(f"[seed] pruned_tasks_c_category={pruned_c}")
        except Exception:
            pass

        existing = set(db.execute(select(Task.store_id, Task.category_url)).all())
        # CRITICAL: Insert category-major (not store-major) to prevent store clustering
        # Old order (store → categories) caused all early tasks to be for store #1
        # New order (categories → stores) interleaves tasks across stores
        for category_url in categories:
            for store in stores:
                key = (store["store_id"], category_url)
                if key in existing:
                    continue
                db.add(
                    Task(
                        state=store["state"],
                        store_id=store["store_id"],
                        store_name=store["name"],
                        store_url=store["url"],
                        category_url=category_url,
                    )
                )
                inserted += 1
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
