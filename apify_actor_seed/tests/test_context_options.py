import importlib
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    src_path = repo_root / "apify_actor_seed" / "src"
    sys.path.insert(0, str(src_path))

    module = importlib.import_module("main")

    assert hasattr(module, "build_context_options"), "build_context_options missing"
    assert hasattr(module, "prime_session"), "prime_session missing"

    opts = module.build_context_options()
    assert "viewport" in opts
    assert "timezone_id" in opts
    assert "locale" in opts
    assert "user_agent" in opts

    width = opts["viewport"]["width"]
    height = opts["viewport"]["height"]
    assert 1280 <= width <= 1920
    assert 720 <= height <= 1080
    assert opts["timezone_id"] in module.TIMEZONES
    assert opts["locale"] in module.LOCALES
    assert opts["user_agent"] in module.USER_AGENTS

    calls = []

    class DummyPage:
        async def goto(self, url, wait_until=None, timeout=None):
            calls.append(("goto", url, wait_until))
        async def evaluate(self, script):
            calls.append(("eval", script))

    async def fake_sleep(_):
        calls.append(("sleep",))

    import asyncio
    asyncio.run(module.prime_session(DummyPage(), sleep_fn=fake_sleep))

    assert any(call[0] == "goto" for call in calls)
    assert sum(1 for call in calls if call[0] == "eval") >= 1


if __name__ == "__main__":
    main()
