from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import psutil

# Handle PyInstaller frozen executable - need absolute imports
if getattr(sys, 'frozen', False):
    from gloorbot_worker import api
    from gloorbot_worker.paths import config_path, logs_dir, cleanup_old_files, status_dir
    from gloorbot_worker.settings import get_settings
else:
    from . import api
    from .paths import config_path, logs_dir, cleanup_old_files, status_dir
    from .settings import get_settings


TARGET_LOW = 70.0
TARGET_HIGH = 90.0
CHECK_INTERVAL_SECONDS = 90
MAX_SLOTS_DEFAULT = int(os.getenv("MAX_SLOTS", "5"))


@dataclass
class SlotProc:
    slot_id: int
    proc: subprocess.Popen


class Supervisor:
    def __init__(self) -> None:
        self.client_id: str | None = self._load_client_id()
        self.slots: list[SlotProc] = []
        self._stop = False
        self._tasks_completed = 0
        self._deals_sent = 0
        self._next_register_attempt_at = 0.0
        self._block_count = 0  # Track consecutive blocks
        self._last_block_time = 0.0
        self._max_slots_override: int | None = None  # Reduced when detecting blocks
        
        # Run disk cleanup on startup
        try:
            deleted = cleanup_old_files(max_age_days=30)
            if deleted > 0:
                print(f"[supervisor] Cleaned up {deleted} old files")
        except Exception:
            pass

    def _load_client_id(self) -> str | None:
        cfg = config_path()
        if cfg.exists():
            try:
                return json.loads(cfg.read_text(encoding="utf-8")).get("client_id")
            except Exception:
                return None
        return None

    def _save_client_id(self, client_id: str) -> None:
        cfg = config_path()
        cfg.write_text(json.dumps({"client_id": client_id}, indent=2), encoding="utf-8")

    def _ensure_client_id(self) -> bool:
        if self.client_id:
            return True
        now = time.time()
        if now < self._next_register_attempt_at:
            return False
        self._next_register_attempt_at = now + 10.0  # retry every 10s until connected
        try:
            cid = api.register()
            self.client_id = cid
            self._save_client_id(cid)
            return True
        except Exception:
            return False

    def start(self) -> None:
        self._stop = False

    def stop(self) -> None:
        self._stop = True
        for slot in list(self.slots):
            self._kill_slot(slot)
        self.slots.clear()

    def _spawn_slot(self) -> None:
        if not self.client_id:
            return
        slot_id = (max([s.slot_id for s in self.slots]) + 1) if self.slots else 0
        log_path = logs_dir() / f"slot_{slot_id}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_file = open(log_path, "a", encoding="utf-8", buffering=1)
        if getattr(sys, "frozen", False):
            cmd = [
                sys.executable,
                "--slot-worker",
                "--client-id",
                self.client_id,
                "--slot-id",
                str(slot_id),
            ]
        else:
            cmd = [
                sys.executable,
                "-m",
                "gloorbot_worker",
                "--slot-worker",
                "--client-id",
                self.client_id,
                "--slot-id",
                str(slot_id),
            ]
        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"
        # Per-slot JSONL logs so multiple slots don't contend for the same file.
        try:
            env.setdefault("GLOORBOT_NAVLOG_PATH", str(logs_dir() / f"nav_slot_{slot_id}.jsonl"))
            env.setdefault("GLOORBOT_EVENTLOG_PATH", str(logs_dir() / f"events_slot_{slot_id}.jsonl"))
        except Exception:
            pass
        env.setdefault("GLOORBOT_SLOT_ID", str(slot_id))
        proc = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=str(Path(__file__).resolve().parents[2]),
            env=env,
        )
        self.slots.append(SlotProc(slot_id=slot_id, proc=proc))

    def _kill_slot(self, slot: SlotProc) -> None:
        try:
            p = psutil.Process(slot.proc.pid)
            for child in p.children(recursive=True):
                try:
                    child.kill()
                except Exception:
                    pass
            p.kill()
        except Exception:
            try:
                slot.proc.kill()
            except Exception:
                pass

    def tick(self) -> dict:
        # Clean up dead slots
        alive: list[SlotProc] = []
        for slot in self.slots:
            if slot.proc.poll() is None:
                alive.append(slot)
        self.slots = alive

        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent

        connected = self._ensure_client_id()
        if connected and self.client_id:
            api.heartbeat(self.client_id, cpu, mem, len(self.slots))

        # Check for block signals from slot workers
        try:
            block_signal = status_dir() / "block_signal.txt"
            if block_signal.exists():
                signal_time = float(block_signal.read_text(encoding="utf-8").strip())
                # Only process if signal is recent (within last 60 seconds)
                if time.time() - signal_time < 60:
                    self.report_block()
                block_signal.unlink()  # Consume the signal
        except Exception:
            pass

        if self._stop:
            return {"running": False, "connected": connected, "slots": 0, "cpu": cpu, "mem": mem}

        if not connected:
            # Joined, but coordinator isn't reachable yet; don't spawn slots.
            return {"running": True, "connected": False, "slots": 0, "cpu": cpu, "mem": mem}

        # Load performance settings
        settings = get_settings()

        # Scale decisions - support fixed browser mode
        if settings.fixed_browser_count > 0:
            # FIXED MODE: Always maintain exactly N browsers (ignores CPU/memory)
            target_slots = settings.fixed_browser_count
            if self._max_slots_override is not None:
                # Block detection can still reduce count
                target_slots = min(target_slots, self._max_slots_override)

            while len(self.slots) < target_slots:
                self._spawn_slot()
            while len(self.slots) > target_slots:
                self._kill_slot(self.slots[-1])
                self.slots = self.slots[:-1]
        else:
            # DYNAMIC MODE: Scale based on CPU/memory (original behavior)
            max_slots_cfg = max(1, settings.max_browsers or MAX_SLOTS_DEFAULT)
            max_slots = self._max_slots_override if self._max_slots_override is not None else max_slots_cfg
            if len(self.slots) == 0:
                self._spawn_slot()
            elif len(self.slots) < max_slots and cpu < TARGET_LOW and mem < TARGET_LOW:
                self._spawn_slot()
            elif cpu > TARGET_HIGH or mem > TARGET_HIGH:
                if len(self.slots) > 1:
                    self._kill_slot(self.slots[-1])
                    self.slots = self.slots[:-1]

        return {"running": True, "connected": True, "slots": len(self.slots), "cpu": cpu, "mem": mem, "blocks": self._block_count}

    def report_block(self) -> None:
        """Called by slot workers when they detect a block. Triggers backoff."""
        now = time.time()
        # Reset block count if last block was more than 10 minutes ago
        if now - self._last_block_time > 600:
            self._block_count = 0
        
        self._block_count += 1
        self._last_block_time = now
        
        # Exponential backoff: reduce max slots based on block count
        if self._block_count >= 5:
            self._max_slots_override = 1
            print(f"[supervisor] High block rate ({self._block_count}), limiting to 1 slot")
        elif self._block_count >= 3:
            self._max_slots_override = max(1, len(self.slots) // 2)
            print(f"[supervisor] Moderate blocks ({self._block_count}), limiting to {self._max_slots_override} slots")
        elif self._block_count >= 1:
            # Just log, don't reduce yet
            print(f"[supervisor] Block detected ({self._block_count} total)")
        
        # Write block status to file so slots can read it
        try:
            block_file = status_dir() / "block_status.json"
            import json
            block_file.write_text(json.dumps({
                "block_count": self._block_count,
                "last_block": self._last_block_time,
                "max_slots": self._max_slots_override,
            }), encoding="utf-8")
        except Exception:
            pass

    def run_loop(self, on_tick) -> None:
        self.start()
        while not self._stop:
            status = self.tick()
            on_tick(status)
            for _ in range(CHECK_INTERVAL_SECONDS):
                if self._stop:
                    break
                time.sleep(1)
