from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import ttk

from . import api
from .supervisor import Supervisor


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
    App(root)
    root.mainloop()
