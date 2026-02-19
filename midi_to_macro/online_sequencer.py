"""Online Sequencer (onlinesequencer.net) integration: fetch sequence list, open in browser."""

import html as html_module
import re
import urllib.request
import webbrowser

BASE = "https://onlinesequencer.net"
SEQUENCES = f"{BASE}/sequences"
SEQUENCES_NEWEST = f"{BASE}/sequences?sort=1"
SEQUENCES_POPULAR = f"{BASE}/sequences?sort=2"
SEQUENCES_RECENTLY_SHARED = f"{BASE}/playlist/1"

# sort: 1=newest, 2=popular, 3=most notes, 4=oldest, 5=longest
SORT_OPTIONS = [
    ("1", "Newest"),
    ("2", "Popular"),
    ("3", "Most notes"),
    ("4", "Oldest"),
    ("5", "Longest"),
]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0"


def fetch_sequences(sort: str = "1", timeout: float = 15) -> list[tuple[str, str]]:
    """Fetch sequence list from onlinesequencer.net/sequences?sort=... Returns [(id, title), ...]."""
    url = f"{BASE}/sequences?sort={sort}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read().decode("utf-8", errors="replace")
    # <div class="preview" title="..."> ... <a href="/ID"></a>
    blocks = re.findall(
        r'<div class="preview" title="([^"]*)"[^>]*>.*?<a href="/(\d+)"',
        data,
        re.DOTALL,
    )
    result = []
    for title, sid in blocks:
        title = html_module.unescape(title.strip()) or f"Sequence {sid}"
        result.append((sid, title))
    return result


def open_browse(sort: str = "1") -> None:
    """Open the sequences list in the browser. sort: 1=newest, 2=popular, 3=most notes, 4=oldest, 5=longest."""
    url = f"{BASE}/sequences?sort={sort}" if sort else SEQUENCES
    webbrowser.open(url)


def open_sequence(sequence_id: str | None) -> bool:
    """Open a specific sequence by ID (number) or full URL. Returns False if invalid."""
    if not sequence_id or not str(sequence_id).strip():
        return False
    s = str(sequence_id).strip()
    if s.isdigit():
        webbrowser.open(f"{BASE}/{s}")
        return True
    if s.startswith("http://") or s.startswith("https://"):
        if "onlinesequencer.net" in s:
            webbrowser.open(s)
            return True
    return False


def open_recently_shared() -> None:
    """Open the Recently Shared playlist (last 50 from chat)."""
    webbrowser.open(SEQUENCES_RECENTLY_SHARED)


def open_newest() -> None:
    """Open sequences sorted by newest."""
    webbrowser.open(SEQUENCES_NEWEST)


def open_popular() -> None:
    """Open sequences sorted by popular."""
    webbrowser.open(SEQUENCES_POPULAR)
