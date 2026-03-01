from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests


def _get_json(url: str, user_agent: str) -> Optional[Dict[str, Any]]:
    headers = {"User-Agent": user_agent}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        return None
    return response.json()


def _request_json(url: str, user_agent: str) -> tuple[Optional[Dict[str, Any]], str]:
    headers = {"User-Agent": user_agent}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.HTTPError as exc:
        status_code = getattr(exc.response, "status_code", None)
        if status_code == 429:
            return None, "rate_limited"
        if status_code == 403:
            return None, "forbidden"
        if status_code:
            return None, f"http_{status_code}"
        return None, "http_error"
    except requests.RequestException:
        return None, "request_failed"
    return response.json(), "ok"


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


def _listing_to_post(data: Dict[str, Any], subreddit: str, comments: List[Dict[str, Any]]) -> Dict[str, Any]:
    post_id = data.get("id", "")
    permalink = data.get("permalink", "")
    return {
        "source": "reddit",
        "subreddit": subreddit,
        "id": post_id,
        "url": f"https://www.reddit.com{permalink}" if permalink else data.get("url", ""),
        "title": data.get("title", "") or "",
        "selftext": data.get("selftext", "") or "",
        "score": int(data.get("score", 0) or 0),
        "num_comments": int(data.get("num_comments", 0) or 0),
        "created_utc": float(data.get("created_utc", 0) or 0),
        "comments": comments,
    }


def fetch_reddit_public(
    subreddits: List[str],
    days: int = 7,
    per_sub_limit: int = 80,
    per_post_comment_limit: int = 20,
    user_agent: str = "vacuum-voice-weekly/0.1 (public-json)",
    mode: str = "new",  # new | hot | top
    diagnostics: Optional[List[Dict[str, Any]]] = None,
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
        data, status = _request_json(url, user_agent=user_agent)
        if diagnostics is not None:
            diagnostics.append(
                {
                    "source": "reddit_listing",
                    "target": sr,
                    "status": status,
                    "results": 0,
                }
            )
        if not data:
            continue

        children = data.get("data", {}).get("children", [])
        if diagnostics is not None:
            diagnostics[-1]["results"] = len(children)
        for ch in children:
            d = ch.get("data", {})
            created_utc = float(d.get("created_utc", 0))
            if created_utc < cutoff:
                continue

            post_id = d.get("id", "")
            comments = []
            if int(d.get("num_comments", 0) or 0) > 0:
                comments = _fetch_comments(post_id, user_agent, per_post_comment_limit)
            out.append(_listing_to_post(d, sr, comments))

        time.sleep(0.4)

    return out


def fetch_reddit_global_search(
    queries: List[str],
    days: int = 7,
    per_query_limit: int = 12,
    per_post_comment_limit: int = 10,
    user_agent: str = "vacuum-voice-weekly/0.1 (global-search)",
    diagnostics: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
    out: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()

    for query in queries:
        if not query.strip():
            continue

        params = urlencode(
            {
                "q": query,
                "sort": "new",
                "limit": per_query_limit,
                "t": "month" if days >= 30 else "week",
            }
        )
        url = f"https://www.reddit.com/search.json?{params}"
        payload, status = _request_json(url, user_agent=user_agent)
        if diagnostics is not None:
            diagnostics.append(
                {
                    "source": "reddit_search",
                    "target": query,
                    "status": status,
                    "results": 0,
                }
            )
        if not payload:
            continue

        children = payload.get("data", {}).get("children", [])
        if diagnostics is not None:
            diagnostics[-1]["results"] = len(children)
        for child in children:
            data = child.get("data", {})
            post_id = data.get("id", "")
            if not post_id or post_id in seen_ids:
                continue

            created_utc = float(data.get("created_utc", 0) or 0)
            if created_utc < cutoff:
                continue

            comments = []
            if int(data.get("num_comments", 0) or 0) > 0:
                comments = _fetch_comments(post_id, user_agent, per_post_comment_limit)

            out.append(_listing_to_post(data, data.get("subreddit", ""), comments))
            seen_ids.add(post_id)

        time.sleep(0.4)

    return out
