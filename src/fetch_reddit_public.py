# src/fetch_reddit_public.py
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import requests


def _get_json(url: str, user_agent: str) -> Optional[Dict[str, Any]]:
    headers = {"User-Agent": user_agent}
    r = requests.get(url, headers=headers, timeout=20)
    if r.status_code != 200:
        return None
    return r.json()


def fetch_reddit_public(
    subreddits: List[str],
    days: int = 7,
    per_sub_limit: int = 80,
    user_agent: str = "vacuum-voice-weekly/0.1 (public-json)",
    mode: str = "new",  # new | hot | top
) -> List[Dict[str, Any]]:
    """
    Fetch subreddit listing via public JSON:
      https://www.reddit.com/r/{sub}/new.json?limit=...
    No auth required.
    """
    cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
    out: List[Dict[str, Any]] = []

    mode = mode.lower().strip()
    if mode not in {"new", "hot", "top"}:
        mode = "new"

    for sr in subreddits:
        url = f"https://www.reddit.com/r/{sr}/{mode}.json?limit={per_sub_limit}"
        data = _get_json(url, user_agent=user_agent)
        if not data:
            continue

        children = data.get("data", {}).get("children", [])
        for ch in children:
            d = ch.get("data", {})
            created_utc = float(d.get("created_utc", 0))
            if created_utc < cutoff:
                continue

            permalink = d.get("permalink", "")
            out.append(
                {
                    "source": "reddit",
                    "subreddit": sr,
                    "id": d.get("id", ""),
                    "url": f"https://www.reddit.com{permalink}" if permalink else d.get("url", ""),
                    "title": d.get("title", "") or "",
                    "selftext": d.get("selftext", "") or "",
                    "score": int(d.get("score", 0) or 0),
                    "num_comments": int(d.get("num_comments", 0) or 0),
                    "created_utc": created_utc,
                    # MVP: listing endpoint不给评论；后面如需再抓 comments.json
                    "comments": [],
                }
            )

        # be polite to Reddit
        time.sleep(1.2)

    return out
