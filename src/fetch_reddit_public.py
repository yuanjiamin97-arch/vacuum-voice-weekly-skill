from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests


def _get_json(url: str, user_agent: str) -> Optional[Dict[str, Any]]:
    headers = {"User-Agent": user_agent}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        return None
    return response.json()


def _fetch_comments(post_id: str, user_agent: str, limit: int) -> List[Dict[str, Any]]:
    if not post_id or limit <= 0:
        return []

    url = f"https://www.reddit.com/comments/{post_id}.json?limit={limit}&sort=top"
    payload = _get_json(url, user_agent=user_agent)
    if not isinstance(payload, list) or len(payload) < 2:
        return []

    children = payload[1].get("data", {}).get("children", [])
    comments: List[Dict[str, Any]] = []
    for child in children:
        data = child.get("data", {})
        body = (data.get("body") or "").strip()
        if not body:
            continue
        comments.append(
            {
                "body": body,
                "score": int(data.get("score", 0) or 0),
                "author": data.get("author", ""),
            }
        )
        if len(comments) >= limit:
            break
    return comments


def fetch_reddit_public(
    subreddits: List[str],
    days: int = 7,
    per_sub_limit: int = 80,
    per_post_comment_limit: int = 20,
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

            post_id = d.get("id", "")
            permalink = d.get("permalink", "")
            comments = []
            if int(d.get("num_comments", 0) or 0) > 0:
                comments = _fetch_comments(post_id, user_agent, per_post_comment_limit)
            out.append(
                {
                    "source": "reddit",
                    "subreddit": sr,
                    "id": post_id,
                    "url": f"https://www.reddit.com{permalink}" if permalink else d.get("url", ""),
                    "title": d.get("title", "") or "",
                    "selftext": d.get("selftext", "") or "",
                    "score": int(d.get("score", 0) or 0),
                    "num_comments": int(d.get("num_comments", 0) or 0),
                    "created_utc": created_utc,
                    "comments": comments,
                }
            )

        time.sleep(0.4)

    return out
