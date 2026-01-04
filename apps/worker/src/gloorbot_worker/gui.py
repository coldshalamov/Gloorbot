from __future__ import annotations

import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

# Handle PyInstaller frozen executable - need absolute imports
if getattr(sys, 'frozen', False):
    from gloorbot_worker import api
    from gloorbot_worker.supervisor import Supervisor
    from gloorbot_worker.paths import status_dir
else:
    from . import api
    from .supervisor import Supervisor
    from .paths import status_dir


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Gloorbot Worker")
        self.root.geometry("760x440")
        self.root.resizable(False, False)

        self.supervisor = Supervisor()
        self._thread: threading.Thread | None = None
        self._running = False

        self.join_btn = ttk.Button(root, text="Join", command=self.join)
        self.kill_btn = ttk.Button(root, text="Kill", command=self.kill, state="disabled")

        self.join_btn.pack(pady=14)
        self.kill_btn.pack(pady=4)

        self.status = tk.StringVar(value="Checking for Chrome...")
        ttk.Label(root, textvariable=self.status).pack(pady=10)

        self.stats = tk.StringVar(value="")
        ttk.Label(root, textvariable=self.stats, justify="left").pack(pady=8)

        self.server = tk.StringVar(value="")
        ttk.Label(root, textvariable=self.server, justify="left").pack(pady=8)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Check for Chrome on startup
        self._check_chrome()
        self._poll()

    def _check_chrome(self) -> None:
        """Check if Google Chrome is installed. Disable Join if not."""
        import shutil
        import os
        
        chrome_found = False
        # Check common Chrome locations on Windows
        chrome_paths = [
            shutil.which("chrome"),
            shutil.which("google-chrome"),
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]
        for path in chrome_paths:
            if path and os.path.isfile(path):
                chrome_found = True
                break
        
        if chrome_found:
            self.status.set("Ready. Click Join.")
        else:
            self.status.set("⚠️ Chrome NOT FOUND! Please install Google Chrome to use this app.")
            self.join_btn.configure(state="disabled")
            self.stats.set("Download Chrome: https://www.google.com/chrome/")


    def join(self) -> None:
        if self._running:
            return
        self._running = True
        self.join_btn.configure(state="disabled")
        self.kill_btn.configure(state="normal")
        self.status.set("Joined. Connecting to coordinator…")

        def run() -> None:
            def on_tick(st: dict) -> None:
                if not st.get("connected"):
                    self.status.set("Joined. Waiting for coordinator…")
                else:
                    self.status.set("Joined. Running.")
                self.stats.set(
                    f"Local:\n"
                    f"  Slots: {st.get('slots')}\n"
                    f"  CPU: {st.get('cpu'):.1f}%\n"
                    f"  MEM: {st.get('mem'):.1f}%\n"
                )
            try:
                self.supervisor.run_loop(on_tick)
            finally:
                self._running = False

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def kill(self) -> None:
        self.status.set("Stopping…")
        self.supervisor.stop()
        self.join_btn.configure(state="normal")
        self.kill_btn.configure(state="disabled")
        self.status.set("Stopped. Click Join to resume.")

    def _poll(self) -> None:
        status = api.fetch_status()
        if status:
            self.server.set(
                f"Coordinator:\n"
                f"  Active clients: {status.get('clients', {}).get('active')}\n"
                f"  Tasks: {status.get('tasks', {}).get('completed')}/{status.get('tasks', {}).get('total')} completed\n"
            )
        else:
            self.server.set("Coordinator: unreachable (worker will keep trying).")
        self.root.after(5000, self._poll)

    def on_close(self) -> None:
        try:
            self.supervisor.stop()
        finally:
            self.root.destroy()


def run_gui() -> None:
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except Exception:
        pass

    try:
        import atexit
        import os

        import psutil

        pid_file = status_dir() / "worker_gui.pid"
        if pid_file.exists():
            try:
                prev_pid = int(pid_file.read_text(encoding="utf-8").strip())
            except Exception:
                prev_pid = -1
            if prev_pid > 0 and psutil.pid_exists(prev_pid):
                try:
                    prev = psutil.Process(prev_pid)
                    if prev.is_running() and prev.status() != psutil.STATUS_ZOMBIE:
                        messagebox.showerror(
                            "Gloorbot Worker",
                            "Gloorbot Worker is already running.\n\n"
                            "Close the existing window (or end the process) before starting another.",
                        )
                        root.destroy()
                        return
                except Exception:
                    # If we can't inspect the process, assume it's running to avoid duplicates.
                    messagebox.showerror(
                        "Gloorbot Worker",
                        "Gloorbot Worker may already be running.\n\n"
                        "Close the existing window (or end the process) before starting another.",
                    )
                    root.destroy()
                    return

        pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid_file.write_text(str(os.getpid()), encoding="utf-8")
        atexit.register(lambda: pid_file.unlink(missing_ok=True))
    except Exception:
        pass

    # Try to load icon
    try:
        import os
        from pathlib import Path
        # When frozen, the icon is in the same dir as the EXE
        # In dev, it might be in apps/worker or PARALLEL
        exe_dir = Path(sys.executable).parent
        spec_dir = Path(__file__).resolve().parents[2]
        icon_candidates = [
            exe_dir / "gloorbot.ico",
            spec_dir / "gloorbot.ico",
            spec_dir.parent.parent / "PARALLEL" / "gloorbot.ico", # for dev if converted
        ]
        for cand in icon_candidates:
            if cand.exists():
                root.iconbitmap(str(cand))
                break
    except Exception:
        pass

    App(root)
    root.mainloop()
