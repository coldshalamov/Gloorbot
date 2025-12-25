import importlib
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    src_path = repo_root / "apify_actor_seed" / "src"
    sys.path.insert(0, str(src_path))

    module = importlib.import_module("main")

    url = "https://www.lowes.com/pl/Lumber-Building-supplies/4294850532"
    built = module.build_url(url, offset=48, store_id="0004")

    parsed = urlparse(built)
    qs = parse_qs(parsed.query)

    assert qs.get("offset") == ["48"]
    assert qs.get("storeNumber") == ["0004"]
    assert qs.get("pickupType") == ["pickupToday"]
    assert qs.get("availability") == ["pickupToday"]
    assert qs.get("inStock") == ["1"]
    assert qs.get("rollUpVariants") == ["0"]


if __name__ == "__main__":
    main()
