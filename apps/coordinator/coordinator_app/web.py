from __future__ import annotations

import asyncio
import threading
import statistics
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func, and_, or_, update

from .db import db_session
from .models import Client, Task, Deal
from .schemas import (
    RegisterRequest,
    RegisterResponse,
    HeartbeatRequest,
    LeaseNextRequest,
    LeaseResponse,
    LeaseCompleteRequest,
    DealsBulkRequest,
)
from .seed import seed_tasks_from_parallel_urls, create_tables


LEASE_SECONDS = int(os.getenv("LEASE_SECONDS", "900"))  # 15 minutes default
ACTIVE_WINDOW_SECONDS = int(os.getenv("ACTIVE_WINDOW_SECONDS", "180"))  # 3 minutes
DEAL_THRESHOLD = float(os.getenv("DEAL_THRESHOLD", "0.50"))
MAX_DEALS_PER_BATCH = int(os.getenv("MAX_DEALS_PER_BATCH", "500"))

base_dir = Path(__file__).resolve().parents[1]  # apps/coordinator

# In Docker, the path may be shallow (/app), so handle IndexError gracefully.
# seed.py checks data/urls.txt locally first anyway.
try:
    repo_root = base_dir.parents[1]
except IndexError:
    repo_root = base_dir

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
    return os.getenv("WORKER_DOWNLOAD_URL")


def create_app() -> FastAPI:
    app = FastAPI(title="Gloorbot Coordinator")

    app.mount("/static", StaticFiles(directory=str(base_dir / "static")), name="static")

    @app.on_event("startup")
    async def _startup() -> None:
        bus.set_loop(asyncio.get_running_loop())
        create_tables()
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
        url = _download_url()
        if not url:
            return PlainTextResponse("WORKER_DOWNLOAD_URL not configured on server.", status_code=404)
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
        upserts = 0
        with db_session() as db:
            for d in req.deals:
                if d.pct_off < DEAL_THRESHOLD:
                    continue
                existing = db.execute(
                    select(Deal).where(and_(Deal.store_id == d.store_id, Deal.product_url == d.product_url))
                ).scalars().first()
                if existing:
                    existing.title = d.title
                    existing.store_name = d.store_name
                    existing.category_url = d.category_url
                    existing.price = d.price
                    existing.was_price = d.was_price
                    existing.pct_off = d.pct_off
                    existing.last_seen_at = now
                    existing.seen_count += 1
                    existing.last_client_id = req.client_id
                else:
                    db.add(
                        Deal(
                            store_id=d.store_id,
                            store_name=d.store_name,
                            category_url=d.category_url,
                            product_url=d.product_url,
                            title=d.title,
                            price=d.price,
                            was_price=d.was_price,
                            pct_off=d.pct_off,
                            first_seen_at=now,
                            last_seen_at=now,
                            seen_count=1,
                            last_client_id=req.client_id,
                        )
                    )
                upserts += 1
            db.commit()

        if upserts:
            bus.publish(f"event:deals\ndata:{{\"type\":\"deals\",\"count\":{upserts}}}\n\n")
        return {"ok": True, "accepted": upserts}

    async def _sse_stream() -> AsyncIterator[bytes]:
        yield b":ok\n\n"
        async for event in bus.subscribe():
            yield event.encode("utf-8")

    @app.get("/api/v1/events", response_model=None)
    async def events() -> StreamingResponse:
        return StreamingResponse(_sse_stream(), media_type="text/event-stream")

    return app
