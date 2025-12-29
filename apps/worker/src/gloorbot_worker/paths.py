from __future__ import annotations

import os
from pathlib import Path


def app_data_dir() -> Path:
    # LocalAppData is per-user and writable without admin.
    base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or str(Path.home())
    d = Path(base) / "GloorbotWorker"
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path() -> Path:
    return app_data_dir() / "config.json"


def profiles_dir() -> Path:
    d = app_data_dir() / "profiles"
    d.mkdir(parents=True, exist_ok=True)
    return d


def status_dir() -> Path:
    d = app_data_dir() / "status"
    d.mkdir(parents=True, exist_ok=True)
    return d


def logs_dir() -> Path:
    d = app_data_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cleanup_old_files(max_age_days: int = 30) -> int:
    """Remove old logs, block artifacts, and other temp files older than max_age_days.
    
    Returns the number of files deleted.
    """
    import time
    
    deleted = 0
    cutoff = time.time() - (max_age_days * 86400)
    
    # Directories to clean
    dirs_to_clean = [
        logs_dir(),
        logs_dir() / "blocks",
        status_dir(),
    ]
    
    for dir_path in dirs_to_clean:
        if not dir_path.exists():
            continue
        try:
            for item in dir_path.iterdir():
                if item.is_file():
                    try:
                        if item.stat().st_mtime < cutoff:
                            item.unlink()
                            deleted += 1
                    except Exception:
                        pass
        except Exception:
            pass
    
    return deleted
