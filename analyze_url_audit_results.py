"""
Analyze url_audit_results.json from audit_all_urls.py.

Outputs:
- url_audit_analysis_summary.json: high-level stats + coverage vs sitemap unique IDs
- DUPLICATE_GROUPS_FROM_AUDIT.md: exact-ID duplicates + candidate duplicates from SKU samples
- MINIMAL_URLS_FROM_AUDIT.txt: one canonical URL per discovered category ID (safe dedupe)
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


INPUT_RESULTS = Path("url_audit_results.json")
INPUT_SITEMAP = Path("sitemap_comparison.json")

OUT_SUMMARY = Path("url_audit_analysis_summary.json")
OUT_DUP_MD = Path("DUPLICATE_GROUPS_FROM_AUDIT.md")
OUT_MINIMAL = Path("MINIMAL_URLS_FROM_AUDIT.txt")


def _category_id(url: str) -> str | None:
    m = re.search(r"/([0-9]+)(?:-|$)", url)
    return m.group(1) if m else None


def _safe_load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def main() -> None:
    if not INPUT_RESULTS.exists():
        raise SystemExit(f"Missing {INPUT_RESULTS} (run audit_all_urls.py first)")

    results = _safe_load_json(INPUT_RESULTS)
    if not isinstance(results, list):
        raise SystemExit(f"{INPUT_RESULTS} must be a JSON list")

    # Normalize
    normalized: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict) or "url" not in item:
            continue
        url = str(item.get("url"))
        normalized.append(
            {
                "url": url,
                "category_id": _category_id(url),
                "blocked": bool(item.get("blocked")),
                "error": item.get("error"),
                "count": int(item.get("count") or 0),
                "product_ids": [str(x) for x in (item.get("product_ids") or []) if x],
                "breadcrumb": item.get("breadcrumb"),
                "title": item.get("title"),
            }
        )

    total = len(normalized)
    blocked = sum(1 for r in normalized if r["blocked"])
    errored = sum(1 for r in normalized if r["error"])
    ok = total - blocked - errored

    by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in normalized:
        if r["category_id"]:
            by_id[r["category_id"]].append(r)

    # Exact-ID duplicates (safe)
    exact_id_dupes = {cid: items for cid, items in by_id.items() if len(items) > 1}

    # Candidate duplicates by identical sample SKU list (high false-positive risk if sample is small)
    by_sample: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for r in normalized:
        sample = tuple(r["product_ids"][:10])
        if len(sample) >= 5 and not r["blocked"] and not r["error"]:
            by_sample[sample].append(r)

    candidate_sample_dupes = {
        sample: items
        for sample, items in by_sample.items()
        if len(items) > 1 and len({i["category_id"] for i in items if i["category_id"]}) > 1
    }

    # Minimal list: one canonical URL per category_id (shortest URL string)
    canonical_by_id: dict[str, str] = {}
    for cid, items in by_id.items():
        canonical_by_id[cid] = sorted({i["url"] for i in items})[0]

    minimal_urls = sorted(canonical_by_id.values())
    OUT_MINIMAL.write_text("\n".join(minimal_urls) + ("\n" if minimal_urls else ""), encoding="utf-8")

    # Sitemap coverage by unique category IDs
    sitemap_unique_ids = None
    missing_category_ids = None
    if INPUT_SITEMAP.exists():
        try:
            s = _safe_load_json(INPUT_SITEMAP)
            urls: list[str] = []
            for key in ("missing_from_map", "common", "extra_in_map"):
                v = s.get(key)
                if isinstance(v, list):
                    urls.extend([str(x) for x in v if isinstance(x, str)])
            sitemap_unique_ids = sorted({_category_id(u) for u in urls if _category_id(u)})
            map_ids = set(canonical_by_id.keys())
            missing_category_ids = sorted([cid for cid in sitemap_unique_ids if cid not in map_ids])
        except Exception:
            sitemap_unique_ids = None
            missing_category_ids = None

    summary = {
        "total_results": total,
        "ok": ok,
        "blocked": blocked,
        "errored": errored,
        "unique_category_ids_in_audit": len(canonical_by_id),
        "exact_id_duplicate_groups": len(exact_id_dupes),
        "candidate_sample_duplicate_groups": len(candidate_sample_dupes),
        "sitemap_unique_category_ids": len(sitemap_unique_ids) if sitemap_unique_ids else None,
        "missing_category_ids_vs_sitemap": len(missing_category_ids) if missing_category_ids else None,
        "missing_category_ids_sample": (missing_category_ids[:25] if missing_category_ids else None),
    }
    OUT_SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Write duplicate report
    lines: list[str] = []
    lines.append("# Duplicate groups from audit")
    lines.append("")
    lines.append("## Exact duplicates (same category ID)")
    if not exact_id_dupes:
        lines.append("- None detected in current results set.")
    else:
        for cid in sorted(exact_id_dupes.keys(), key=lambda x: int(x)):
            urls = sorted({i["url"] for i in exact_id_dupes[cid]})
            lines.append(f"- ID `{cid}` ({len(urls)} URLs)")
            for u in urls:
                lines.append(f"  - `{u}`")
    lines.append("")
    lines.append("## Candidate duplicates (identical first-page SKU samples across different IDs)")
    lines.append(
        "- These are *candidates only* (false positives possible): identical first-page samples do not prove full-set equality."
    )
    if not candidate_sample_dupes:
        lines.append("- None detected (with >=5 sampled IDs).")
    else:
        # Sort by group size desc
        groups = sorted(candidate_sample_dupes.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        for sample, items in groups[:200]:
            urls = sorted({i["url"] for i in items})
            cids = sorted(_dedupe_preserve_order([i["category_id"] for i in items if i["category_id"]]))
            lines.append(f"- Sample `{','.join(sample[:5])}...` ({len(urls)} URLs, IDs: {', '.join(cids)})")
            for u in urls:
                lines.append(f"  - `{u}`")
    OUT_DUP_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {OUT_SUMMARY}")
    print(f"Wrote {OUT_DUP_MD}")
    print(f"Wrote {OUT_MINIMAL}")


if __name__ == "__main__":
    main()

