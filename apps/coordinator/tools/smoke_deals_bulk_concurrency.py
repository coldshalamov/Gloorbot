"""
Smoke test: concurrent /api/v1/deals/bulk submissions with the same deal should be idempotent.

Run:
  python apps/coordinator/tools/smoke_deals_bulk_concurrency.py
"""

from __future__ import annotations

import os
import tempfile
import threading
import time
from pathlib import Path
import sys


def _make_payload(client_id: str, product_url: str) -> dict:
    return {
        "client_id": client_id,
        "deals": [
            {
                "store_id": "0061",
                "store_name": "Arlington, WA (#0061)",
                "category_url": "https://www.lowes.com/pl/vanities/123",
                "product_url": product_url,
                "title": "Example Product",
                "price": 10.0,
                "was_price": 20.0,
                "pct_off": 0.5,
                "found_at": "2026-01-04T00:00:00Z",
            }
        ],
    }


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "coordinator.sqlite")
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

        # Import after env is set (db engine is created at import-time).
        project_root = Path(__file__).resolve().parents[1]  # apps/coordinator
        sys.path.insert(0, str(project_root))

        from fastapi.testclient import TestClient

        from coordinator_app.web import create_app

        app = create_app()
        product_url = "https://www.lowes.com/pd/Example/9999999999"

        with TestClient(app) as client:
            barrier = threading.Barrier(3)
            results: list[tuple[int, str]] = []
            lock = threading.Lock()

            def worker(thread_client_id: str) -> None:
                payload = _make_payload(thread_client_id, product_url)
                barrier.wait()
                resp = client.post("/api/v1/deals/bulk", json=payload)
                with lock:
                    results.append((resp.status_code, resp.text))

            t1 = threading.Thread(target=worker, args=("c1",), daemon=True)
            t2 = threading.Thread(target=worker, args=("c2",), daemon=True)
            t1.start()
            t2.start()

            # Synchronize start.
            barrier.wait()
            t1.join(timeout=10)
            t2.join(timeout=10)

            # Give SQLite a moment to settle.
            time.sleep(0.1)

            statuses = [s for (s, _) in results]
            if statuses.count(200) != 2:
                print("FAIL: expected 2x 200 OK, got:", results)
                return 1

            print("OK:", results)

        # Ensure the sqlite file is released so TemporaryDirectory can delete it.
        from coordinator_app.db import engine

        engine.dispose()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
