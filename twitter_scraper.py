"""
Twitter/X scraper — supplemental layer via Twikit.
Uses session cookies so login only happens once.
Failure here is NON-FATAL — RSS layer continues without it.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

log = logging.getLogger(__name__)

COOKIES_FILE = Path(__file__).parent / "data" / "twitter_cookies.json"


async def _get_client(username: str, email: str, password: str):
    from twikit import Client

    client = Client("en-US")

    if COOKIES_FILE.exists():
        try:
            client.load_cookies(str(COOKIES_FILE))
            log.info("Twitter: loaded session cookies")
            return client
        except Exception as e:
            log.warning(f"Twitter: failed to load cookies ({e}), re-logging in")

    if not (username and password):
        raise RuntimeError("No Twitter credentials configured. Run setup.py first.")

    await client.login(
        auth_info_1=username,
        auth_info_2=email,
        password=password,
    )
    COOKIES_FILE.parent.mkdir(exist_ok=True)
    client.save_cookies(str(COOKIES_FILE))
    log.info("Twitter: logged in and saved cookies")
    return client


def _tweet_to_dict(tweet, lookback_hours: int) -> dict | None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    try:
        created = tweet.created_at
        if isinstance(created, str):
            created = datetime.strptime(created, "%a %b %d %H:%M:%S +0000 %Y")
            created = created.replace(tzinfo=timezone.utc)
        if created < cutoff:
            return None
    except Exception:
        pass

    return {
        "id": str(tweet.id),
        "title": tweet.full_text[:120],
        "url": f"https://x.com/{tweet.user.screen_name}/status/{tweet.id}",
        "source": f"@{tweet.user.screen_name}",
        "type": "tweet",
        "published_utc": created.isoformat() if created else None,
        "summary": tweet.full_text,
        "engagement": {
            "likes": tweet.favorite_count or 0,
            "retweets": tweet.retweet_count or 0,
            "replies": getattr(tweet, "reply_count", 0) or 0,
        },
    }


async def fetch_tweets(
    queries: list[str],
    credentials: dict,
    lookback_hours: int,
) -> list[dict]:
    username = credentials.get("username", "")
    email = credentials.get("email", "")
    password = credentials.get("password", "")

    client = await _get_client(username, email, password)

    results = []
    for query in queries:
        try:
            tweets = await client.search_tweet(query, "Latest")
            count = 0
            for tweet in tweets:
                item = _tweet_to_dict(tweet, lookback_hours)
                if item:
                    results.append(item)
                    count += 1
                if count >= 20:
                    break
            log.info(f"  Twitter [{query[:40]}...]: {count} tweets")
            await asyncio.sleep(2)  # be gentle — 50 req/15min limit
        except Exception as e:
            log.warning(f"  Twitter query failed [{query[:40]}]: {e}")
            continue

    return results
