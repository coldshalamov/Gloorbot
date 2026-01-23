"""
Structured JSON logging to make diagnostics visible on Render.

Logs are written to:
1. Standard Python logger (visible in Render dashboard)
2. Local JSON log file at /var/logs/gloorbot-structured.jsonl (persistent on Render)
3. Memory buffer for in-app diagnostics

This allows us to see exactly what's happening with worker delegation,
browser crashes, and task assignment without guessing.
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any


# Setup structured logging directory
def get_log_dir() -> Path:
    """Get the log directory, creating it if needed."""
    # On Render, use /var/logs/ which persists across restarts
    # Locally, use ./logs/
    if os.getenv("RENDER") == "true":
        log_dir = Path("/var/logs")
    else:
        log_dir = Path("./logs")

    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def structured_log(
    event: str,
    level: str = "info",
    **data: Any,
) -> None:
    """
    Write a structured JSON log entry.

    Args:
        event: Event name (e.g., "worker_crash", "task_delegation", "browser_restart")
        level: Log level ("info", "warning", "error", "debug")
        **data: Additional contextual data
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event,
        "level": level.upper(),
        **data,
    }

    # Write to JSON log file
    try:
        log_file = get_log_dir() / "gloorbot-structured.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, separators=(",", ":")) + "\n")
    except Exception as e:
        logging.error(f"Failed to write structured log: {e}")

    # Also log via standard Python logger
    logger = logging.getLogger("gloorbot.structured")
    log_message = f"[{event}] {json.dumps(data, separators=(',', ':'))}"

    if level == "error":
        logger.error(log_message)
    elif level == "warning":
        logger.warning(log_message)
    elif level == "debug":
        logger.debug(log_message)
    else:
        logger.info(log_message)


def log_worker_crash(
    slot_id: int,
    store_id: str,
    store_name: str,
    category_url: str,
    error: str,
    page_title: str | None = None,
    page_url: str | None = None,
    browser_state: str | None = None,
) -> None:
    """Log a worker browser crash with full context."""
    structured_log(
        "worker_browser_crash",
        level="error",
        slot_id=slot_id,
        store_id=store_id,
        store_name=store_name,
        category_url=category_url[:200] if category_url else None,
        error=str(error)[:500],
        page_title=page_title,
        page_url=page_url[:200] if page_url else None,
        browser_state=browser_state,
    )


def log_task_delegation(
    slot_id: int,
    task_id: str,
    store_id: str,
    store_name: str,
    category_url: str,
    status: str,  # "assigned", "started", "completed", "failed"
    duration_seconds: float | None = None,
    products_found: int | None = None,
    error: str | None = None,
) -> None:
    """Log task delegation and progress."""
    structured_log(
        "task_delegation",
        level="info",
        slot_id=slot_id,
        task_id=task_id,
        store_id=store_id,
        store_name=store_name,
        category_url=category_url[:200] if category_url else None,
        status=status,
        duration_seconds=duration_seconds,
        products_found=products_found,
        error=str(error)[:500] if error else None,
    )


def log_worker_heartbeat(
    slot_id: int,
    client_id: str,
    tasks_completed: int,
    tasks_active: int,
    browser_alive: bool,
    memory_mb: int | None = None,
) -> None:
    """Log worker heartbeat/health status."""
    structured_log(
        "worker_heartbeat",
        level="debug",
        slot_id=slot_id,
        client_id=client_id,
        tasks_completed=tasks_completed,
        tasks_active=tasks_active,
        browser_alive=browser_alive,
        memory_mb=memory_mb,
    )


def log_coordinator_dispatch(
    num_workers: int,
    num_available_tasks: int,
    num_tasks_leased: int,
    store_distribution: dict[str, int] | None = None,
) -> None:
    """Log coordinator task distribution decisions."""
    structured_log(
        "coordinator_dispatch",
        level="info",
        num_workers=num_workers,
        num_available_tasks=num_available_tasks,
        num_tasks_leased=num_tasks_leased,
        store_distribution=store_distribution,
    )


def log_grid_validation_failure(
    page_num: int,
    store_id: str,
    store_name: str,
    category_url: str,
    reason: str,
    page_url: str | None = None,
) -> None:
    """Log when grid validation fails (important for debugging crashes)."""
    structured_log(
        "grid_validation_failure",
        level="warning",
        page_num=page_num,
        store_id=store_id,
        store_name=store_name,
        category_url=category_url[:200] if category_url else None,
        reason=reason,
        page_url=page_url[:200] if page_url else None,
    )


def log_redirect_detected(
    store_id: str,
    store_name: str,
    requested_url: str,
    landed_url: str,
    redirect_type: str,  # "c_page", "different_domain", etc.
) -> None:
    """Log URL redirects which are common crash triggers."""
    structured_log(
        "redirect_detected",
        level="warning",
        store_id=store_id,
        store_name=store_name,
        requested_url=requested_url[:200] if requested_url else None,
        landed_url=landed_url[:200] if landed_url else None,
        redirect_type=redirect_type,
    )
