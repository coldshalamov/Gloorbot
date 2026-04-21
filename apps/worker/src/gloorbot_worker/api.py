from __future__ import annotations

import os
import socket
import uuid
from dataclasses import dataclass
from typing import Literal

import requests

from . import __version__


def _requests_verify() -> str | bool:
    # Frozen Windows builds can lose requests' CA discovery unless the certifi
    # bundle is explicitly carried into the PyInstaller payload.
    try:
        import certifi

        ca_bundle = certifi.where()
        if ca_bundle:
            return ca_bundle
    except Exception:
        pass
    return True


def coordinator_url() -> str:
    url = os.getenv("GLOORBOT_COORDINATOR_URL", "").strip()
    if not url:
        return "https://gloorbot-coordinator.onrender.com"
    return url.rstrip("/")


@dataclass(frozen=True)
class Lease:
    task_id: int
    lease_seconds: int
    store_id: str
    store_name: str
    store_url: str
    category_url: str


HeartbeatResult = Literal["ok", "stale_client", "error"]


def register() -> str:
    res = requests.post(
        f"{coordinator_url()}/api/v1/client/register",
        json={"hostname": socket.gethostname(), "version": __version__},
        timeout=15,
        verify=_requests_verify(),
    )
    res.raise_for_status()
    return res.json()["client_id"]


def heartbeat(
    client_id: str,
    cpu_percent: float | None,
    mem_percent: float | None,
    slots: int | None,
    tasks_completed: int = 0,
    deals_sent: int = 0,
) -> HeartbeatResult:
    try:
        res = requests.post(
            f"{coordinator_url()}/api/v1/client/heartbeat",
            json={
                "client_id": client_id,
                "hostname": socket.gethostname(),
                "version": __version__,
                "cpu_percent": cpu_percent,
                "mem_percent": mem_percent,
                "slots": slots,
                "tasks_completed": int(tasks_completed),
                "deals_sent": int(deals_sent),
            },
            timeout=10,
            verify=_requests_verify(),
        )
        try:
            data = res.json()
        except Exception:
            data = None
        if res.status_code == 404:
            return "stale_client"
        if (
            isinstance(data, dict)
            and data.get("ok") is False
            and str(data.get("error") or "").strip().lower() == "unknown_client"
        ):
            return "stale_client"
        res.raise_for_status()
        return "ok"
    except requests.HTTPError as exc:
        response = getattr(exc, "response", None)
        if response is not None and response.status_code == 404:
            return "stale_client"
        return "error"
    except Exception:
        # Best-effort; worker must continue even if coordinator is flaky.
        return "error"


def lease_next(client_id: str, preferred_store_id: str | None) -> Lease | None:
    # Coordinator currently validates this field as a required string.
    # Normalize None to empty string so new slots can request their first task.
    preferred = preferred_store_id or ""
    res = requests.post(
        f"{coordinator_url()}/api/v1/lease/next",
        json={"client_id": client_id, "preferred_store_id": preferred},
        timeout=30,
        verify=_requests_verify(),
    )
    res.raise_for_status()
    data = res.json()
    if not data:
        return None
    return Lease(**data)


def lease_complete(
    client_id: str,
    task_id: int,
    duration_sec: float | None,
    products_seen: int,
    deals_sent: int,
    *,
    scan_status: str | None = None,
) -> None:
    requests.post(
        f"{coordinator_url()}/api/v1/lease/complete",
        json={
            "client_id": client_id,
            "task_id": task_id,
            "duration_sec": duration_sec,
            "products_seen": products_seen,
            "deals_sent": deals_sent,
            "scan_status": scan_status,
        },
        timeout=15,
        verify=_requests_verify(),
    ).raise_for_status()


def lease_fail(client_id: str, task_id: int, duration_sec: float | None) -> None:
    try:
        requests.post(
            f"{coordinator_url()}/api/v1/lease/fail",
            json={"client_id": client_id, "task_id": task_id, "duration_sec": duration_sec},
            timeout=15,
            verify=_requests_verify(),
        ).raise_for_status()
    except Exception:
        pass


def submit_deals(client_id: str, deals: list[dict], *, task_id: int | None = None) -> tuple[int, str]:
    if not deals:
        return 0, ""
    batch_id = uuid.uuid4().hex[:16]
    res = requests.post(
        f"{coordinator_url()}/api/v1/deals/bulk",
        json={"client_id": client_id, "batch_id": batch_id, "task_id": task_id, "deals": deals},
        timeout=30,
        verify=_requests_verify(),
    )
    res.raise_for_status()
    data = res.json()
    return int(data.get("accepted", 0)), str(data.get("batch_id") or batch_id)


def fetch_status() -> dict | None:
    try:
        res = requests.get(
            f"{coordinator_url()}/api/v1/status",
            timeout=10,
            verify=_requests_verify(),
        )
        if not res.ok:
            return None
        return res.json()
    except Exception:
        return None
