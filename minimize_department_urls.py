"""
Minimize discovered /pl/ candidates into a canonical list:

Rules (high-confidence, structural):
1) Deduplicate exact duplicates by base category ID (numeric in the URL path).
2) If multiple URLs share the same base category ID:
   - Prefer an unrefined URL form that ends with '/<id>' (no extra '-<something>' suffix).
   - Otherwise, keep *all* variants for that base ID (because we cannot prove which refinement
     partitions cover the whole set without enumerating products).

Outputs:
- discovered/pl_minimal_structural.txt
- discovered/pl_groups_by_category_id.json (for review)
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


IN_PL = Path("discovered/pl_candidates.txt")
OUT_MIN = Path("discovered/pl_minimal_structural.txt")
OUT_GROUPS = Path("discovered/pl_groups_by_category_id.json")


def _category_id_from_pl(url: str) -> str | None:
    # /pl/.../<baseId> or /pl/.../<baseId>-<refId>
    m = re.search(r"/(\d+)(?:-|$)", url.rstrip("/"))
    return m.group(1) if m else None


def _is_unrefined(url: str, category_id: str) -> bool:
    tail = url.rstrip("/").split("/")[-1]
    return tail == category_id


def _load_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> None:
    urls = _load_lines(IN_PL)
    by_id: dict[str, list[str]] = defaultdict(list)
    for u in urls:
        cid = _category_id_from_pl(u)
        if not cid:
            continue
        if u not in by_id[cid]:
            by_id[cid].append(u)

    groups: dict[str, Any] = {}
    minimal: list[str] = []

    for cid, group in sorted(by_id.items(), key=lambda kv: int(kv[0])):
        unrefined = [u for u in group if _is_unrefined(u, cid)]
        if unrefined:
            chosen = sorted(unrefined, key=len)[0]
            minimal.append(chosen)
            groups[cid] = {"chosen": [chosen], "all": group, "reason": "has_unrefined"}
        else:
            # Cannot safely pick one without a proof pass.
            keep = sorted(group, key=len)
            minimal.extend(keep)
            groups[cid] = {"chosen": keep, "all": group, "reason": "no_unrefined_keep_all"}

    OUT_MIN.write_text("\n".join(minimal) + ("\n" if minimal else ""), encoding="utf-8")
    OUT_GROUPS.write_text(json.dumps(groups, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_MIN} ({len(minimal)} URLs)")
    print(f"Wrote {OUT_GROUPS} ({len(groups)} category IDs)")


if __name__ == "__main__":
    main()

