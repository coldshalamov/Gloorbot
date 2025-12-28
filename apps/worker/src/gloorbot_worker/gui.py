from __future__ import annotations

import os
import shutil
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

# Handle PyInstaller frozen executable - need absolute imports
if getattr(sys, 'frozen', False):
    from gloorbot_worker import api
    from gloorbot_worker.supervisor import Supervisor
else:
    from . import api
    from .supervisor import Supervisor


def _find_chrome() -> str | None:
    """Check if Google Chrome is installed and return its path."""
    # Check common Windows Chrome locations
    possible_paths = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    # Also check if 'chrome' is in PATH (unlikely on Windows but worth checking)
    if shutil.which("chrome"):
        return shutil.which("chrome")
    return None


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

        self.status = tk.StringVar(value="Ready. Click Join.")
        ttk.Label(root, textvariable=self.status).pack(pady=10)

        self.stats = tk.StringVar(value="")
        ttk.Label(root, textvariable=self.stats, justify="left").pack(pady=8)

        self.server = tk.StringVar(value="")
        ttk.Label(root, textvariable=self.server, justify="left").pack(pady=8)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._poll()

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

    # Check for Chrome before starting
    if not _find_chrome():
        root.withdraw()  # Hide main window temporarily
        result = messagebox.askyesno(
            "Chrome Required",
            "Google Chrome is required for reliable scraping but was not found.\n\n"
            "The worker can still run with the bundled Chromium browser, but you may "
            "experience more blocking from Lowe's website.\n\n"
            "Would you like to download Google Chrome now?\n\n"
            "(Click 'No' to continue anyway with Chromium)",
        )
        if result:
            webbrowser.open("https://www.google.com/chrome/")
            messagebox.showinfo(
                "Install Chrome",
                "Please install Chrome, then restart Gloorbot Worker."
            )
            root.destroy()
            return
        root.deiconify()  # Show main window again

    App(root)
    root.mainloop()
