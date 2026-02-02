from __future__ import annotations

import sys
import threading
import shutil
import tkinter as tk
from tkinter import messagebox, ttk

# Handle PyInstaller frozen executable - need absolute imports
if getattr(sys, "frozen", False):
    from gloorbot_worker import api
    from gloorbot_worker.supervisor import Supervisor
    from gloorbot_worker.paths import status_dir, profiles_dir
    from gloorbot_worker import __version__
    from gloorbot_worker.settings import (
        PerformanceSettings,
        get_settings,
        set_settings,
        reset_settings,
    )
else:
    from . import api
    from .supervisor import Supervisor
    from .paths import status_dir, profiles_dir
    from . import __version__
    from .settings import (
        PerformanceSettings,
        get_settings,
        set_settings,
        reset_settings,
    )


class SettingsDialog:
    """Performance tuning dialog with sliders and checkboxes."""

    def __init__(self, parent: tk.Tk, on_save: callable) -> None:
        self.on_save = on_save
        self.settings = get_settings()

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Performance Tuning")
        self.dialog.geometry("520x680")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Create notebook (tabs)
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1: Browser & Timing
        timing_frame = ttk.Frame(notebook, padding=10)
        notebook.add(timing_frame, text="Timing")

        # Tab 2: Resource Blocking
        resource_frame = ttk.Frame(notebook, padding=10)
        notebook.add(resource_frame, text="Resources")

        # Tab 3: Presets
        preset_frame = ttk.Frame(notebook, padding=10)
        notebook.add(preset_frame, text="Presets")

        # === TIMING TAB ===
        self._build_timing_tab(timing_frame)

        # === RESOURCE TAB ===
        self._build_resource_tab(resource_frame)

        # === PRESET TAB ===
        self._build_preset_tab(preset_frame)

        # Buttons at bottom
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(fill="x", padx=10, pady=10)

        ttk.Button(btn_frame, text="Save", command=self._save).pack(
            side="right", padx=5
        )
        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy).pack(
            side="right"
        )
        ttk.Button(btn_frame, text="Reset to Defaults", command=self._reset).pack(
            side="left"
        )

    def _build_timing_tab(self, parent: ttk.Frame) -> None:
        """Build the timing settings tab."""
        # Browser Count
        lf = ttk.LabelFrame(parent, text="Browser Pool", padding=10)
        lf.pack(fill="x", pady=5)

        ttk.Label(lf, text="Fixed Browser Count (0 = dynamic):").pack(anchor="w")
        self.fixed_browsers = tk.IntVar(value=self.settings.fixed_browser_count)
        browser_scale = ttk.Scale(
            lf,
            from_=0,
            to=10,
            orient="horizontal",
            variable=self.fixed_browsers,
            command=lambda v: self._update_label(v, self.browser_label),
        )
        browser_scale.pack(fill="x")
        self.browser_label = ttk.Label(lf, text=str(self.settings.fixed_browser_count))
        self.browser_label.pack(anchor="e")

        ttk.Label(lf, text="Max Browsers (when dynamic):").pack(
            anchor="w", pady=(10, 0)
        )
        self.max_browsers = tk.IntVar(value=self.settings.max_browsers)
        max_scale = ttk.Scale(
            lf,
            from_=1,
            to=10,
            orient="horizontal",
            variable=self.max_browsers,
            command=lambda v: self._update_label(v, self.max_label),
        )
        max_scale.pack(fill="x")
        self.max_label = ttk.Label(lf, text=str(self.settings.max_browsers))
        self.max_label.pack(anchor="e")

        # Navigation Delays
        lf2 = ttk.LabelFrame(parent, text="Navigation Timing (seconds)", padding=10)
        lf2.pack(fill="x", pady=5)

        ttk.Label(lf2, text="Nav Delay Min:").pack(anchor="w")
        self.nav_min = tk.DoubleVar(value=self.settings.nav_delay_min)
        ttk.Scale(
            lf2,
            from_=0.5,
            to=5.0,
            orient="horizontal",
            variable=self.nav_min,
            command=lambda v: self._update_label(v, self.nav_min_label, 2),
        ).pack(fill="x")
        self.nav_min_label = ttk.Label(lf2, text=f"{self.settings.nav_delay_min:.2f}")
        self.nav_min_label.pack(anchor="e")

        ttk.Label(lf2, text="Nav Delay Max:").pack(anchor="w", pady=(10, 0))
        self.nav_max = tk.DoubleVar(value=self.settings.nav_delay_max)
        ttk.Scale(
            lf2,
            from_=1.0,
            to=8.0,
            orient="horizontal",
            variable=self.nav_max,
            command=lambda v: self._update_label(v, self.nav_max_label, 2),
        ).pack(fill="x")
        self.nav_max_label = ttk.Label(lf2, text=f"{self.settings.nav_delay_max:.2f}")
        self.nav_max_label.pack(anchor="e")

        # Click Delays
        lf3 = ttk.LabelFrame(parent, text="Click Timing (seconds)", padding=10)
        lf3.pack(fill="x", pady=5)

        ttk.Label(lf3, text="Click Delay Min:").pack(anchor="w")
        self.click_min = tk.DoubleVar(value=self.settings.click_delay_min)
        ttk.Scale(
            lf3,
            from_=0.01,
            to=1.0,
            orient="horizontal",
            variable=self.click_min,
            command=lambda v: self._update_label(v, self.click_min_label, 2),
        ).pack(fill="x")
        self.click_min_label = ttk.Label(
            lf3, text=f"{self.settings.click_delay_min:.2f}"
        )
        self.click_min_label.pack(anchor="e")

        ttk.Label(lf3, text="Click Delay Max:").pack(anchor="w", pady=(10, 0))
        self.click_max = tk.DoubleVar(value=self.settings.click_delay_max)
        ttk.Scale(
            lf3,
            from_=0.05,
            to=2.0,
            orient="horizontal",
            variable=self.click_max,
            command=lambda v: self._update_label(v, self.click_max_label, 2),
        ).pack(fill="x")
        self.click_max_label = ttk.Label(
            lf3, text=f"{self.settings.click_delay_max:.2f}"
        )
        self.click_max_label.pack(anchor="e")

        # Inter-lease delay
        lf4 = ttk.LabelFrame(parent, text="Inter-Task Delay (seconds)", padding=10)
        lf4.pack(fill="x", pady=5)

        ttk.Label(lf4, text="Delay between tasks Min:").pack(anchor="w")
        self.inter_min = tk.DoubleVar(value=self.settings.inter_lease_delay_min)
        ttk.Scale(
            lf4,
            from_=0.5,
            to=5.0,
            orient="horizontal",
            variable=self.inter_min,
            command=lambda v: self._update_label(v, self.inter_min_label, 2),
        ).pack(fill="x")
        self.inter_min_label = ttk.Label(
            lf4, text=f"{self.settings.inter_lease_delay_min:.2f}"
        )
        self.inter_min_label.pack(anchor="e")

        ttk.Label(lf4, text="Delay between tasks Max:").pack(anchor="w", pady=(10, 0))
        self.inter_max = tk.DoubleVar(value=self.settings.inter_lease_delay_max)
        ttk.Scale(
            lf4,
            from_=1.0,
            to=10.0,
            orient="horizontal",
            variable=self.inter_max,
            command=lambda v: self._update_label(v, self.inter_max_label, 2),
        ).pack(fill="x")
        self.inter_max_label = ttk.Label(
            lf4, text=f"{self.settings.inter_lease_delay_max:.2f}"
        )
        self.inter_max_label.pack(anchor="e")

    def _build_resource_tab(self, parent: ttk.Frame) -> None:
        """Build the resource blocking settings tab."""
        # Resource Blocking
        lf = ttk.LabelFrame(parent, text="Resource Blocking", padding=10)
        lf.pack(fill="x", pady=5)

        ttk.Label(
            lf,
            text="Block resources to save bandwidth and speed up scraping.\n"
            "CAUTION: Blocking too much may trigger Akamai detection.",
            wraplength=450,
            foreground="gray",
        ).pack(anchor="w", pady=(0, 10))

        self.block_images = tk.BooleanVar(value=self.settings.block_images)
        ttk.Checkbutton(
            lf,
            text="Block Images (60-70% bandwidth savings)",
            variable=self.block_images,
        ).pack(anchor="w")

        self.block_fonts = tk.BooleanVar(value=self.settings.block_fonts)
        ttk.Checkbutton(
            lf, text="Block Fonts (5-10% bandwidth savings)", variable=self.block_fonts
        ).pack(anchor="w")

        self.block_media = tk.BooleanVar(value=self.settings.block_media)
        ttk.Checkbutton(
            lf, text="Block Audio/Video (safe, rarely used)", variable=self.block_media
        ).pack(anchor="w")

        self.block_analytics = tk.BooleanVar(value=self.settings.block_analytics)
        ttk.Checkbutton(
            lf, text="Block Analytics (except Akamai)", variable=self.block_analytics
        ).pack(anchor="w")

        self.abort_images = tk.BooleanVar(value=self.settings.abort_images_after_dom)
        ttk.Checkbutton(
            lf,
            text="Abort images after DOM renders (hybrid approach)",
            variable=self.abort_images,
        ).pack(anchor="w")

        # Viewport
        lf2 = ttk.LabelFrame(parent, text="Viewport Size", padding=10)
        lf2.pack(fill="x", pady=5)

        ttk.Label(
            lf2,
            text="Smaller viewport = faster rendering, less memory.\n"
            "1280x720 is 37% fewer pixels than 1440x900.",
            wraplength=450,
            foreground="gray",
        ).pack(anchor="w", pady=(0, 10))

        ttk.Label(lf2, text="Width:").pack(anchor="w")
        self.viewport_width = tk.IntVar(value=self.settings.viewport_width)
        ttk.Scale(
            lf2,
            from_=1024,
            to=1920,
            orient="horizontal",
            variable=self.viewport_width,
            command=lambda v: self._update_label(v, self.vw_label),
        ).pack(fill="x")
        self.vw_label = ttk.Label(lf2, text=str(self.settings.viewport_width))
        self.vw_label.pack(anchor="e")

        ttk.Label(lf2, text="Height:").pack(anchor="w", pady=(10, 0))
        self.viewport_height = tk.IntVar(value=self.settings.viewport_height)
        ttk.Scale(
            lf2,
            from_=600,
            to=1080,
            orient="horizontal",
            variable=self.viewport_height,
            command=lambda v: self._update_label(v, self.vh_label),
        ).pack(fill="x")
        self.vh_label = ttk.Label(lf2, text=str(self.settings.viewport_height))
        self.vh_label.pack(anchor="e")

        # Browser Args
        lf3 = ttk.LabelFrame(parent, text="Browser Optimizations", padding=10)
        lf3.pack(fill="x", pady=5)

        self.disable_gpu = tk.BooleanVar(value=self.settings.disable_gpu)
        ttk.Checkbutton(
            lf3,
            text="Disable GPU (faster on low-end machines)",
            variable=self.disable_gpu,
        ).pack(anchor="w")

        self.memory_off = tk.BooleanVar(value=self.settings.memory_pressure_off)
        ttk.Checkbutton(
            lf3,
            text="Disable Memory Pressure (prevents OOM crashes)",
            variable=self.memory_off,
        ).pack(anchor="w")

        self.bg_networking = tk.BooleanVar(
            value=self.settings.disable_background_networking
        )
        ttk.Checkbutton(
            lf3, text="Disable Background Networking", variable=self.bg_networking
        ).pack(anchor="w")

    def _build_preset_tab(self, parent: ttk.Frame) -> None:
        """Build the presets tab."""
        ttk.Label(
            parent,
            text="Quick presets for different use cases.\n"
            "Click a preset to load its settings, then Save to apply.",
            wraplength=450,
        ).pack(anchor="w", pady=(0, 20))

        presets = [
            (
                "Conservative",
                "Slow but safe. Use if getting blocked.",
                PerformanceSettings.conservative,
            ),
            (
                "Balanced (Default)",
                "Proven reliable settings.",
                PerformanceSettings.balanced,
            ),
            (
                "Aggressive",
                "Faster, higher block risk.",
                PerformanceSettings.aggressive,
            ),
            (
                "Ultra Aggressive",
                "Maximum speed. Requires good IPs.",
                PerformanceSettings.ultra_aggressive,
            ),
        ]

        for name, desc, preset_fn in presets:
            frame = ttk.Frame(parent)
            frame.pack(fill="x", pady=5)

            ttk.Button(
                frame,
                text=name,
                width=20,
                command=lambda fn=preset_fn: self._load_preset(fn),
            ).pack(side="left")

            ttk.Label(frame, text=desc, foreground="gray").pack(side="left", padx=10)

        # Warning
        ttk.Label(
            parent,
            text="\nAkamai Detection Warning:\n"
            "- NEVER run headless (instant block)\n"
            "- NEVER block /_sec/ scripts\n"
            "- Aggressive settings may get you blocked\n"
            "- If blocked, switch to Conservative preset",
            wraplength=450,
            foreground="red",
        ).pack(anchor="w", pady=(20, 0))

    def _update_label(self, value: str, label: ttk.Label, decimals: int = 0) -> None:
        """Update a label with the current slider value."""
        try:
            if decimals > 0:
                label.config(text=f"{float(value):.{decimals}f}")
            else:
                label.config(text=str(int(float(value))))
        except Exception:
            pass

    def _load_preset(self, preset_fn: callable) -> None:
        """Load a preset and update all UI elements."""
        preset = preset_fn()
        self.settings = preset

        # Update all variables
        self.fixed_browsers.set(preset.fixed_browser_count)
        self.max_browsers.set(preset.max_browsers)
        self.nav_min.set(preset.nav_delay_min)
        self.nav_max.set(preset.nav_delay_max)
        self.click_min.set(preset.click_delay_min)
        self.click_max.set(preset.click_delay_max)
        self.inter_min.set(preset.inter_lease_delay_min)
        self.inter_max.set(preset.inter_lease_delay_max)
        self.block_images.set(preset.block_images)
        self.block_fonts.set(preset.block_fonts)
        self.block_media.set(preset.block_media)
        self.block_analytics.set(preset.block_analytics)
        self.abort_images.set(preset.abort_images_after_dom)
        self.viewport_width.set(preset.viewport_width)
        self.viewport_height.set(preset.viewport_height)
        self.disable_gpu.set(preset.disable_gpu)
        self.memory_off.set(preset.memory_pressure_off)
        self.bg_networking.set(preset.disable_background_networking)

        # Update labels
        self._update_label(str(preset.fixed_browser_count), self.browser_label)
        self._update_label(str(preset.max_browsers), self.max_label)
        self._update_label(str(preset.nav_delay_min), self.nav_min_label, 2)
        self._update_label(str(preset.nav_delay_max), self.nav_max_label, 2)
        self._update_label(str(preset.click_delay_min), self.click_min_label, 2)
        self._update_label(str(preset.click_delay_max), self.click_max_label, 2)
        self._update_label(str(preset.inter_lease_delay_min), self.inter_min_label, 2)
        self._update_label(str(preset.inter_lease_delay_max), self.inter_max_label, 2)
        self._update_label(str(preset.viewport_width), self.vw_label)
        self._update_label(str(preset.viewport_height), self.vh_label)

        messagebox.showinfo(
            "Preset Loaded",
            f"Loaded '{preset_fn.__name__}' preset.\nClick Save to apply.",
        )

    def _save(self) -> None:
        """Save current settings."""
        self.settings.fixed_browser_count = int(self.fixed_browsers.get())
        self.settings.max_browsers = int(self.max_browsers.get())
        self.settings.nav_delay_min = float(self.nav_min.get())
        self.settings.nav_delay_max = float(self.nav_max.get())
        self.settings.click_delay_min = float(self.click_min.get())
        self.settings.click_delay_max = float(self.click_max.get())
        self.settings.inter_lease_delay_min = float(self.inter_min.get())
        self.settings.inter_lease_delay_max = float(self.inter_max.get())
        self.settings.block_images = bool(self.block_images.get())
        self.settings.block_fonts = bool(self.block_fonts.get())
        self.settings.block_media = bool(self.block_media.get())
        self.settings.block_analytics = bool(self.block_analytics.get())
        self.settings.abort_images_after_dom = bool(self.abort_images.get())
        self.settings.viewport_width = int(self.viewport_width.get())
        self.settings.viewport_height = int(self.viewport_height.get())
        self.settings.disable_gpu = bool(self.disable_gpu.get())
        self.settings.memory_pressure_off = bool(self.memory_off.get())
        self.settings.disable_background_networking = bool(self.bg_networking.get())

        set_settings(self.settings)
        self.on_save(self.settings)
        self.dialog.destroy()
        messagebox.showinfo(
            "Settings Saved",
            "Performance settings saved.\nRestart workers for changes to take effect.",
        )

    def _reset(self) -> None:
        """Reset to default settings."""
        if messagebox.askyesno("Reset Settings", "Reset all settings to defaults?"):
            self.settings = reset_settings()
            self._load_preset(PerformanceSettings.balanced)


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"Gloorbot Worker v{__version__}")
        self.root.geometry("760x520")
        self.root.resizable(False, False)

        self.supervisor = Supervisor()
        self._thread: threading.Thread | None = None
        self._running = False
        self._settings = get_settings()

        # Version label at bottom-right
        v_label = ttk.Label(root, text=f"v{__version__}", foreground="gray")
        v_label.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-5)

        # Main buttons frame
        btn_frame = ttk.Frame(root)
        btn_frame.pack(pady=14)

        self.join_btn = ttk.Button(btn_frame, text="Join", command=self.join)
        self.kill_btn = ttk.Button(
            btn_frame, text="Kill", command=self.kill, state="disabled"
        )
        self.settings_btn = ttk.Button(
            btn_frame, text="Settings", command=self._open_settings
        )

        self.join_btn.pack(side="left", padx=5)
        self.kill_btn.pack(side="left", padx=5)
        self.settings_btn.pack(side="left", padx=5)

        self.status = tk.StringVar(value="Checking for Chrome...")
        ttk.Label(root, textvariable=self.status).pack(pady=10)

        self.stats = tk.StringVar(value="")
        ttk.Label(root, textvariable=self.stats, justify="left").pack(pady=8)

        self.server = tk.StringVar(value="")
        ttk.Label(root, textvariable=self.server, justify="left").pack(pady=8)

        # Settings summary
        self.settings_summary = tk.StringVar(value="")
        self._update_settings_summary()
        ttk.Label(
            root, textvariable=self.settings_summary, justify="left", foreground="gray"
        ).pack(pady=8)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Check for Chrome on startup
        self._check_chrome()
        self._poll()

    def _update_settings_summary(self) -> None:
        """Update the settings summary display."""
        s = self._settings
        mode = (
            f"Fixed {s.fixed_browser_count}"
            if s.fixed_browser_count > 0
            else f"Dynamic (max {s.max_browsers})"
        )
        blocking = []
        if s.block_images:
            blocking.append("images")
        if s.block_fonts:
            blocking.append("fonts")
        if s.block_media:
            blocking.append("media")
        blocking_str = ", ".join(blocking) if blocking else "none"

        self.settings_summary.set(
            f"Performance Settings:\n"
            f"  Browsers: {mode}\n"
            f"  Nav delay: {s.nav_delay_min:.1f}-{s.nav_delay_max:.1f}s\n"
            f"  Click delay: {s.click_delay_min:.2f}-{s.click_delay_max:.2f}s\n"
            f"  Blocking: {blocking_str}\n"
            f"  Viewport: {s.viewport_width}x{s.viewport_height}"
        )

    def _open_settings(self) -> None:
        """Open the settings dialog."""

        def on_save(settings: PerformanceSettings) -> None:
            self._settings = settings
            self._update_settings_summary()

        SettingsDialog(self.root, on_save)

    def _check_chrome(self) -> None:
        """Check if Google Chrome is installed.

        The worker can still run using the bundled Playwright Chromium when the
        installer ships it, so missing system Chrome should not block starting
        on a fresh machine.
        """
        import shutil
        import os

        chrome_found = False
        # Check common Chrome locations on Windows
        chrome_paths = [
            shutil.which("chrome"),
            shutil.which("google-chrome"),
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(
                r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
            ),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]
        for path in chrome_paths:
            if path and os.path.isfile(path):
                chrome_found = True
                break

        if chrome_found:
            self.status.set("Ready. Click Join.")
        else:
            # Run with bundled browsers (installer includes Playwright Chromium).
            os.environ["GLOORBOT_FORCE_BUNDLED"] = "1"
            os.environ["GLOORBOT_PREFER_CHROME"] = "0"
            self.status.set("Chrome not found. Will use bundled browser. Click Join.")
            self.stats.set(
                "Tip: Installing Chrome can improve reliability vs. bot blocks,\n"
                "but it is not required to run.\n"
                "Download Chrome: https://www.google.com/chrome/"
            )

    def join(self) -> None:
        if self._running:
            return
        self._running = True
        self.join_btn.configure(state="disabled")
        self.kill_btn.configure(state="normal")
        self.settings_btn.configure(state="disabled")  # Disable settings while running
        self.status.set("Joined. Connecting to coordinator...")

        def run() -> None:
            def on_tick(st: dict) -> None:
                if not st.get("connected"):
                    self.status.set("Joined. Waiting for coordinator...")
                else:
                    self.status.set("Joined. Running.")
                blocks = st.get("blocks", 0)
                block_str = f"\n  Blocks: {blocks}" if blocks > 0 else ""
                self.stats.set(
                    f"Local:\n"
                    f"  Slots: {st.get('slots')}\n"
                    f"  CPU: {st.get('cpu'):.1f}%\n"
                    f"  MEM: {st.get('mem'):.1f}%{block_str}"
                )

            try:
                self.supervisor.run_loop(on_tick)
            finally:
                self._running = False

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def kill(self) -> None:
        self.status.set("Stopping...")
        self.supervisor.stop()
        self.join_btn.configure(state="normal")
        self.kill_btn.configure(state="disabled")
        self.settings_btn.configure(state="normal")  # Re-enable settings
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

        def _any_worker_process_running() -> bool:
            try:
                for proc in psutil.process_iter(["name", "cmdline"]):
                    name = (proc.info.get("name") or "").lower()
                    if "gloorbotworker" in name:
                        return True
                    cmd = " ".join(proc.info.get("cmdline") or [])
                    if "gloorbot_worker" in cmd and "--slot-worker" in cmd:
                        return True
            except Exception:
                return False
            return False

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
            else:
                # Stale PID file: previous run likely crashed. If no worker processes
                # are running, remove stale profiles to avoid corrupted sessions.
                if not _any_worker_process_running():
                    try:
                        prof_dir = profiles_dir()
                        if prof_dir.exists():
                            shutil.rmtree(prof_dir, ignore_errors=True)
                            prof_dir.mkdir(parents=True, exist_ok=True)
                    except Exception:
                        pass

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
            spec_dir.parent.parent
            / "PARALLEL"
            / "gloorbot.ico",  # for dev if converted
        ]
        for cand in icon_candidates:
            if cand.exists():
                root.iconbitmap(str(cand))
                break
    except Exception:
        pass

    App(root)
    root.mainloop()
