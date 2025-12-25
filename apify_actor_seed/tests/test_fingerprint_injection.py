import importlib
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    src_path = repo_root / "apify_actor_seed" / "src"
    sys.path.insert(0, str(src_path))

    module = importlib.import_module("main")

    assert hasattr(module, "apply_fingerprint_randomization"), "apply_fingerprint_randomization missing"

    calls = []

    class DummyPage:
        async def add_init_script(self, script: str) -> None:
            calls.append(script)

    page = DummyPage()

    # Run async helper
    import asyncio

    profile = module.build_fingerprint_profile(1400, 900)
    asyncio.run(module.apply_fingerprint_randomization(page, profile))

    assert len(calls) >= 4, f"expected at least 4 scripts, got {len(calls)}"
    combined = "\n".join(calls)
    assert "HTMLCanvasElement" in combined
    assert "WebGLRenderingContext" in combined
    assert "AudioContext" in combined
    assert "window.screen" in combined


if __name__ == "__main__":
    main()
