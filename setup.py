"""
First-time setup — logs into Twitter/X and saves session cookies.
Run this once. After that, scraper.py reuses the cookies automatically.

Usage:
    python setup.py
"""

import asyncio
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
CREDS_PATH = BASE_DIR / "data" / "twitter_creds.json"
COOKIES_PATH = BASE_DIR / "data" / "twitter_cookies.json"


async def main():
    try:
        from twikit import Client
    except ImportError:
        print("ERROR: twikit not installed. Run: pip install twikit")
        sys.exit(1)

    print("=== Twitter/X Setup ===")
    print("A FREE Twitter account is enough. Use a dedicated account, not your personal one.")
    print()

    username = input("Twitter username (without @): ").strip()
    email = input("Twitter email: ").strip()
    password = input("Twitter password: ").strip()

    if not (username and email and password):
        print("All fields required.")
        sys.exit(1)

    print("\nLogging in...")
    client = Client("en-US")
    try:
        await client.login(
            auth_info_1=username,
            auth_info_2=email,
            password=password,
        )
    except Exception as e:
        print(f"Login failed: {e}")
        print("Check your credentials and try again.")
        sys.exit(1)

    COOKIES_PATH.parent.mkdir(exist_ok=True)
    client.save_cookies(str(COOKIES_PATH))
    print(f"Session cookies saved to: {COOKIES_PATH}")

    # Save credentials for re-login if cookies expire
    with open(CREDS_PATH, "w") as f:
        json.dump({"username": username, "email": email, "password": password}, f)
    print(f"Credentials saved to: {CREDS_PATH}")

    print("\nSetup complete. Run: python scraper.py")


if __name__ == "__main__":
    asyncio.run(main())
