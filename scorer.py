"""
Relevance scoring — ranks items 0-100 by source authority, keyword match, and recency.
"""

from datetime import datetime, timezone, timedelta

SCORE_KEYWORDS = [
    "gpt", "claude", "gemini", "llm", "model", "release", "agent",
    "reasoning", "multimodal", "benchmark", "alignment", "openai",
    "anthropic", "deepmind", "mistral", "llama", "fine-tun",
]

SOURCE_WEIGHTS = {
    "OpenAI": 30,
    "Hugging Face": 25,
    "Google AI": 25,
    "MIT Tech Review": 20,
    "TLDR AI": 18,
    "Ben's Bites": 18,
    "The Rundown AI": 18,
    "MarkTechPost": 15,
    "arXiv cs.AI": 12,
    "arXiv cs.CL": 12,
}


def _recency_bonus(pub_utc_str: str | None) -> int:
    if not pub_utc_str:
        return 0
    try:
        pub = datetime.fromisoformat(pub_utc_str)
        age = datetime.now(timezone.utc) - pub
        if age < timedelta(hours=6):
            return 20
        if age < timedelta(hours=12):
            return 10
        if age < timedelta(hours=24):
            return 5
    except Exception:
        pass
    return 0


def _keyword_score(title: str, summary: str, cap: int) -> int:
    text = (title + " " + summary).lower()
    hits = sum(1 for kw in SCORE_KEYWORDS if kw in text)
    return min(hits * 5, cap)


def score(item: dict) -> int:
    total = 0

    if item["type"] == "rss":
        total += SOURCE_WEIGHTS.get(item["source"], 10)
        total += _keyword_score(item["title"], item.get("summary", ""), cap=30)
        total += _recency_bonus(item.get("published_utc"))

    elif item["type"] == "tweet":
        total += 10  # base
        eng = item.get("engagement") or {}
        likes = eng.get("likes", 0)
        if likes > 1000:
            total += 45
        elif likes > 500:
            total += 35
        elif likes > 100:
            total += 20
        elif likes > 20:
            total += 10
        total += _keyword_score(item["title"], item.get("summary", ""), cap=20)
        total += _recency_bonus(item.get("published_utc"))

    return min(total, 100)


def rank(items: list[dict]) -> list[dict]:
    for item in items:
        item["score"] = score(item)
    return sorted(items, key=lambda x: x["score"], reverse=True)
