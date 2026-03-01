"""Check for updates via GitHub releases and open/download latest."""

from __future__ import annotations

import json
import re
import tempfile
import urllib.error
import urllib.request
import webbrowser

from midi_to_macro.version import (
    GITHUB_RELEASES_API,
    GITHUB_RELEASES_PAGE,
    __version__ as current_version,
)


def _parse_version(s: str) -> tuple[int, ...]:
    """Convert version string to comparable tuple (e.g. '1.2.3' -> (1, 2, 3))."""
    s = re.sub(r"[^0-9.].*$", "", s.strip())
    parts = s.split(".")[:4]
    return tuple(int(p) if p.isdigit() else 0 for p in parts)


def check_for_updates(timeout: float = 10.0) -> tuple[str | None, str | None, str | None, str | None]:
    """
    Fetch latest release from GitHub. Returns (latest_version, html_url, body, download_url).
    download_url is the first browser_download_url asset, or None.
    Returns (None, None, None, None) on error or if no release.
    """
    try:
        req = urllib.request.Request(
            GITHUB_RELEASES_API,
            headers={"Accept": "application/vnd.github.v3+json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
    except (urllib.error.URLError, OSError, ValueError):
        return (None, None, None, None)

    try:
        release = json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return (None, None, None, None)

    tag = release.get("tag_name") or ""
    # Strip leading 'v' if present
    latest_version = tag.lstrip("v").strip() or None
    html_url = release.get("html_url") or GITHUB_RELEASES_PAGE
    body = (release.get("body") or "").strip() or None
    download_url = None
    assets = release.get("assets") or []
    for a in assets:
        url = a.get("browser_download_url")
        if url:
            download_url = url
            break

    return (latest_version, html_url, body, download_url)


def is_newer(latest: str, current: str = current_version) -> bool:
    """Return True if latest > current."""
    return _parse_version(latest) > _parse_version(current)


def open_releases_page() -> None:
    """Open the GitHub releases page in the default browser."""
    webbrowser.open(GITHUB_RELEASES_PAGE)


def open_release_page(url: str) -> None:
    """Open a specific release URL in the default browser."""
    webbrowser.open(url)


def download_update(download_url: str, timeout: float = 60.0) -> str | None:
    """
    Download the update file to a temp file. Returns the path to the downloaded file,
    or None on failure. Caller is responsible for running the file (e.g. os.startfile) and
    optionally cleaning up.
    """
    if not download_url:
        return None
    try:
        req = urllib.request.Request(download_url, headers={"Accept": "application/octet-stream"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
    except (urllib.error.URLError, OSError, ValueError):
        return None
    # Infer extension from URL
    path = download_url.split("/")[-1].split("?")[0] or "update"
    if not path.endswith(".exe") and not path.endswith(".msi"):
        path = path + ".exe"
    fd, path = tempfile.mkstemp(suffix="_" + path)
    try:
        with open(fd, "wb") as f:
            f.write(data)
        return path
    except OSError:
        return None
