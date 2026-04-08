"""
AI News Scraper — main orchestrator.

Layers:
  1. RSS (always runs — 10 AI sources, zero credentials needed)
  2. Twitter/X via Twikit (supplemental — skipped gracefully if unconfigured or broken)

Run:
  python scraper.py

First-time Twitter setup:
  python setup.py
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import rss_scraper
import twitter_scraper
import deduplicator
import scorer
import formatter

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
LOG_PATH = BASE_DIR / "output" / "scraper.log"
CREDS_PATH = BASE_DIR / "data" / "twitter_creds.json"


def setup_logging():
    LOG_PATH.parent.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)),
        ],
    )


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_twitter_creds() -> dict:
    """Load Twitter credentials from data/twitter_creds.json or environment."""
    # Env vars take priority
    if os.environ.get("TWITTER_USERNAME"):
        return {
            "username": os.environ["TWITTER_USERNAME"],
            "email": os.environ.get("TWITTER_EMAIL", ""),
            "password": os.environ["TWITTER_PASSWORD"],
        }
    if CREDS_PATH.exists():
        with open(CREDS_PATH) as f:
            return json.load(f)
    return {}


async def send_telegram(digest_md: str, token: str, chat_id: str):
    """Send top portion of digest to Telegram (4000 char limit)."""
    import urllib.request

    text = digest_md[:4000]
    data = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=15)
        logging.getLogger(__name__).info("Telegram: digest sent")
    except Exception as e:
        logging.getLogger(__name__).warning(f"Telegram: failed to send — {e}")


async def main():
    setup_logging()
    log = logging.getLogger(__name__)
    log.info("=== AI News Scraper starting ===")

    config = load_config()
    all_items = []

    # ── Layer 1: RSS (always runs) ──────────────────────────────────────────
    log.info("Fetching RSS feeds...")
    rss_items = rss_scraper.fetch_all(
        config["rss_feeds"],
        lookback_hours=config.get("lookback_hours", 25),
    )
    all_items.extend(rss_items)
    log.info(f"RSS total: {len(rss_items)} items")

    # ── Layer 2: Twitter (non-fatal) ────────────────────────────────────────
    creds = load_twitter_creds()
    cookies_exist = (BASE_DIR / "data" / "twitter_cookies.json").exists()

    if creds or cookies_exist:
        log.info("Fetching Twitter/X...")
        try:
            tw_items = await twitter_scraper.fetch_tweets(
                queries=config["twitter_queries"],
                credentials=creds,
                lookback_hours=config.get("lookback_hours", 25),
            )
            all_items.extend(tw_items)
            log.info(f"Twitter total: {len(tw_items)} items")
        except Exception as e:
            log.warning(f"Twitter scraping failed (continuing RSS-only): {e}")
    else:
        log.info("Twitter: no credentials found — RSS-only mode. Run setup.py to add Twitter.")

    # ── Deduplicate ─────────────────────────────────────────────────────────
    new_items = deduplicator.filter_new(all_items)
    if not new_items:
        log.info("No new items since last run. Done.")
        return

    # ── Score and rank ───────────────────────────────────────────────────────
    ranked = scorer.rank(new_items)
    log.info(f"Ranked {len(ranked)} items. Top score: {ranked[0]['score'] if ranked else 0}")

    # ── Write output ─────────────────────────────────────────────────────────
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_dir = BASE_DIR / config.get("output_dir", "output")
    md_path, json_path = formatter.write(ranked, output_dir, date_str)
    log.info(f"Saved: {md_path.name}")
    log.info(f"Saved: {json_path.name}")

    # ── Write web dashboard data ──────────────────────────────────────────────
    web_data_dir = BASE_DIR / "docs" / "data"
    web_data_dir.mkdir(parents=True, exist_ok=True)
    web_json = web_data_dir / "latest.json"
    web_json.write_text(formatter.to_json(ranked), encoding="utf-8")
    log.info(f"Saved: docs/data/latest.json (dashboard data)")

    # ── Telegram ─────────────────────────────────────────────────────────────
    if config.get("telegram_enabled"):
        token = os.environ.get(config.get("telegram_bot_token_env", "TELEGRAM_BOT_TOKEN"), "")
        chat_id = config.get("telegram_chat_id", "")
        if token and chat_id:
            digest_md = md_path.read_text(encoding="utf-8")
            await send_telegram(digest_md, token, chat_id)
        else:
            log.warning("Telegram enabled but token/chat_id missing.")

    log.info(f"=== Done. {len(ranked)} items written to {md_path} ===")


if __name__ == "__main__":
    asyncio.run(main())
