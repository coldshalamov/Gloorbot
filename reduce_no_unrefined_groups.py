"""
Heuristic reduction for category base-IDs that have no obvious "unrefined" /<id> URL.

Inputs:
- discovered/no_unrefined_groups.json   (base_id -> [urls...])
- discovered/no_unrefined_audit.json    (audit_url_list.py output; list of {url,count,product_ids,...})

Outputs:
- discovered/no_unrefined_recommended_keep.txt
- discovered/no_unrefined_reduction_report.md
- discovered/no_unrefined_reduction.json

Important:
This is not a mathematical proof of minimality; it is an evidence-based reduction using:
- product grid count (first page)
- sample product id overlap (first page)
"""

from __future__ import annotations

import json
from pathlib import Path


GROUPS = Path("discovered/no_unrefined_groups.json")
AUDIT = Path("discovered/no_unrefined_audit.json")

OUT_KEEP = Path("discovered/no_unrefined_recommended_keep.txt")
OUT_REPORT = Path("discovered/no_unrefined_reduction_report.md")
OUT_JSON = Path("discovered/no_unrefined_reduction.json")


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    if not GROUPS.exists():
        raise SystemExit(f"Missing {GROUPS}")
    if not AUDIT.exists():
        raise SystemExit(f"Missing {AUDIT}")

    groups: dict[str, list[str]] = _load_json(GROUPS)
    audit_list = _load_json(AUDIT)
    if not isinstance(audit_list, list):
        raise SystemExit("Audit JSON must be a list.")

    audit_by_url: dict[str, dict] = {r.get("url"): r for r in audit_list if isinstance(r, dict) and r.get("url")}

    recommendations: dict[str, dict] = {}
    keep_urls: list[str] = []

    md: list[str] = []
    md.append("# No-Unrefined Group Reduction Report\n\n")
    md.append(
        "These groups have a shared base category id but no obvious unrefined `/.../<id>` URL.\n"
        "We use first-page product counts + sample product IDs to recommend a smaller keep-set.\n\n"
    )

    total_groups = len(groups)
    total_urls = sum(len(v) for v in groups.values())
    md.append(f"- Groups: {total_groups}\n")
    md.append(f"- URLs: {total_urls}\n\n")

    for cid, urls in sorted(groups.items(), key=lambda kv: (len(kv[1]) * -1, kv[0])):
        audited = []
        missing = []
        for u in urls:
            r = audit_by_url.get(u)
            if not r:
                missing.append(u)
                continue
            audited.append(r)

        # If we don't have all data yet, be conservative.
        if missing or not audited:
            recommendations[cid] = {
                "status": "incomplete",
                "keep": urls,
                "missing_audit": missing,
            }
            keep_urls.extend(urls)
            continue

        # Choose "best" by count, then by number of extracted product IDs.
        audited_sorted = sorted(
            audited,
            key=lambda r: (
                int(r.get("count") or 0),
                len(r.get("product_ids") or []),
            ),
            reverse=True,
        )
        best = audited_sorted[0]
        best_ids = set(best.get("product_ids") or [])
        best_count = int(best.get("count") or 0)

        keep = [best.get("url")]
        dropped = []

        for r in audited_sorted[1:]:
            u = r.get("url")
            count = int(r.get("count") or 0)
            ids = set(r.get("product_ids") or [])
            if not ids:
                # If we couldn't extract IDs, keep it (conservative).
                keep.append(u)
                continue

            overlap = len(ids & best_ids)
            overlap_ratio = overlap / max(1, len(ids))

            # Heuristic drop: if the sample looks like a subset and count isn't larger.
            if overlap_ratio >= 0.8 and count <= best_count:
                dropped.append(
                    {
                        "url": u,
                        "count": count,
                        "overlap_ratio_vs_best": round(overlap_ratio, 3),
                        "overlap": overlap,
                        "sample_size": len(ids),
                    }
                )
            else:
                keep.append(u)

        recommendations[cid] = {
            "status": "complete",
            "best": {"url": best.get("url"), "count": best_count, "product_ids": list(best_ids)},
            "keep": keep,
            "dropped": dropped,
        }
        keep_urls.extend(keep)

    keep_urls = [u for u in keep_urls if isinstance(u, str) and u.strip()]
    # preserve order, dedupe
    seen = set()
    keep_urls_deduped = []
    for u in keep_urls:
        if u not in seen:
            seen.add(u)
            keep_urls_deduped.append(u)

    OUT_KEEP.write_text("\n".join(keep_urls_deduped) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(recommendations, indent=2), encoding="utf-8")

    # Build a compact markdown summary.
    complete = [v for v in recommendations.values() if v.get("status") == "complete"]
    incomplete = [v for v in recommendations.values() if v.get("status") != "complete"]
    dropped_urls = sum(len(v.get("dropped") or []) for v in complete)
    kept_urls = sum(len(v.get("keep") or []) for v in complete) + sum(len(v.get("keep") or []) for v in incomplete)

    md.append("## Summary\n\n")
    md.append(f"- Complete groups: {len(complete)}\n")
    md.append(f"- Incomplete groups (missing audits): {len(incomplete)}\n")
    md.append(f"- URLs kept (recommended): {kept_urls}\n")
    md.append(f"- URLs dropped (heuristic): {dropped_urls}\n\n")

    md.append("## Largest Groups (top 25)\n\n")
    top = sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)[:25]
    for cid, urls in top:
        rec = recommendations.get(cid, {})
        md.append(f"### {cid} ({len(urls)} URLs)\n")
        md.append(f"- status: {rec.get('status')}\n")
        keep = rec.get("keep") or []
        md.append(f"- keep: {len(keep)}\n")
        dropped = rec.get("dropped") or []
        if dropped:
            md.append(f"- dropped: {len(dropped)}\n")
        md.append("\n")

    OUT_REPORT.write_text("".join(md), encoding="utf-8")
    print(f"Wrote {OUT_KEEP} ({len(keep_urls_deduped)} URLs)")
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_REPORT}")


if __name__ == "__main__":
    main()

