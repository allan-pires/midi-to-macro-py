"""Entry point: request admin (Windows), then run the GUI."""

import logging
import sys
import tkinter as tk

from midi_to_macro import parse_midi, build_mcr_lines, export_mcr
from midi_to_macro.admin import request_admin_and_restart
from midi_to_macro.app import App
from midi_to_macro.log_config import setup_logging


def main():
    setup_logging()
    log = logging.getLogger("midi_to_macro.main")
    request_admin_and_restart()
    root = tk.Tk()
    try:
        App(root)
        root.mainloop()
    except Exception as e:
        log.exception("Startup error")
        root.destroy()
        from tkinter import messagebox
        messagebox.showerror('Startup error', str(e))
        sys.exit(1)


if __name__ == '__main__':
    main()
