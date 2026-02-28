import os
from datetime import datetime, timezone
from typing import List, Dict, Any
import praw


def fetch_reddit(subreddits: List[str], keywords: List[str], days: int, limit: int = 200) -> List[Dict[str, Any]]:
    """Fetch recent posts+comments from subreddits matching keywords."""
    reddit = praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent=os.environ["REDDIT_USER_AGENT"],
    )

    # naive time filter: keep only recent by created_utc
    cutoff = datetime.now(timezone.utc).timestamp() - days * 86400

    out: List[Dict[str, Any]] = []
    query = " OR ".join([f'"{k}"' for k in keywords]) if keywords else ""

    for sr in subreddits:
        subreddit = reddit.subreddit(sr)
        # Use subreddit search for relevance
        for post in subreddit.search(query, sort="new", limit=limit):
            if post.created_utc < cutoff:
                continue

            post.comments.replace_more(limit=0)
            comments = []
            for c in post.comments.list()[:200]:
                comments.append({"body": getattr(c, "body", ""), "score": getattr(c, "score", 0)})

            out.append(
                {
                    "source": "reddit",
                    "subreddit": sr,
                    "id": post.id,
                    "url": f"https://www.reddit.com{post.permalink}",
                    "title": post.title,
                    "selftext": post.selftext or "",
                    "score": post.score,
                    "num_comments": post.num_comments,
                    "created_utc": post.created_utc,
                    "comments": comments,
                }
            )

    return out
