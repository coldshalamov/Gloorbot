from __future__ import annotations

import asyncio
import logging
import threading
import statistics
import os
import secrets
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import AsyncIterator

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func, and_, or_, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .db import db_session
from .category_breadcrumbs import Breadcrumb, breadcrumb_leaf_name, breadcrumb_path
from .category_name import extract_category_name
from .models import Client, Task, Deal, DealSource, IngestEvent, CategoryMeta
from .schemas import (
    RegisterRequest,
    RegisterResponse,
    HeartbeatRequest,
    LeaseNextRequest,
    LeaseResponse,
    LeaseCompleteRequest,
    DealsBulkRequest,
    CategoryMetaBulkRequest,
)
from .seed import seed_tasks_from_parallel_urls, create_tables
from .admin_auth import verify_credentials, create_session, verify_session, invalidate_session
from .store_config import get_store_config_manager


LEASE_SECONDS = int(os.getenv("LEASE_SECONDS", "900"))  # 15 minutes default
ACTIVE_WINDOW_SECONDS = int(os.getenv("ACTIVE_WINDOW_SECONDS", "180"))  # 3 minutes
DEAL_THRESHOLD = float(os.getenv("DEAL_THRESHOLD", "0.50"))
MAX_DEALS_PER_BATCH = int(os.getenv("MAX_DEALS_PER_BATCH", "500"))

# Cheapskater integration - forward deals to the Cheapskater website
CHEAPSKATER_INGEST_URL = os.getenv("CHEAPSKATER_INGEST_URL", "")
CHEAPSKATER_INGEST_API_KEY = os.getenv("CHEAPSKATER_INGEST_API_KEY", "")

DEBUG_API_TOKEN = os.getenv("DEBUG_API_TOKEN", "")
DEBUG_RETENTION_DAYS = int(os.getenv("DEBUG_RETENTION_DAYS", "3"))

logger = logging.getLogger(__name__)

# HTTP client for forwarding to Cheapskater (reused for connection pooling)     
_http_client: httpx.Client | None = None

_worker_download_url_cache: str | None = None
_worker_download_url_cache_at: float | None = None

_last_debug_cleanup_at: datetime | None = None


def _get_http_client() -> httpx.Client:
    global _http_client
    if _http_client is None:
        _http_client = httpx.Client(timeout=10.0)
    return _http_client


def _forward_deals_to_cheapskater(
    deals: list[dict],
    *,
    batch_id: str | None = None,
    client_id: str | None = None,
) -> dict:
    """Forward deals to Cheapskater website (best-effort, non-blocking)."""
    if not CHEAPSKATER_INGEST_URL or not deals:
        if not CHEAPSKATER_INGEST_URL:
            logger.warning("CHEAPSKATER_INGEST_URL not configured - deals will not be forwarded")
        return {"attempted": False, "status_code": None, "accepted": 0, "error": "not_configured"}

    logger.info(
        "[FORWARD] batch_id=%s client_id=%s attempting count=%s url_configured=%s",
        batch_id,
        client_id,
        len(deals),
        bool(CHEAPSKATER_INGEST_URL),
    )
    try:
        client = _get_http_client()
        headers = {}
        if CHEAPSKATER_INGEST_API_KEY:
            headers["X-API-Key"] = CHEAPSKATER_INGEST_API_KEY
        if batch_id:
            headers["X-Gloorbot-Batch-Id"] = batch_id
        if client_id:
            headers["X-Gloorbot-Client-Id"] = client_id

        payload = {
            "source": "gloorbot",
            "batch_id": batch_id,
            "client_id": client_id,
            "deals": deals,
        }

        resp = client.post(CHEAPSKATER_INGEST_URL, json=payload, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            logger.info(
                "[FORWARD] batch_id=%s client_id=%s ok accepted=%s",
                batch_id,
                client_id,
                data.get("accepted", 0),
            )
            return {
                "attempted": True,
                "status_code": resp.status_code,
                "accepted": int(data.get("accepted", 0) or 0),
                "error": None,
            }
        else:
            logger.warning(
                "[FORWARD] batch_id=%s client_id=%s failed status=%s body=%s",
                batch_id,
                client_id,
                resp.status_code,
                resp.text[:200],
            )
            return {
                "attempted": True,
                "status_code": resp.status_code,
                "accepted": 0,
                "error": f"{resp.status_code}: {resp.text[:200]}",
            }
    except Exception as e:
        logger.warning("[FORWARD] batch_id=%s client_id=%s exception=%s", batch_id, client_id, e)
        return {"attempted": True, "status_code": None, "accepted": 0, "error": str(e)[:200]}


def _require_debug_token(request: Request) -> None:
    if not DEBUG_API_TOKEN:
        raise HTTPException(status_code=404, detail="debug endpoints disabled")
    provided = request.headers.get("x-debug-token") or ""
    if provided != DEBUG_API_TOKEN:
        raise HTTPException(status_code=401, detail="invalid debug token")


def _maybe_cleanup_debug_tables(*, force: bool = False) -> None:
    global _last_debug_cleanup_at
    now = datetime.utcnow()
    if not force and _last_debug_cleanup_at and (now - _last_debug_cleanup_at) < timedelta(hours=1):
        return

    cutoff = now - timedelta(days=DEBUG_RETENTION_DAYS)
    with db_session() as db:
        db.execute(delete(IngestEvent).where(IngestEvent.created_at < cutoff))
        db.execute(delete(DealSource).where(DealSource.last_seen_at < cutoff))
        db.commit()
    _last_debug_cleanup_at = now


base_dir = Path(__file__).resolve().parents[1]  # apps/coordinator

# In Docker, the path may be shallow (/app), so handle IndexError gracefully.
# seed.py checks data/urls.txt locally first anyway.
try:
    repo_root = base_dir.parents[1]
except IndexError:
    repo_root = base_dir

# Persistent data directory (for Render/Docker)
DATA_DIR = os.getenv("DATA_DIR", "").strip()
if DATA_DIR:
    persistent_data_dir = Path(DATA_DIR).expanduser()
else:
    persistent_data_dir = base_dir / "data"

try:
    persistent_data_dir.mkdir(parents=True, exist_ok=True)
except Exception as e:
    logger.warning(f"Could not create persistent data dir {persistent_data_dir}: {e}")

templates = Jinja2Templates(directory=str(base_dir / "templates"))


class EventBus:
    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()
        self._subs: set[asyncio.Queue[str]] = set()

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def publish(self, event: str) -> None:
        # Endpoints may run in a threadpool; marshal publishing onto the main loop.
        if not self._loop:
            return
        self._loop.call_soon_threadsafe(self._publish_in_loop, event)

    def _publish_in_loop(self, event: str) -> None:
        with self._lock:
            targets = list(self._subs)
        for q in targets:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # Drop for slow subscribers; dashboard can refresh via polling.
                pass

    async def subscribe(self) -> AsyncIterator[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=200)
        with self._lock:
            self._subs.add(q)
        try:
            while True:
                event = await q.get()
                yield event
        finally:
            with self._lock:
                self._subs.discard(q)


bus = EventBus()


def _download_url() -> str | None:
    value = (os.getenv("WORKER_DOWNLOAD_URL", "") or "").strip()
    if not value:
        return None
    # Allow opting into GitHub "latest" resolution without changing code.
    if value.lower() in {"latest", "github:latest", "github-latest"}:
        return None
    return value

def _github_worker_repo() -> str:
    # Format: "owner/repo"
    return os.getenv("WORKER_GITHUB_REPO", "coldshalamov/Gloorbot").strip()


def _resolve_worker_download_url() -> str | None:
    """
    Resolve the URL for the current WorkerSetup.exe installer.

    Priority:
    1) WORKER_DOWNLOAD_URL (explicit override; recommended for production)
    2) GitHub Releases latest asset lookup (best-effort fallback)
    """

    explicit = _download_url()
    if explicit:
        return explicit

    global _worker_download_url_cache, _worker_download_url_cache_at
    now = time.time()
    if _worker_download_url_cache and _worker_download_url_cache_at and (now - _worker_download_url_cache_at) < 15 * 60:
        return _worker_download_url_cache

    repo = _github_worker_repo()
    if not repo or "/" not in repo:
        return None

    try:
        client = _get_http_client()
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "gloorbot-coordinator",
        }
        resp = client.get(f"https://api.github.com/repos/{repo}/releases/latest", headers=headers)
        if resp.status_code != 200:
            return None
        data = resp.json()
        assets = data.get("assets") if isinstance(data, dict) else None
        if not isinstance(assets, list):
            return None

        for asset in assets:
            if not isinstance(asset, dict):
                continue
            name = (asset.get("name") or "").strip()
            if name.lower() != "workersetup.exe":
                continue
            url = (asset.get("browser_download_url") or "").strip()
            if not url:
                continue
            _worker_download_url_cache = url
            _worker_download_url_cache_at = now
            return url
        return None
    except Exception:
        return None


def create_app() -> FastAPI:
    app = FastAPI(title="Gloorbot Coordinator")

    app.mount("/static", StaticFiles(directory=str(base_dir / "static")), name="static")

    @app.on_event("startup")
    async def _startup() -> None:
        bus.set_loop(asyncio.get_running_loop())
        create_tables()
        _maybe_cleanup_debug_tables(force=True)
        try:
            inserted = seed_tasks_from_parallel_urls(repo_root)
        except FileNotFoundError:
            inserted = 0
        if inserted:
            bus.publish(f"event:seed\ndata:{{\"tasks_inserted\":{inserted}}}\n\n")

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True, "utc": datetime.utcnow().isoformat()}

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        try:
            return templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "download_url": _download_url(),
                    "deal_threshold_pct": int(DEAL_THRESHOLD * 100),
                },
            )
        except Exception as e:
            return HTMLResponse(f"<pre>Template error: {e}\nbase_dir={base_dir}\ntemplates_dir={base_dir / 'templates'}</pre>", status_code=500)

    @app.get("/download", response_model=None)
    def download() -> Response:
        url = _resolve_worker_download_url()
        if not url:
            return PlainTextResponse(
                "Worker download not configured. Set WORKER_DOWNLOAD_URL, or set WORKER_GITHUB_REPO to enable GitHub fallback.",
                status_code=404,
            )
        return RedirectResponse(url=url, status_code=302)

    @app.get("/api/v1/status")
    def api_status() -> dict:
        now = datetime.utcnow()
        active_cutoff = now - timedelta(seconds=ACTIVE_WINDOW_SECONDS)
        with db_session() as db:
            total_tasks = db.scalar(select(func.count(Task.id))) or 0
            leased = (
                db.scalar(select(func.count(Task.id)).where(Task.lease_expires_at != None, Task.lease_expires_at >= now))  # noqa: E711
                or 0
            )
            done = db.scalar(select(func.count(Task.id)).where(Task.last_completed_at != None)) or 0  # noqa: E711
            completed_last_hour = (
                db.scalar(select(func.count(Task.id)).where(Task.last_completed_at >= now - timedelta(hours=1)))
                or 0
            )

            durations = db.execute(
                select(Task.last_duration_sec).where(Task.last_duration_sec != None)  # noqa: E711
            ).scalars().all()
            median_duration = statistics.median(durations) if durations else None

            active_clients = db.scalar(select(func.count(Client.id)).where(Client.last_seen_at >= active_cutoff)) or 0

            recent_deals = db.execute(
                select(Deal)
                .where(Deal.pct_off >= DEAL_THRESHOLD)
                .order_by(Deal.last_seen_at.desc())
                .limit(50)
            ).scalars().all()

            latest_ingest = db.execute(
                select(IngestEvent).order_by(IngestEvent.created_at.desc()).limit(1)
            ).scalars().first()

        return {
            "utc": now.isoformat(),
            "tasks": {
                "total": total_tasks,
                "leased": leased,
                "completed": done,
                "completed_last_hour": completed_last_hour,
                "median_duration_sec": median_duration,
            },
            "clients": {"active": active_clients},
            "integration": {
                "cheapskater_ingest_url_configured": bool(CHEAPSKATER_INGEST_URL),
                "cheapskater_ingest_api_key_configured": bool(CHEAPSKATER_INGEST_API_KEY),
                "debug_api_enabled": bool(DEBUG_API_TOKEN),
                "latest_ingest": (
                    {
                        "created_at": latest_ingest.created_at.isoformat(),
                        "batch_id": latest_ingest.batch_id,
                        "client_id": latest_ingest.client_id,
                        "task_id": latest_ingest.task_id,
                        "upserted": latest_ingest.upserted,
                        "forwarded_count": latest_ingest.forwarded_count,
                        "forward_status_code": latest_ingest.forward_status_code,
                        "forward_error": latest_ingest.forward_error,
                    }
                    if latest_ingest
                    else None
                ),
            },
            "recent_deals": [
                {
                    "store_id": d.store_id,
                    "store_name": d.store_name,
                    "product_url": d.product_url,
                    "title": d.title,
                    "price": d.price,
                    "was_price": d.was_price,
                    "pct_off": d.pct_off,
                    "last_seen_at": d.last_seen_at.isoformat(),
                }
                for d in recent_deals
            ],
        }

    @app.get("/api/v1/debug/task-url-stats")
    def debug_task_url_stats(request: Request, limit: int = 25) -> dict:
        """
        Debug helper: show whether any legacy non-listing `/c/` category URLs exist in tasks.

        Token-gated via DEBUG_API_TOKEN (same as other debug endpoints).
        """
        _require_debug_token(request)
        limit = max(1, min(int(limit), 200))
        now = datetime.utcnow()
        with db_session() as db:
            total = db.scalar(select(func.count(Task.id))) or 0
            c_count = db.scalar(select(func.count(Task.id)).where(Task.category_url.like("%/c/%"))) or 0
            pl_count = db.scalar(select(func.count(Task.id)).where(Task.category_url.like("%/pl/%"))) or 0
            leased_c = (
                db.scalar(
                    select(func.count(Task.id))
                    .where(Task.category_url.like("%/c/%"))
                    .where(Task.lease_expires_at != None, Task.lease_expires_at >= now)  # noqa: E711
                )
                or 0
            )
            examples = (
                db.execute(
                    select(Task.category_url, func.count(Task.id).label("n"))
                    .where(Task.category_url.like("%/c/%"))
                    .group_by(Task.category_url)
                    .order_by(func.count(Task.id).desc())
                    .limit(limit)
                )
                .all()
            )
        return {
            "utc": now.isoformat(),
            "tasks_total": total,
            "tasks_pl_count": pl_count,
            "tasks_c_count": c_count,
            "tasks_c_leased_count": leased_c,
            "tasks_c_examples": [{"category_url": url, "count": int(n)} for (url, n) in examples],
        }

    @app.get("/api/v1/debug/ingest-events")
    def debug_ingest_events(request: Request, limit: int = 100) -> dict:
        _require_debug_token(request)
        limit = max(1, min(int(limit), 500))
        with db_session() as db:
            events = db.execute(
                select(IngestEvent).order_by(IngestEvent.created_at.desc()).limit(limit)
            ).scalars().all()
        return {
            "ok": True,
            "events": [
                {
                    "id": e.id,
                    "created_at": e.created_at.isoformat(),
                    "batch_id": e.batch_id,
                    "client_id": e.client_id,
                    "task_id": e.task_id,
                    "received_count": e.received_count,
                    "unique_count": e.unique_count,
                    "below_threshold": e.below_threshold,
                    "upserted": e.upserted,
                    "forwarded_count": e.forwarded_count,
                    "forward_status_code": e.forward_status_code,
                    "forward_error": e.forward_error,
                }
                for e in events
            ],
        }

    @app.get("/api/v1/debug/deal-sources")
    def debug_deal_sources(request: Request, store_id: str, product_url: str, limit: int = 200) -> dict:
        _require_debug_token(request)
        limit = max(1, min(int(limit), 500))
        with db_session() as db:
            sources = db.execute(
                select(DealSource)
                .where(DealSource.store_id == store_id, DealSource.product_url == product_url)
                .order_by(DealSource.seen_count.desc(), DealSource.last_seen_at.desc())
                .limit(limit)
            ).scalars().all()
        return {
            "ok": True,
            "store_id": store_id,
            "product_url": product_url,
            "sources": [
                {
                    "category_url": s.category_url,
                    "seen_count": s.seen_count,
                    "first_seen_at": s.first_seen_at.isoformat(),
                    "last_seen_at": s.last_seen_at.isoformat(),
                    "last_client_id": s.last_client_id,
                    "last_batch_id": s.last_batch_id,
                    "last_task_id": s.last_task_id,
                }
                for s in sources
            ],
        }

    @app.post("/api/v1/debug/category-meta/bulk")
    def debug_category_meta_bulk(request: Request, req: CategoryMetaBulkRequest) -> dict:
        """
        Upsert category metadata derived from Lowe's breadcrumbs.

        Token-gated via DEBUG_API_TOKEN (same as other debug endpoints).
        Intended workflow:
        - Use dev-browser (warmed profile) to visit a /pl/ category URL
        - Extract breadcrumbs
        - POST them here to persist a robust (text-based) category_name
        """

        _require_debug_token(request)
        now = datetime.utcnow()
        upserted = 0
        with db_session() as db:
            for item in req.items:
                url = (item.category_url or "").strip()
                if not url:
                    continue
                crumbs = [Breadcrumb(text=c.text, href=c.href) for c in item.breadcrumbs]
                leaf = breadcrumb_leaf_name(crumbs)
                path = breadcrumb_path(crumbs)
                breadcrumbs_json = json.dumps(
                    [{"text": c.text, "href": c.href} for c in crumbs],
                    ensure_ascii=False,
                )
                base = sqlite_insert(CategoryMeta).values(
                    category_url=url,
                    category_name=leaf,
                    category_path=path,
                    breadcrumbs_json=breadcrumbs_json,
                    created_at=now,
                    updated_at=now,
                )
                stmt = base.on_conflict_do_update(
                    index_elements=[CategoryMeta.category_url],
                    set_={
                        CategoryMeta.category_name.key: base.excluded.category_name,
                        CategoryMeta.category_path.key: base.excluded.category_path,
                        CategoryMeta.breadcrumbs_json.key: base.excluded.breadcrumbs_json,
                        CategoryMeta.updated_at.key: now,
                    },
                )
                db.execute(stmt)
                upserted += 1
            db.commit()
        return {"ok": True, "upserted": upserted}

    @app.post("/api/v1/client/register", response_model=RegisterResponse)       
    def register(req: RegisterRequest, request: Request) -> RegisterResponse:
        client_id = secrets.token_urlsafe(16)
        now = datetime.utcnow()
        with db_session() as db:
            db.add(
                Client(
                    id=client_id,
                    created_at=now,
                    last_seen_at=now,
                    last_ip=request.client.host if request.client else None,
                    last_hostname=req.hostname,
                    last_version=req.version,
                )
            )
            db.commit()
        bus.publish(f"event:client\ndata:{{\"type\":\"register\",\"client_id\":\"{client_id}\"}}\n\n")
        return RegisterResponse(client_id=client_id)

    @app.post("/api/v1/client/heartbeat")
    def heartbeat(req: HeartbeatRequest, request: Request) -> dict:
        now = datetime.utcnow()
        with db_session() as db:
            client = db.get(Client, req.client_id)
            if not client:
                return {"ok": False, "error": "unknown_client"}
            client.last_seen_at = now
            client.last_ip = request.client.host if request.client else client.last_ip
            client.last_hostname = req.hostname or client.last_hostname
            client.last_version = req.version or client.last_version
            client.last_cpu_percent = req.cpu_percent
            client.last_mem_percent = req.mem_percent
            client.last_slots = req.slots
            db.commit()
        bus.publish(f"event:client\ndata:{{\"type\":\"heartbeat\",\"client_id\":\"{req.client_id}\"}}\n\n")
        return {"ok": True}

    @app.post("/api/v1/lease/next", response_model=LeaseResponse | None)
    def lease_next(req: LeaseNextRequest) -> LeaseResponse | None:
        now = datetime.utcnow()
        lease_until = now + timedelta(seconds=LEASE_SECONDS)
        with db_session() as db:
            db.query(Task).where(Task.lease_expires_at != None, Task.lease_expires_at < now).update(  # noqa: E711
                {Task.lease_expires_at: None, Task.lease_client_id: None}
            )
            db.commit()

            base_filter = and_(
                or_(Task.lease_expires_at == None, Task.lease_expires_at < now),  # noqa: E711
                # Never lease non-listing /c/ categories; they cause workers to spin.
                Task.category_url.not_like("%/c/%"),
            )

            query = select(Task).where(base_filter)
            if req.preferred_store_id:
                query = query.order_by((Task.store_id != req.preferred_store_id).asc())
            query = query.order_by(Task.last_completed_at.asc().nullsfirst(), Task.id.asc()).limit(1)

            # Lease atomically to avoid two workers getting the same task under concurrency.
            for _ in range(5):
                task = db.execute(query).scalars().first()
                if not task:
                    return None

                result = db.execute(
                    update(Task)
                    .where(
                        Task.id == task.id,
                        or_(Task.lease_expires_at == None, Task.lease_expires_at < now),  # noqa: E711
                    )
                    .values(
                        lease_client_id=req.client_id,
                        lease_expires_at=lease_until,
                        last_started_at=now,
                    )
                )
                if result.rowcount == 1:
                    db.commit()
                    leased_task = db.get(Task, task.id)
                    if not leased_task:
                        return None
                    return LeaseResponse(
                        task_id=leased_task.id,
                        lease_seconds=LEASE_SECONDS,
                        store_id=leased_task.store_id,
                        store_name=leased_task.store_name,
                        store_url=leased_task.store_url,
                        category_url=leased_task.category_url,
                    )

                db.rollback()

            return None

    @app.post("/api/v1/lease/complete")
    def lease_complete(req: LeaseCompleteRequest) -> dict:
        now = datetime.utcnow()
        with db_session() as db:
            task = db.get(Task, req.task_id)
            if not task:
                return {"ok": False, "error": "unknown_task"}
            if task.lease_client_id and task.lease_client_id != req.client_id:
                return {"ok": False, "error": "not_lease_holder"}

            task.lease_client_id = None
            task.lease_expires_at = None
            task.last_completed_at = now
            task.last_client_id = req.client_id
            task.last_duration_sec = req.duration_sec
            task.completed_count += 1
            db.commit()

        bus.publish(f"event:task\ndata:{{\"type\":\"complete\",\"task_id\":{req.task_id}}}\n\n")
        return {"ok": True}

    @app.post("/api/v1/lease/fail")
    def lease_fail(req: LeaseCompleteRequest) -> dict:
        with db_session() as db:
            task = db.get(Task, req.task_id)
            if not task:
                return {"ok": False, "error": "unknown_task"}
            if task.lease_client_id and task.lease_client_id != req.client_id:
                return {"ok": False, "error": "not_lease_holder"}

            task.lease_client_id = None
            task.lease_expires_at = None
            task.last_client_id = req.client_id
            task.error_count += 1
            db.commit()

        bus.publish(f"event:task\ndata:{{\"type\":\"fail\",\"task_id\":{req.task_id}}}\n\n")
        return {"ok": True}

    @app.post("/api/v1/deals/bulk")
    def deals_bulk(req: DealsBulkRequest) -> dict:
        if len(req.deals) > MAX_DEALS_PER_BATCH:
            raise HTTPException(status_code=413, detail="Too many deals in one request")
        now = datetime.utcnow()
        batch_id = getattr(req, "batch_id", None) or secrets.token_urlsafe(12)
        received_count = len(req.deals)
        upserts = 0
        below_threshold = 0
        rejected_suspicious = 0
        accepted_deals: list[dict] = []  # For forwarding to Cheapskater

        # Defensive: de-dupe deals within this request to avoid violating the
        # UNIQUE(store_id, product_url) constraint when multiple identical deals
        # arrive in one batch.
        unique_deals: dict[tuple[str, str], object] = {}
        for deal in req.deals:
            key = (deal.store_id, deal.product_url)
            existing = unique_deals.get(key)
            # Keep the "best" (highest pct_off) entry if duplicates exist.
            if existing is None or getattr(deal, "pct_off", 0) > getattr(existing, "pct_off", 0):
                unique_deals[key] = deal
        if len(unique_deals) != received_count:
            logger.info(
                "[DEALS] batch_id=%s client_id=%s dedupe %s -> %s unique",
                batch_id,
                req.client_id,
                received_count,
                len(unique_deals),
            )

        _maybe_cleanup_debug_tables()

        with db_session() as db:
            try:
                category_urls = {
                    d.category_url
                    for d in unique_deals.values()
                    if getattr(d, "category_url", None)
                }
                category_name_overrides: dict[str, str] = {}
                if category_urls:
                    rows = db.execute(
                        select(CategoryMeta.category_url, CategoryMeta.category_name).where(
                            CategoryMeta.category_url.in_(list(category_urls))
                        )
                    ).all()
                    category_name_overrides = {row[0]: row[1] for row in rows if row and row[0] and row[1]}

                for d in unique_deals.values():
                    # Track deals below threshold for metrics (no longer reject them)
                    if d.pct_off < DEAL_THRESHOLD:
                        below_threshold += 1

                    category_name = category_name_overrides.get(d.category_url or "") or extract_category_name(d.category_url)
                    base = sqlite_insert(Deal).values(
                        store_id=d.store_id,
                        store_name=d.store_name,
                        category_url=d.category_url,
                        category_name=category_name,
                        product_url=d.product_url,
                        title=d.title,
                        image_url=getattr(d, "image_url", None),
                        price=d.price,
                        was_price=d.was_price,
                        pct_off=d.pct_off,
                        first_seen_at=now,
                        last_seen_at=now,
                        seen_count=1,
                        last_client_id=req.client_id,
                    )
                    stmt = base.on_conflict_do_update(
                        index_elements=[Deal.store_id, Deal.product_url],
                        set_={
                            Deal.store_name.key: base.excluded.store_name,
                            Deal.category_url.key: base.excluded.category_url,
                            Deal.category_name.key: base.excluded.category_name,
                            Deal.title.key: base.excluded.title,
                            Deal.image_url.key: func.coalesce(base.excluded.image_url, Deal.image_url),
                            Deal.price.key: base.excluded.price,
                            Deal.was_price.key: base.excluded.was_price,
                            Deal.pct_off.key: base.excluded.pct_off,
                            Deal.last_seen_at.key: now,
                            Deal.seen_count.key: Deal.seen_count + 1,
                            Deal.last_client_id.key: req.client_id,
                        },
                    )
                    db.execute(stmt)
                    upserts += 1

                    category_url = d.category_url or "(missing)"
                    src_base = sqlite_insert(DealSource).values(
                        store_id=d.store_id,
                        product_url=d.product_url,
                        category_url=category_url,
                        first_seen_at=now,
                        last_seen_at=now,
                        seen_count=1,
                        last_client_id=req.client_id,
                        last_batch_id=batch_id,
                        last_task_id=getattr(req, "task_id", None),
                    )
                    src_stmt = src_base.on_conflict_do_update(
                        index_elements=[DealSource.store_id, DealSource.product_url, DealSource.category_url],
                        set_={
                            DealSource.last_seen_at.key: now,
                            DealSource.seen_count.key: DealSource.seen_count + 1,
                            DealSource.last_client_id.key: req.client_id,
                            DealSource.last_batch_id.key: batch_id,
                            DealSource.last_task_id.key: getattr(req, "task_id", None),
                        },
                    )
                    db.execute(src_stmt)

                    # Collect deal for Cheapskater forwarding
                    accepted_deals.append(
                        {
                            "store_id": d.store_id,
                            "store_name": d.store_name,
                            "category_url": d.category_url,
                            "category_name": category_name,
                            "product_url": d.product_url,
                            "title": d.title,
                            "image_url": getattr(d, "image_url", None),
                            "price": d.price,
                            "was_price": d.was_price,
                            "pct_off": d.pct_off,
                            "found_at": now.isoformat() + "Z",
                        }
                    )
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                logger.exception("[DEALS] batch_id=%s client_id=%s integrity_error=%s", batch_id, req.client_id, exc)
                raise HTTPException(status_code=500, detail="database integrity error") from exc

        logger.info(
            "[DEALS] batch_id=%s client_id=%s received=%s unique=%s below_threshold=%s rejected_suspicious=%s upserted=%s",
            batch_id,
            req.client_id,
            received_count,
            len(unique_deals),
            below_threshold,
            rejected_suspicious,
            upserts,
        )

        if upserts:
            bus.publish(f"event:deals\ndata:{{\"type\":\"deals\",\"count\":{upserts}}}\n\n")

        # Forward to Cheapskater (best-effort, non-blocking on failure)
        forward_result = {"attempted": False, "status_code": None, "accepted": 0, "error": None}
        if accepted_deals:
            forward_result = _forward_deals_to_cheapskater(accepted_deals, batch_id=batch_id, client_id=req.client_id)

        with db_session() as db:
            db.add(
                IngestEvent(
                    batch_id=batch_id,
                    client_id=req.client_id,
                    task_id=getattr(req, "task_id", None),
                    received_count=received_count,
                    unique_count=len(unique_deals),
                    below_threshold=below_threshold,
                    upserted=upserts,
                    forwarded_count=len(accepted_deals) if forward_result.get("attempted") else 0,
                    forward_status_code=forward_result.get("status_code"),
                    forward_error=forward_result.get("error"),
                )
            )
            db.commit()

        return {
            "ok": True,
            "accepted": upserts,
            "rejected_suspicious": rejected_suspicious,
            "batch_id": batch_id,
        }

    async def _sse_stream() -> AsyncIterator[bytes]:
        yield b":ok\n\n"
        async for event in bus.subscribe():
            yield event.encode("utf-8")

    @app.get("/api/v1/events", response_model=None)
    async def events() -> StreamingResponse:
        return StreamingResponse(_sse_stream(), media_type="text/event-stream")

    # ============================================================================
    # ADMIN ROUTES
    # ============================================================================

    @app.get("/admin/login", response_class=HTMLResponse)
    def admin_login_page(request: Request) -> HTMLResponse:
        """Render the admin login page."""
        return templates.TemplateResponse("admin_login.html", {"request": request})

    @app.get("/admin/dashboard", response_class=HTMLResponse)
    def admin_dashboard_page(request: Request) -> HTMLResponse:
        """Render the admin dashboard page."""
        return templates.TemplateResponse("admin_dashboard.html", {"request": request})

    @app.post("/admin/api/login")
    async def admin_login(request: Request) -> dict:
        """Admin login endpoint."""
        try:
            data = await request.json()
            email = data.get("email", "")
            password = data.get("password", "")
            
            if verify_credentials(email, password):
                token = create_session(email)
                return {"ok": True, "token": token}
            else:
                raise HTTPException(status_code=401, detail="Invalid credentials")
        except Exception as e:
            logger.error(f"Login error: {e}")
            raise HTTPException(status_code=400, detail="Invalid request")

    def _require_admin_auth(request: Request) -> None:
        """Verify admin authentication token."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        if not verify_session(token):
            raise HTTPException(status_code=401, detail="Invalid or expired session")

    @app.get("/admin/api/config")
    def admin_get_config(request: Request) -> dict:
        """Get current store configuration."""
        _require_admin_auth(request)
        
        config_manager = get_store_config_manager()
        return {
            "enabled_states": config_manager.get_enabled_states(),
            "enabled_stores": config_manager.config.get("enabled_stores", []),
            "all_stores": config_manager.get_all_stores_by_state(),
            "last_updated": config_manager.config.get("last_updated"),
        }

    @app.post("/admin/api/config")
    async def admin_save_config(request: Request) -> dict:
        """Save store configuration."""
        _require_admin_auth(request)
        
        try:
            data = await request.json()
            
            enabled_states = data.get("enabled_states", [])
            enabled_stores = data.get("enabled_stores", [])
            
            config_manager = get_store_config_manager()
            config_manager.set_enabled_states(enabled_states)
            
            # Generate new urls.txt file
            urls_content = config_manager.generate_urls_txt()
            
            # Save to PARALLEL/urls.txt (Works on local dev, might fail on Render)
            try:
                parallel_urls_path = repo_root / "PARALLEL" / "urls.txt"
                parallel_urls_path.parent.mkdir(parents=True, exist_ok=True)
                with open(parallel_urls_path, 'w') as f:
                    f.write(urls_content)
            except Exception as e:
                logger.warning(f"Could not write to PARALLEL/urls.txt (expected on Render): {e}")
            
            # Save to persistent data directory (Crucial for state persistence)
            try:
                data_urls_path = persistent_data_dir / "urls.txt"
                with open(data_urls_path, 'w') as f:
                    f.write(urls_content)
            except Exception as e:
                logger.error(f"Failed to write to persistent data directory: {e}")
            
            logger.info(f"Admin config saved: {len(enabled_states)} states, {len(enabled_stores)} specific stores")
            
            # CRITICAL: Clear ALL existing tasks so workers immediately get the new configuration
            # Without this, workers would continue processing old WA/OR tasks even after switching to FL
            with db_session() as db:
                old_task_count = db.scalar(select(func.count(Task.id))) or 0
                if old_task_count > 0:
                    logger.info(f"Clearing {old_task_count} old tasks to apply new configuration")
                    db.execute(delete(Task))
                    db.commit()
                    logger.info("Old tasks cleared successfully")
            
            # Re-seed tasks from the new configuration
            try:
                # Tell seeder to look in our persistent directory first
                os.environ["LOCAL_URLS_PATH"] = str(data_urls_path)
                inserted = seed_tasks_from_parallel_urls(repo_root)
                logger.info(f"Re-seeded {inserted} tasks from new configuration")
                
                # Notify all connected workers via event bus
                bus.publish(f"event:config\\ndata:{{\\\"type\\\":\\\"config_updated\\\",\\\"tasks_inserted\\\":{inserted}}}\\n\\n")
            except Exception as e:
                logger.error(f"Failed to re-seed tasks: {e}")
                raise HTTPException(status_code=500, detail=f"Config saved but failed to update tasks: {str(e)}")
            
            return {
                "ok": True,
                "enabled_states": enabled_states,
                "enabled_stores": enabled_stores,
                "urls_generated": True,
                "tasks_cleared": old_task_count,
                "tasks_inserted": inserted,
            }
        except Exception as e:
            logger.exception("Config save error")
            raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

    @app.post("/admin/api/config/reset")
    async def admin_reset_config(request: Request) -> dict:
        """Reset configuration to default (WA/OR)."""
        _require_admin_auth(request)
        
        config_manager = get_store_config_manager()
        config_manager.set_enabled_states(["WA", "OR"])
        config_manager.set_enabled_stores([])
        
        # Generate new urls.txt file
        urls_content = config_manager.generate_urls_txt()
        
        # Save to PARALLEL/urls.txt
        try:
            parallel_urls_path = repo_root / "PARALLEL" / "urls.txt"
            parallel_urls_path.parent.mkdir(parents=True, exist_ok=True)
            with open(parallel_urls_path, 'w') as f:
                f.write(urls_content)
        except Exception as e:
            logger.warning(f"Could not reset PARALLEL/urls.txt: {e}")
            
        # Save to persistent data directory
        try:
            data_urls_path = persistent_data_dir / "urls.txt"
            with open(data_urls_path, 'w') as f:
                f.write(urls_content)
        except Exception as e:
            logger.error(f"Failed to write to persistent data directory during reset: {e}")
        
        logger.info("Admin config reset to default (WA/OR)")
        
        # Re-seed tasks
        try:
            inserted = seed_tasks_from_parallel_urls(repo_root)
            logger.info(f"Re-seeded {inserted} tasks after reset")
        except Exception as e:
            logger.warning(f"Failed to re-seed tasks: {e}")
        
        return {"ok": True, "reset": True}

    @app.post("/admin/api/logout")
    def admin_logout(request: Request) -> dict:
        """Logout admin session."""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            invalidate_session(token)
        return {"ok": True}

    return app
