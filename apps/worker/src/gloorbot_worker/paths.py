from __future__ import annotations

import os
import shutil
from pathlib import Path


def _base_appdata_root() -> Path:
    # LocalAppData is per-user and writable without admin.
    base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or str(Path.home())
    return Path(base)


def _legacy_app_data_dir() -> Path:
    # Older builds used LOCALAPPDATA/GloorbotWorker which can collide with the installer
    # directory (depending on where the EXE was installed).
    return _base_appdata_root() / "GloorbotWorker"


def app_data_dir() -> Path:
    # Keep runtime data separate from the installation directory to ensure we can
    # always write logs/profiles/status files even if the EXE is installed under
    # a path that collides with the old directory name.
    d = _base_appdata_root() / "GloorbotWorkerData"
    legacy = _legacy_app_data_dir()

    # Best-effort migration of known runtime artifacts from legacy dir.
    if legacy.exists() and not d.exists():
        try:
            d.mkdir(parents=True, exist_ok=True)
            for name in ["config.json", "profiles", "status", "logs"]:
                src = legacy / name
                dst = d / name
                if src.exists() and not dst.exists():
                    try:
                        shutil.move(str(src), str(dst))
                    except Exception:
                        # If move fails (locked/permission), fall back to copy for files.
                        try:
                            if src.is_file():
                                shutil.copy2(str(src), str(dst))
                        except Exception:
                            pass
        except Exception:
            pass

    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path() -> Path:
    return app_data_dir() / "config.json"


def config_dir() -> Path:
    """Directory for configuration files (settings, tuning, etc.)."""
    d = app_data_dir() / "config"
    d.mkdir(parents=True, exist_ok=True)
    return d


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
