import importlib
import os
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    src_path = repo_root / "apify_actor_seed" / "src"
    sys.path.insert(0, str(src_path))

    module = importlib.import_module("main")

    for key in [
        "CHEAPSKATER_REQUIRE_PROXY",
        "CHEAPSKATER_FINGERPRINT_INJECTION",
        "CHEAPSKATER_RANDOM_UA",
        "CHEAPSKATER_RANDOM_TZLOCALE",
    ]:
        os.environ.pop(key, None)

    assert hasattr(module, "require_proxy_enabled"), "require_proxy_enabled missing"
    assert hasattr(module, "fingerprint_injection_enabled"), "fingerprint_injection_enabled missing"
    assert hasattr(module, "randomize_user_agent_enabled"), "randomize_user_agent_enabled missing"
    assert hasattr(module, "randomize_locale_enabled"), "randomize_locale_enabled missing"

    assert module.require_proxy_enabled() is False
    assert module.fingerprint_injection_enabled() is True
    assert module.randomize_user_agent_enabled() is True
    assert module.randomize_locale_enabled() is True


if __name__ == "__main__":
    main()
