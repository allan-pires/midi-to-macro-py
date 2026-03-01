"""Load active theme (dark/light) and persist user choice."""

import os

_SETTINGS_DIR = os.path.join(os.path.expanduser("~"), ".midi_to_macro")
_THEME_FILE = os.path.join(_SETTINGS_DIR, "theme.txt")
_DEFAULT = "dark"


def get_theme_name() -> str:
    """Return 'dark' or 'light' from saved preference."""
    if not os.path.isfile(_THEME_FILE):
        return _DEFAULT
    try:
        with open(_THEME_FILE, encoding="utf-8") as f:
            name = (f.read() or "").strip().lower()
        return name if name in ("dark", "light") else _DEFAULT
    except OSError:
        return _DEFAULT


def set_theme(name: str) -> None:
    """Save theme preference ('dark' or 'light'). Caller should restart the app."""
    if name not in ("dark", "light"):
        return
    try:
        os.makedirs(_SETTINGS_DIR, exist_ok=True)
        with open(_THEME_FILE, "w", encoding="utf-8") as f:
            f.write(name)
    except OSError:
        pass


def get_theme():
    """Return the active theme module (same interface as theme.py)."""
    if get_theme_name() == "light":
        from midi_to_macro import theme_light
        return theme_light
    from midi_to_macro import theme
    return theme
