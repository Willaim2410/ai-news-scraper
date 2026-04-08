"""
Persistent deduplication — remembers what was seen across daily runs.
Stores MD5 hashes of normalized titles in data/seen_hashes.json.
Hashes older than 7 days are pruned automatically.
"""

import hashlib
import json
import logging
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

log = logging.getLogger(__name__)

HASHES_FILE = Path(__file__).parent / "data" / "seen_hashes.json"
RETENTION_DAYS = 7


def _normalize(title: str) -> str:
    return re.sub(r"[^a-z0-9]", "", title.lower())[:80]


def _hash(title: str) -> str:
    return hashlib.md5(_normalize(title).encode()).hexdigest()


def _load() -> dict[str, str]:
    if not HASHES_FILE.exists():
        return {}
    try:
        with open(HASHES_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save(hashes: dict[str, str]):
    HASHES_FILE.parent.mkdir(exist_ok=True)
    with open(HASHES_FILE, "w") as f:
        json.dump(hashes, f, indent=2)


def _prune(hashes: dict[str, str]) -> dict[str, str]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    cutoff_str = cutoff.isoformat()
    return {h: ts for h, ts in hashes.items() if ts > cutoff_str}


def filter_new(items: list[dict]) -> list[dict]:
    """Return only items not seen in the last 7 days. Updates the hash store."""
    seen = _prune(_load())
    now_str = datetime.now(timezone.utc).isoformat()

    new_items = []
    for item in items:
        h = _hash(item.get("title", item.get("url", "")))
        if h not in seen:
            new_items.append(item)
            seen[h] = now_str

    _save(seen)
    log.info(f"Dedup: {len(items)} -> {len(new_items)} new items")
    return new_items
