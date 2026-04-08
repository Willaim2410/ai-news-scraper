"""
RSS scraper — reliable foundation layer.
Pulls from official AI lab blogs, newsletters, and arXiv.
No credentials required. Zero fragility.
"""

import calendar
import logging
import time
from datetime import datetime, timezone, timedelta

import feedparser

log = logging.getLogger(__name__)

ARXIV_KEYWORDS = [
    "language model", "llm", "gpt", "chatgpt", "transformer",
    "instruction tuning", "rlhf", "alignment", "reasoning",
    "multimodal", "vision-language", "diffusion", "foundation model",
    "agent", "tool use", "retrieval augmented", "rag", "fine-tun",
]


def _parse_date(entry) -> datetime | None:
    """Return a UTC-aware datetime from feedparser's parsed date fields."""
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if t is None:
        return None
    try:
        return datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc)
    except Exception:
        return None


def _is_arxiv_relevant(title: str, summary: str) -> bool:
    text = (title + " " + summary).lower()
    return any(kw in text for kw in ARXIV_KEYWORDS)


def fetch_feed(feed_cfg: dict, lookback_hours: int) -> list[dict]:
    name = feed_cfg["name"]
    url = feed_cfg["url"]
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    try:
        parsed = feedparser.parse(url, agent="Mozilla/5.0 AI-News-Scraper/1.0")
    except Exception as e:
        log.warning(f"RSS fetch failed [{name}]: {e}")
        return []

    if parsed.bozo and not parsed.entries:
        log.warning(f"RSS malformed [{name}]: {parsed.bozo_exception}")
        return []

    is_arxiv = "arxiv" in url.lower()
    items = []
    arxiv_count = 0

    for entry in parsed.entries:
        pub = _parse_date(entry)
        if pub and pub < cutoff:
            continue

        title = entry.get("title", "").strip()
        link = entry.get("link", "")
        summary = entry.get("summary", entry.get("description", ""))[:500].strip()

        if not title or not link:
            continue

        if is_arxiv:
            if not _is_arxiv_relevant(title, summary):
                continue
            if arxiv_count >= 5:  # cap arXiv to avoid flooding the digest
                continue
            arxiv_count += 1

        items.append({
            "id": link,
            "title": title,
            "url": link,
            "source": name,
            "type": "rss",
            "published_utc": pub.isoformat() if pub else None,
            "summary": summary,
            "engagement": None,
        })

    log.info(f"  RSS [{name}]: {len(items)} items")
    return items


def fetch_all(feeds: list[dict], lookback_hours: int) -> list[dict]:
    all_items = []
    for feed in feeds:
        all_items.extend(fetch_feed(feed, lookback_hours))
    return all_items
