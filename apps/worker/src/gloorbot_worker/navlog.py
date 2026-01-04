import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strip_pagination(url: str) -> str:
    try:
        p = urlparse(url)
        q = parse_qs(p.query, keep_blank_values=True)
        q.pop("offset", None)
        new_query = urlencode(q, doseq=True)
        return urlunparse((p.scheme, p.netloc, p.path, p.params, new_query, p.fragment))
    except Exception:
        return url


@dataclass(frozen=True)
class JsonlLogger:
    path: Path
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    keep: int = 5

    def _rotate_if_needed(self) -> None:
        try:
            if not self.path.exists():
                return
            if self.path.stat().st_size < self.max_bytes:
                return
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            rotated = self.path.with_name(f"{self.path.stem}.{ts}{self.path.suffix}")
            try:
                self.path.rename(rotated)
            except Exception:
                return

            # Best-effort retention.
            try:
                siblings = sorted(
                    self.path.parent.glob(f"{self.path.stem}.*{self.path.suffix}"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                for extra in siblings[self.keep :]:
                    try:
                        extra.unlink()
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            return

    def write(self, event: str, **fields: Any) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._rotate_if_needed()
            payload: dict[str, Any] = {"ts": _utc_iso(), "event": event}
            payload.update(fields)

            for key in ["url", "page_url", "category_url", "requested_url", "landed_url"]:
                val = payload.get(key)
                if isinstance(val, str) and val:
                    payload[f"{key}_canonical"] = _strip_pagination(val)

            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            return


def default_event_logger(*, slot_id: int | None = None) -> JsonlLogger:
    # Allow overriding path (useful for installer builds).
    env_path = (os.getenv("GLOORBOT_EVENTLOG_PATH") or "").strip()
    if env_path:
        return JsonlLogger(path=Path(env_path))

    from .paths import logs_dir

    suffix = f"_slot_{slot_id}" if isinstance(slot_id, int) else ""
    return JsonlLogger(path=logs_dir() / f"events{suffix}.jsonl")


def set_default_parallel_navlog_path(*, slot_id: int | None = None) -> None:
    # PARALLEL/scraper.py will use this for low-level page navigation traces.
    if (os.getenv("GLOORBOT_NAVLOG_PATH") or "").strip():
        return

    from .paths import logs_dir

    suffix = f"_slot_{slot_id}" if isinstance(slot_id, int) else ""
    os.environ["GLOORBOT_NAVLOG_PATH"] = str(logs_dir() / f"nav{suffix}.jsonl")
