"""
Gap analysis between:
- sitemap-derived structural minimal set (sitemap_minimal_structural_urls.txt)
- Departments UI discovery structural minimal set (discovered/pl_minimal_structural.txt)
- original LowesMap.txt (515 URLs) and MINIMAL_URLS_FROM_AUDIT.txt (505 URLs)

Outputs:
- gap_analysis.json
- GAP_ANALYSIS.md
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse


BASE_ID_RE = re.compile(r"^(\d{6,})")


def _load_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [l.strip() for l in path.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip()]


def _base_id(url: str) -> str | None:
    try:
        seg = urlparse(url).path.rstrip("/").split("/")[-1]
    except Exception:
        return None
    m = BASE_ID_RE.match(seg)
    return m.group(1) if m else None


def _base_ids(urls: list[str]) -> set[str]:
    out: set[str] = set()
    for u in urls:
        cid = _base_id(u)
        if cid:
            out.add(cid)
    return out


def main() -> None:
    sitemap_min = Path("sitemap_minimal_structural_urls.txt")
    discovered_min = Path("discovered/pl_minimal_structural.txt")
    lowesmap = Path("LowesMap.txt")
    minimal_from_audit = Path("MINIMAL_URLS_FROM_AUDIT.txt")

    sitemap_urls = _load_lines(sitemap_min)
    discovered_urls = _load_lines(discovered_min)
    lowesmap_urls = _load_lines(lowesmap)
    audit_min_urls = _load_lines(minimal_from_audit)

    sitemap_ids = _base_ids(sitemap_urls)
    discovered_ids = _base_ids(discovered_urls)
    lowesmap_ids = _base_ids(lowesmap_urls)
    audit_min_ids = _base_ids(audit_min_urls)

    report = {
        "counts": {
            "sitemap_min_urls": len(sitemap_urls),
            "sitemap_base_ids": len(sitemap_ids),
            "discovered_min_urls": len(discovered_urls),
            "discovered_base_ids": len(discovered_ids),
            "lowesmap_urls": len(lowesmap_urls),
            "lowesmap_base_ids": len(lowesmap_ids),
            "audit_min_urls": len(audit_min_urls),
            "audit_min_base_ids": len(audit_min_ids),
        },
        "base_id_overlap": {
            "discovered_vs_sitemap": len(discovered_ids & sitemap_ids),
            "missing_from_discovered_vs_sitemap": len(sitemap_ids - discovered_ids),
            "extra_in_discovered_vs_sitemap": len(discovered_ids - sitemap_ids),
            "lowesmap_vs_sitemap": len(lowesmap_ids & sitemap_ids),
            "missing_from_lowesmap_vs_sitemap": len(sitemap_ids - lowesmap_ids),
        },
        "missing_base_ids_from_discovered_vs_sitemap": sorted(sitemap_ids - discovered_ids)[:500],
        "missing_base_ids_from_lowesmap_vs_sitemap": sorted(sitemap_ids - lowesmap_ids)[:500],
    }

    Path("gap_analysis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    md = []
    md.append("# Gap Analysis\n\n")
    md.append("This compares different URL sources against the sitemap-derived base category universe.\n\n")
    md.append("## Counts\n\n")
    for k, v in report["counts"].items():
        md.append(f"- {k}: {v}\n")
    md.append("\n## Base ID Overlap\n\n")
    for k, v in report["base_id_overlap"].items():
        md.append(f"- {k}: {v}\n")
    md.append("\n## Interpretation\n\n")
    md.append(
        "- The sitemap-derived set is the only one that approaches catalog-scale coverage (thousands of base category IDs).\n"
    )
    md.append(
        "- The Departments UI discovery covers a *subset* of sitemap base IDs; it is useful for navigation analysis, but it is not sufficient to claim full catalog coverage.\n"
    )
    md.append(
        "- The original 515-url LowesMap set is also a small subset of the sitemap base IDs; reducing it to 505 only removes exact duplicates and does not improve coverage.\n"
    )
    md.append("\n## Notes\n\n")
    md.append(
        "- This is *structural* coverage at the **base category id** level; it does not prove a mathematical minimal set-cover over products.\n"
    )

    Path("GAP_ANALYSIS.md").write_text("".join(md), encoding="utf-8")
    print("Wrote gap_analysis.json")
    print("Wrote GAP_ANALYSIS.md")


if __name__ == "__main__":
    main()

