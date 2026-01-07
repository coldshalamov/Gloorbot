from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class TestCase:
    name: str
    cmd: list[str]
    env: dict[str, str] | None = None


def _run_case(case: TestCase) -> int:
    env = os.environ.copy()
    if case.env:
        env.update(case.env)

    print(f"\n=== {case.name} ===", flush=True)
    print(" ".join(case.cmd), flush=True)
    p = subprocess.run(case.cmd, cwd=str(ROOT), env=env)
    if p.returncode != 0:
        print(f"[FAIL] {case.name} (exit={p.returncode})", flush=True)
    else:
        print(f"[PASS] {case.name}", flush=True)
    return p.returncode


def main() -> int:
    cases: list[TestCase] = [
        TestCase(
            name="fixture suite (offline HTML -> tile_group split + pricing)",
            cmd=[sys.executable, "test_price_extraction_fixtures.py"],
        ),
        TestCase(
            name="tile_group split (Python locator path)",
            cmd=[sys.executable, "test_tile_group_extraction.py"],
        ),
        TestCase(
            name="tile_group split (JS near-me path regression)",
            cmd=[sys.executable, "test_near_me_dom_tile_group_split.py"],
        ),
        TestCase(
            name="price extraction ignores financing noise",
            cmd=[sys.executable, "test_price_extraction_financing_noise.py"],
            env={"GLOORBOT_PRICE_DIAGNOSTICS": "1"},
        ),
        TestCase(
            name="worker rejects financing strings as prices",
            cmd=[sys.executable, "test_worker_price_reject_financing.py"],
        ),
    ]

    failed: list[str] = []
    for case in cases:
        rc = _run_case(case)
        if rc != 0:
            failed.append(case.name)

    print("\n=== SUMMARY ===", flush=True)
    if failed:
        print(f"{len(failed)} failed:", flush=True)
        for n in failed:
            print(f"- {n}", flush=True)
        return 1

    print("All checks passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
