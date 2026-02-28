from typing import List, Dict, Any
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound


def fetch_transcript(video_id: str) -> str:
    try:
        t = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([x["text"] for x in t])
    except (TranscriptsDisabled, NoTranscriptFound):
        return ""


def fetch_youtube(videos: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    MVP: user provides video list: [{"video_id": "...", "channel": "...", "title": "...", "url": "..."}]
    Later: auto-discover via YouTube API.
    """
    out = []
    for v in videos:
        transcript = fetch_transcript(v["video_id"])
        out.append(
            {
                "source": "youtube",
                "channel": v.get("channel", ""),
                "video_id": v["video_id"],
                "title": v.get("title", ""),
                "url": v.get("url", f"https://www.youtube.com/watch?v={v['video_id']}"),
                "transcript": transcript,
            }
        )
    return out
