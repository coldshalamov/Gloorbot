from __future__ import annotations


def _looks_like_facet_value(slug: str) -> bool:
    text = (slug or "").strip().lower()
    if not text:
        return True
    words = [part for part in text.split("-") if part]
    if any(ch.isdigit() for ch in text):
        return True
    if len(words) >= 5:
        return True
    return False


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
        if _looks_like_facet_value(slug):
            fallback_segments = [seg for seg in reversed(text_segments[:-1]) if not _looks_like_facet_value(seg)]
            if fallback_segments:
                slug = fallback_segments[0]
        name = slug.replace("-", " ").strip()
        return name.title() if name else "Uncategorized"
    except Exception:
        return "Uncategorized"


__all__ = ["extract_category_name"]

