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
    from gloorbot_worker.paths import config_path, logs_dir
else:
    from . import api
    from .paths import config_path, logs_dir


TARGET_LOW = 70.0
TARGET_HIGH = 90.0
CHECK_INTERVAL_SECONDS = 90


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
        log_file = open(log_path, "a", encoding="utf-8")
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
        proc = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=str(Path(__file__).resolve().parents[2]),
            env=dict(os.environ),
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

        if self._stop:
            return {"running": False, "connected": connected, "slots": 0, "cpu": cpu, "mem": mem}

        if not connected:
            # Joined, but coordinator isn't reachable yet; don't spawn slots.
            return {"running": True, "connected": False, "slots": 0, "cpu": cpu, "mem": mem}

        # Scale decisions
        if len(self.slots) == 0:
            self._spawn_slot()
        elif cpu < TARGET_LOW and mem < TARGET_LOW:
            self._spawn_slot()
        elif cpu > TARGET_HIGH or mem > TARGET_HIGH:
            if len(self.slots) > 1:
                self._kill_slot(self.slots[-1])
                self.slots = self.slots[:-1]

        return {"running": True, "connected": True, "slots": len(self.slots), "cpu": cpu, "mem": mem}

    def run_loop(self, on_tick) -> None:
        self.start()
        while not self._stop:
            status = self.tick()
            on_tick(status)
            for _ in range(CHECK_INTERVAL_SECONDS):
                if self._stop:
                    break
                time.sleep(1)
