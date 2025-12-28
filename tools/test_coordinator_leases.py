"""
Lease stress test (local coordinator).
Runs multiple concurrent clients and checks for duplicate task_id leases.
"""

from __future__ import annotations

import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


COORDINATOR_URL = os.getenv("COORDINATOR_URL", "http://127.0.0.1:8000").rstrip("/")
CLIENTS = int(os.getenv("LEASE_TEST_CLIENTS", "50"))
DURATION = int(os.getenv("LEASE_TEST_SECONDS", "30"))


lock = threading.Lock()
leased = set()
duplicates = 0
leases_total = 0


def register_client() -> str:
    res = requests.post(f"{COORDINATOR_URL}/api/v1/client/register", json={}, timeout=10)
    res.raise_for_status()
    return res.json()["client_id"]


def lease_loop(client_id: str) -> None:
    global duplicates, leases_total
    end_at = time.time() + DURATION
    while time.time() < end_at:
        try:
            res = requests.post(
                f"{COORDINATOR_URL}/api/v1/lease/next",
                json={"client_id": client_id},
                timeout=10,
            )
            res.raise_for_status()
            data = res.json()
            if not data:
                time.sleep(0.2)
                continue
            task_id = data["task_id"]
            with lock:
                leases_total += 1
                if task_id in leased:
                    duplicates += 1
                leased.add(task_id)
            # complete immediately
            requests.post(
                f"{COORDINATOR_URL}/api/v1/lease/complete",
                json={"client_id": client_id, "task_id": task_id},
                timeout=10,
            )
        except Exception:
            time.sleep(0.2)


def main() -> None:
    print(f"Coordinator: {COORDINATOR_URL}")
    print(f"Clients: {CLIENTS}, Duration: {DURATION}s")
    client_ids = [register_client() for _ in range(CLIENTS)]

    with ThreadPoolExecutor(max_workers=CLIENTS) as pool:
        futures = [pool.submit(lease_loop, cid) for cid in client_ids]
        for f in as_completed(futures):
            f.result()

    print(f"Total leases: {leases_total}")
    print(f"Duplicates: {duplicates}")
    if duplicates == 0:
        print("PASS: No duplicate leases observed.")
    else:
        print("FAIL: Duplicate leases detected.")


if __name__ == "__main__":
    main()
