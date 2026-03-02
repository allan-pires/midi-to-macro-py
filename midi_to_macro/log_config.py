"""Configure application logging to a file and stderr."""

import logging
import os
import sys


def setup_logging() -> None:
    """Configure root logger: file in temp dir + stderr at INFO."""
    root = logging.getLogger("midi_to_macro")
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    log_path = None
    try:
        log_dir = os.path.join(os.environ.get("TEMP", os.path.expanduser("~")), "WhereSongsMeet")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "app.log")
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except OSError:
        pass

    eh = logging.StreamHandler(sys.stderr)
    eh.setLevel(logging.INFO)
    eh.setFormatter(fmt)
    root.addHandler(eh)

    root.info("Logging started; file: %s", log_path or "(none)")
