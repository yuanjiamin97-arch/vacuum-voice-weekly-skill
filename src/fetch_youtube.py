from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import requests
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_published_at(value: str) -> datetime | None:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _fetch_transcript(video_id: str) -> str:
    if not video_id:
        return ""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join(item.get("text", "") for item in transcript).strip()
    except AttributeError:
        try:
            transcript = YouTubeTranscriptApi().fetch(video_id)
            return " ".join(getattr(item, "text", "") for item in transcript).strip()
        except Exception:
            return ""
    except Exception:
        return ""


def _fetch_comments(video_id: str, max_comments: int = 30) -> List[Dict[str, Any]]:
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key or not video_id:
        return []

    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": min(max_comments, 100),
        "order": "relevance",
        "textFormat": "plainText",
        "key": api_key,
    }
    try:
        response = requests.get(
            "https://www.googleapis.com/youtube/v3/commentThreads",
            params=params,
            timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException:
        return []

    comments: List[Dict[str, Any]] = []
    for item in response.json().get("items", []):
        snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
        text = (snippet.get("textDisplay") or "").strip()
        if not text:
            continue
        comments.append(
            {
                "body": text,
                "author": snippet.get("authorDisplayName", ""),
                "score": int(snippet.get("likeCount", 0) or 0),
            }
        )
    return comments


def _normalize_video(entry: Dict[str, Any]) -> Dict[str, Any]:
    video_id = entry.get("id") or entry.get("video_id") or ""
    url = entry.get("webpage_url") or entry.get("url") or ""
    if url and not str(url).startswith("http"):
        url = f"https://www.youtube.com/watch?v={video_id}"
    if not url and video_id:
        url = f"https://www.youtube.com/watch?v={video_id}"
    return {
        "video_id": video_id,
        "channel": entry.get("channel") or entry.get("uploader") or entry.get("channel_name") or "",
        "title": entry.get("title") or "",
        "description": entry.get("description") or "",
        "url": url,
        "published_at": entry.get("upload_date") or entry.get("published_at") or "",
    }


def _discover_recent_videos(channels: List[str], days: int, max_videos_per_channel: int) -> List[Dict[str, Any]]:
    if not channels:
        return []

    cutoff = _utc_now() - timedelta(days=days)
    out: List[Dict[str, Any]] = []
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "ignoreerrors": True,
        "no_warnings": True,
        "socket_timeout": 8,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for channel_name in channels:
            query = f"ytsearchdate{max_videos_per_channel * 2}:{channel_name}"
            try:
                info = ydl.extract_info(query, download=False) or {}
            except Exception:
                continue

            entries = info.get("entries") or []
            matches: List[Dict[str, Any]] = []
            channel_lower = channel_name.lower()
            for entry in entries:
                if not entry:
                    continue
                uploader = str(entry.get("uploader") or entry.get("channel") or "").lower()
                title = str(entry.get("title") or "").lower()
                if channel_lower in uploader or channel_lower in title:
                    matches.append(_normalize_video(entry))
                if len(matches) >= max_videos_per_channel:
                    break

            if not matches:
                matches = [_normalize_video(entry) for entry in entries[:max_videos_per_channel] if entry]

            for video in matches:
                published = _parse_published_at(video.get("published_at", ""))
                if published and published < cutoff:
                    continue
                out.append(video)

    return out


def _search_global_videos(queries: List[str], max_videos_total: int) -> List[Dict[str, Any]]:
    if not queries or max_videos_total <= 0:
        return []

    out: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "ignoreerrors": True,
        "no_warnings": True,
        "socket_timeout": 8,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for query in queries:
            if not query.strip():
                continue
            try:
                info = ydl.extract_info(f"ytsearchdate{max_videos_total}:{query}", download=False) or {}
            except Exception:
                continue

            for entry in info.get("entries") or []:
                if not entry:
                    continue
                normalized = _normalize_video(entry)
                video_id = normalized["video_id"]
                if not video_id or video_id in seen_ids:
                    continue
                out.append(normalized)
                seen_ids.add(video_id)
                if len(out) >= max_videos_total:
                    return out

    return out


def fetch_youtube(
    videos: List[Dict[str, Any]] | None = None,
    channels: List[str] | None = None,
    search_queries: List[str] | None = None,
    days: int = 7,
    max_videos_per_channel: int = 2,
    max_videos_total: int = 5,
    include_comments: bool = True,
    diagnostics: List[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    seeds: List[Dict[str, Any]] = []

    if search_queries:
        seeds = _search_global_videos(search_queries, max_videos_total)
        if diagnostics is not None:
            diagnostics.append(
                {
                    "source": "youtube_search",
                    "target": "global_search",
                    "status": "ok" if seeds else "no_results",
                    "results": len(seeds),
                }
            )

    if not seeds and videos:
        seeds = list(videos)
        if diagnostics is not None:
            diagnostics.append(
                {
                    "source": "youtube_seed",
                    "target": "configured_videos",
                    "status": "ok" if seeds else "empty",
                    "results": len(seeds),
                }
            )

    if not seeds:
        seeds = _discover_recent_videos(channels or [], days, max_videos_per_channel)
        if diagnostics is not None:
            diagnostics.append(
                {
                    "source": "youtube_listing",
                    "target": "channel_fallback",
                    "status": "ok" if seeds else "no_results",
                    "results": len(seeds),
                }
            )

    out: List[Dict[str, Any]] = []
    for video in seeds:
        normalized = _normalize_video(video)
        if not normalized["video_id"]:
            continue
        transcript = _fetch_transcript(normalized["video_id"])
        comments = _fetch_comments(normalized["video_id"]) if include_comments else []
        out.append(
            {
                "source": "youtube",
                "channel": normalized["channel"],
                "video_id": normalized["video_id"],
                "title": normalized["title"],
                "url": normalized["url"],
                "description": normalized["description"],
                "published_at": normalized["published_at"],
                "transcript": transcript,
                "comments": comments,
            }
        )

    if diagnostics is not None:
        diagnostics.append(
            {
                "source": "youtube_final",
                "target": "analyzed_items",
                "status": "ok",
                "results": len(out),
            }
        )
    return out
