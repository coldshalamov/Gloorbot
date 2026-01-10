from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Breadcrumb:
    text: str
    href: str | None = None


def normalize_breadcrumbs(items: list[Breadcrumb]) -> list[Breadcrumb]:
    normalized: list[Breadcrumb] = []
    for item in items:
        text = (item.text or "").strip()
        if not text:
            continue
        href = (item.href or "").strip() or None
        normalized.append(Breadcrumb(text=text, href=href))
    return normalized


def breadcrumb_text_path(items: list[Breadcrumb]) -> list[str]:
    crumbs = normalize_breadcrumbs(items)
    parts = [c.text for c in crumbs if c.text.lower() != "home"]
    return parts


def breadcrumb_leaf_name(items: list[Breadcrumb]) -> str:
    parts = breadcrumb_text_path(items)
    if not parts:
        return "Uncategorized"
    return parts[-1]


def breadcrumb_path(items: list[Breadcrumb]) -> str | None:
    parts = breadcrumb_text_path(items)
    if not parts:
        return None
    return " / ".join(parts)


__all__ = [
    "Breadcrumb",
    "normalize_breadcrumbs",
    "breadcrumb_text_path",
    "breadcrumb_leaf_name",
    "breadcrumb_path",
]

