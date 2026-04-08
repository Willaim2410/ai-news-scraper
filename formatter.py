"""
Formats ranked items into a Markdown digest and JSON data file.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


def _engagement_str(item: dict) -> str:
    eng = item.get("engagement")
    if not eng:
        return ""
    parts = []
    if eng.get("likes"):
        parts.append(f"{eng['likes']:,} likes")
    if eng.get("retweets"):
        parts.append(f"{eng['retweets']:,} RTs")
    return " | ".join(parts)


def to_markdown(items: list[dict], date_str: str) -> str:
    rss_items = [i for i in items if i["type"] == "rss"]
    tweet_items = [i for i in items if i["type"] == "tweet"]
    total = len(items)

    lines = [
        f"# AI News Digest — {date_str}",
        f"*Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} | "
        f"{total} items | RSS({len(rss_items)}) Twitter({len(tweet_items)})*",
        "",
        "---",
        "",
    ]

    # Top 10 stories across all sources
    top = items[:10]
    if top:
        lines.append("## Top Stories")
        lines.append("")
        for i, item in enumerate(top, 1):
            eng = _engagement_str(item)
            pub = (item.get("published_utc") or "")[:16].replace("T", " ")
            lines.append(f"### {i}. [{item['title']}]({item['url']})")
            lines.append(f"**{item['source']}** | {pub} UTC | Score: {item['score']}")
            if item.get("summary") and item["type"] == "rss":
                summary = item["summary"][:280]
                lines.append(f"> {summary}{'...' if len(item['summary']) > 280 else ''}")
            elif item["type"] == "tweet":
                lines.append(f"> {item.get('summary', '')[:280]}")
                if eng:
                    lines.append(f"*{eng}*")
            lines.append("")

    # Twitter section
    if tweet_items[10:] if len(tweet_items) > 0 else False:
        twitter_rest = [t for t in tweet_items if t not in top]
        if twitter_rest:
            lines.append("---")
            lines.append("## More from Twitter")
            lines.append("")
            for item in twitter_rest[:10]:
                eng = _engagement_str(item)
                lines.append(
                    f"- **{item['source']}**: {item['title'][:140]} "
                    f"[→]({item['url']})"
                    + (f" _{eng}_" if eng else "")
                )
            lines.append("")

    # RSS remainder
    rss_rest = [r for r in rss_items if r not in top]
    if rss_rest:
        lines.append("---")
        lines.append("## More News")
        lines.append("")
        for item in rss_rest[:20]:
            pub = (item.get("published_utc") or "")[:10]
            lines.append(
                f"- **[{item['title']}]({item['url']})** "
                f"— {item['source']}" + (f" ({pub})" if pub else "")
            )
        lines.append("")

    lines.append("---")
    lines.append("*Twitter data may be absent if X is rate-limiting. RSS sources are always active.*")

    return "\n".join(lines)


def to_json(items: list[dict]) -> str:
    return json.dumps(items, indent=2, ensure_ascii=False)


def write(items: list[dict], output_dir: Path, date_str: str):
    output_dir.mkdir(parents=True, exist_ok=True)

    md = to_markdown(items, date_str)
    js = to_json(items)

    md_path = output_dir / f"ai_news_{date_str}.md"
    json_path = output_dir / f"ai_news_{date_str}.json"
    latest_path = output_dir / "latest.md"

    md_path.write_text(md, encoding="utf-8")
    json_path.write_text(js, encoding="utf-8")
    latest_path.write_text(md, encoding="utf-8")

    return md_path, json_path
