from __future__ import annotations

import sys
import os

# Handle PyInstaller frozen executable - need absolute imports
if getattr(sys, 'frozen', False):
    # Running as compiled/frozen executable
    from gloorbot_worker.gui import run_gui
    from gloorbot_worker.slot_worker import main as slot_worker_main
else:
    # Running as normal Python script
    from .gui import run_gui
    from .slot_worker import main as slot_worker_main


def main() -> None:
    # When packaged, the GUI process spawns more processes of the same EXE.
    # Those child processes run the slot worker mode.
    if len(sys.argv) >= 2 and sys.argv[1] == "--slot-worker":
        slot_worker_main(sys.argv[2:])
        return
    run_gui()


if __name__ == "__main__":
    main()
