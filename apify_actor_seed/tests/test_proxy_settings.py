import importlib
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    src_path = repo_root / "apify_actor_seed" / "src"
    sys.path.insert(0, str(src_path))

    module = importlib.import_module("main")

    assert hasattr(module, "proxy_settings_from_url"), "proxy_settings_from_url missing"

    proxy_url = "http://user:pass@proxy.example.com:8000"
    settings = module.proxy_settings_from_url(proxy_url)
    assert settings["server"] == "http://proxy.example.com:8000"
    assert settings["username"] == "user"
    assert settings["password"] == "pass"

    proxy_url_no_auth = "http://proxy.example.com:8000"
    settings = module.proxy_settings_from_url(proxy_url_no_auth)
    assert settings["server"] == "http://proxy.example.com:8000"
    assert "username" not in settings
    assert "password" not in settings


if __name__ == "__main__":
    main()
