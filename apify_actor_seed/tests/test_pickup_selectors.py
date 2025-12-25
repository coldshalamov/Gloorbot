import importlib
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    src_path = repo_root / "apify_actor_seed" / "src"
    sys.path.insert(0, str(src_path))

    module = importlib.import_module("main")

    assert hasattr(module, "PICKUP_SELECTORS"), "PICKUP_SELECTORS missing"

    selectors = module.PICKUP_SELECTORS
    assert any("availability" in sel for sel in selectors)
    assert any("pickup" in sel for sel in selectors)
    assert any("data-test-id" in sel for sel in selectors)


if __name__ == "__main__":
    main()
