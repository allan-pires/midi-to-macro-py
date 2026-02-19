"""Entry point: request admin (Windows), then run the GUI."""

import tkinter as tk

from midi_to_macro import parse_midi, build_mcr_lines, export_mcr
from midi_to_macro.admin import request_admin_and_restart
from midi_to_macro.app import App


def main():
    request_admin_and_restart()
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
