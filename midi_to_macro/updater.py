"""Check for updates via GitHub releases and open/download latest."""

from __future__ import annotations

import json
import os
import re
import tempfile
import urllib.error
import urllib.request
import webbrowser
import zipfile

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


def check_for_updates(timeout: float = 10.0) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    """
    Fetch latest release from GitHub. Returns (latest_version, html_url, body, download_url, error_message).
    On success error_message is None. On error returns (None, None, None, None, error_message).
    """
    try:
        req = urllib.request.Request(
            GITHUB_RELEASES_API,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "midi-to-macro-updater",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return (None, None, None, None, "No releases found. Publish a release on GitHub or check the repo in version.py.")
        return (None, None, None, None, f"HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        return (None, None, None, None, str(e.reason) if e.reason else "Connection error")
    except (OSError, ValueError) as e:
        return (None, None, None, None, str(e))

    try:
        release = json.loads(data)
    except (json.JSONDecodeError, TypeError) as e:
        return (None, None, None, None, f"Invalid response: {e}")

    tag = release.get("tag_name") or ""
    # Strip leading 'v' if present
    latest_version = tag.lstrip("v").strip() or None
    html_url = release.get("html_url") or GITHUB_RELEASES_PAGE
    body = (release.get("body") or "").strip() or None
    download_url = None
    assets = release.get("assets") or []
    # Prefer .zip (onedir bundle) for "Download and run" — runs without temp extraction, avoids "Failed to load Python DLL"
    for a in assets:
        url = a.get("browser_download_url")
        name = (a.get("name") or "").lower()
        if url and name.endswith(".zip"):
            download_url = url
            break
    if not download_url:
        for a in assets:
            url = a.get("browser_download_url")
            if url:
                download_url = url
                break

    return (latest_version, html_url, body, download_url, None)


def is_newer(latest: str, current: str = current_version) -> bool:
    """Return True if latest > current."""
    return _parse_version(latest) > _parse_version(current)


def open_releases_page() -> None:
    """Open the GitHub releases page in the default browser."""
    webbrowser.open(GITHUB_RELEASES_PAGE)


def open_release_page(url: str) -> None:
    """Open a specific release URL in the default browser."""
    webbrowser.open(url)


def download_update(
    download_url: str,
    timeout: float = 60.0,
    save_dir: str | None = None,
) -> str | None:
    """
    Download the update. Returns the path to run (exe or folder exe), or None on failure.
    - If URL is .zip and save_dir is set: download zip, extract to save_dir/where-songs-meet/,
      return path to save_dir/where-songs-meet/where-songs-meet.exe (runs with DLLs beside it, no "Failed to load Python DLL").
    - If URL is .exe and save_dir is set: save exe there, return its path.
    - If save_dir is None: save to temp and return path (caller runs or cleans up).
    """
    if not download_url:
        return None
    try:
        req = urllib.request.Request(
            download_url,
            headers={
                "Accept": "application/octet-stream",
                "User-Agent": "midi-to-macro-updater",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
    except (urllib.error.URLError, OSError, ValueError):
        return None
    filename = download_url.split("/")[-1].split("?")[0] or "update"

    if filename.lower().endswith(".zip") and save_dir:
        # Extract onedir bundle so exe runs from a folder with all DLLs
        os.makedirs(save_dir, exist_ok=True)
        zip_path = os.path.join(save_dir, filename)
        try:
            with open(zip_path, "wb") as f:
                f.write(data)
            extract_dir = os.path.join(save_dir, "where-songs-meet")
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(os.path.dirname(extract_dir))
            exe_path = os.path.join(extract_dir, "where-songs-meet.exe")
            try:
                os.remove(zip_path)
            except OSError:
                pass
            return exe_path if os.path.isfile(exe_path) else None
        except (OSError, zipfile.BadZipFile):
            return None

    if not filename.endswith(".exe") and not filename.endswith(".msi"):
        filename = filename + ".exe"

    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        path = os.path.join(save_dir, filename)
        try:
            with open(path, "wb") as f:
                f.write(data)
            return path
        except OSError:
            return None

    fd, path = tempfile.mkstemp(suffix="_" + filename)
    try:
        with open(fd, "wb") as f:
            f.write(data)
        return path
    except OSError:
        return None
