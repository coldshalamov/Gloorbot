from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class AuditRecord:
    url: str
    kind: str
    status: int | None
    title: str | None
    final_url: str | None


def _load_url_list(path: Path) -> list[str]:
    urls: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not (line.startswith("http://") or line.startswith("https://")):
            continue
        urls.append(line)
    return urls


def _load_audit_latest(path: Path) -> dict[str, AuditRecord]:
    latest: dict[str, AuditRecord] = {}
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        url = rec.get("url")
        if not isinstance(url, str) or not url:
            continue
        latest[url] = AuditRecord(
            url=url,
            kind=str(rec.get("kind") or ""),
            status=rec.get("status") if isinstance(rec.get("status"), int) else None,
            title=rec.get("title") if isinstance(rec.get("title"), str) else None,
            final_url=rec.get("finalUrl") if isinstance(rec.get("finalUrl"), str) else None,
        )
    return latest


def _rewrite_file_removing_urls(*, file_path: Path, remove: set[str], backup_suffix: str) -> int:
    original = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    kept_lines: list[str] = []
    removed = 0

    for raw in original:
        stripped = raw.strip()
        if stripped in remove:
            removed += 1
            continue
        kept_lines.append(raw)

    backup_path = file_path.with_name(file_path.name + backup_suffix)
    if not backup_path.exists():
        backup_path.write_text("\n".join(original) + "\n", encoding="utf-8")

    file_path.write_text("\n".join(kept_lines) + "\n", encoding="utf-8")
    return removed


def _write_report(path: Path, *, not_found: Iterable[AuditRecord]) -> None:
    items = []
    for rec in sorted(not_found, key=lambda r: r.url):
        items.append(
            {
                "url": rec.url,
                "kind": rec.kind,
                "status": rec.status,
                "final_url": rec.final_url,
                "title": rec.title,
            }
        )
    path.write_text(json.dumps({"not_found": items}, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Remove confirmed 404 category URLs from seed lists.")
    ap.add_argument("--audit", type=Path, required=True, help="JSONL output from dev-browser audit-lowes-urls.ts")
    ap.add_argument(
        "--current",
        type=Path,
        required=True,
        help="Current category URL list that was audited (one URL per line).",
    )
    ap.add_argument(
        "--targets",
        type=Path,
        nargs="+",
        required=True,
        help="Seed list files to rewrite (e.g. apps/coordinator/data/urls.txt PARALLEL/urls.txt ...).",
    )
    ap.add_argument(
        "--report",
        type=Path,
        default=Path("logs/not_found_urls.json"),
        help="Where to write a JSON report of not_found URLs.",
    )
    args = ap.parse_args()

    audit_latest = _load_audit_latest(args.audit)
    current_urls = _load_url_list(args.current)
    current_set = set(current_urls)

    # For safety: only prune URLs that were in the audited current list AND are marked not_found.
    not_found: list[AuditRecord] = []
    for url in sorted(current_set):
        rec = audit_latest.get(url)
        if rec and rec.kind == "not_found":
            not_found.append(rec)

    remove_set = {r.url for r in not_found}

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_suffix = f".bak.{ts}"

    print(json.dumps({"current_urls": len(current_set), "not_found": len(remove_set), "backup_suffix": backup_suffix}, indent=2))
    if not remove_set:
        return 0

    _write_report(args.report, not_found=not_found)
    print(f"Wrote report: {args.report}")

    for target in args.targets:
        if not target.exists():
            raise FileNotFoundError(f"Missing target file: {target}")
        removed = _rewrite_file_removing_urls(file_path=target, remove=remove_set, backup_suffix=backup_suffix)
        print(f"{target}: removed {removed}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
