from __future__ import annotations


def extract_category_name(category_url: str | None) -> str:
    """
    Convert a Lowe's /pl/ category URL into a user-friendly category name.

    Rules (per CATEGORY_FILTER_SPEC.md):
    - Strip query params and trailing slashes.
    - Split on "/pl/" then "/" to get segments.
    - Drop purely-numeric segments (including hyphenated numeric IDs).
    - Use the last remaining text segment as the most-specific category slug.
    - Convert kebab-case to Title Case.
    """

    if not category_url:
        return "Uncategorized"

    try:
        path = category_url.split("?", 1)[0].rstrip("/")
        if "/pl/" not in path:
            return "Uncategorized"

        tail = path.split("/pl/", 1)[-1]
        segments = [seg for seg in tail.split("/") if seg]
        text_segments = [seg for seg in segments if not seg.replace("-", "").isdigit()]
        if not text_segments:
            return "Uncategorized"

        slug = text_segments[-1]
        name = slug.replace("-", " ").strip()
        return name.title() if name else "Uncategorized"
    except Exception:
        return "Uncategorized"


__all__ = ["extract_category_name"]

