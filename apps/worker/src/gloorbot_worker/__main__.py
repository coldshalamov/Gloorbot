from __future__ import annotations

import sys

from .gui import run_gui
from .slot_worker import main as slot_worker_main


def main() -> None:
    # When packaged, the GUI process spawns more processes of the same EXE.
    # Those child processes run the slot worker mode.
    if len(sys.argv) >= 2 and sys.argv[1] == "--slot-worker":
        slot_worker_main(sys.argv[2:])
        return
    run_gui()


main()
