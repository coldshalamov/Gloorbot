import importlib
import os
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    src_path = repo_root / "apify_actor_seed" / "src"
    sys.path.insert(0, str(src_path))

    module = importlib.import_module("main")

    assert hasattr(module, "resolve_user_data_dir"), "resolve_user_data_dir missing"

    test_path = repo_root / "apify_actor_seed" / "tests" / "profile_seed"
    os.environ["CHEAPSKATER_USER_DATA_DIR"] = str(test_path)

    resolved = module.resolve_user_data_dir()
    assert Path(resolved) == test_path

    os.environ.pop("CHEAPSKATER_USER_DATA_DIR", None)


if __name__ == "__main__":
    main()
