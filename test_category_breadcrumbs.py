from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent
COORDINATOR_DIR = ROOT / "apps" / "coordinator"
if str(COORDINATOR_DIR) not in sys.path:
    sys.path.insert(0, str(COORDINATOR_DIR))


pytest.importorskip("fastapi")

from coordinator_app.category_breadcrumbs import Breadcrumb, breadcrumb_leaf_name, breadcrumb_path


def test_breadcrumb_leaf_name_ignores_home() -> None:
    crumbs = [
        Breadcrumb(text="Home", href="/"),
        Breadcrumb(text="Home Decor", href="/c/Home-decor"),
        Breadcrumb(text="Window Treatments", href="/c/Window-treatments-Home-decor"),
        Breadcrumb(text="Curtains & Drapes", href=None),
    ]
    assert breadcrumb_leaf_name(crumbs) == "Curtains & Drapes"
    assert breadcrumb_path(crumbs) == "Home Decor / Window Treatments / Curtains & Drapes"


def test_breadcrumb_two_level_path() -> None:
    crumbs = [
        Breadcrumb(text="Electrical", href="/c/Electrical"),
        Breadcrumb(text="Extension Cords & Surge Protectors", href="/pl/extension-cords-surge-protectors/4294542242"),
    ]
    assert breadcrumb_leaf_name(crumbs) == "Extension Cords & Surge Protectors"
    assert breadcrumb_path(crumbs) == "Electrical / Extension Cords & Surge Protectors"


def test_breadcrumb_empty() -> None:
    assert breadcrumb_leaf_name([]) == "Uncategorized"
    assert breadcrumb_path([]) is None

