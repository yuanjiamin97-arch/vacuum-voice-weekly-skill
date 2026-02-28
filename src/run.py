
import json
import os
from pathlib import Path
from dotenv import load_dotenv

from fetch_reddit_public import fetch_reddit_public
from fetch_youtube import fetch_youtube
from analyze import analyze_corpus
from render import render_weekly_report

ROOT = Path(__file__).resolve().parents[1]

def main():
    load_dotenv(ROOT / ".env")

    config = json.loads((ROOT / "input.example.json").read_text(encoding="utf-8"))
    template_md = (ROOT / "weekly_report.template.md").read_text(encoding="utf-8")

    items = []

    # Reddit (public JSON, no auth)
if "reddit" in config["sources"]:
    reddit_items = fetch_reddit_public(
        subreddits=config["reddit"]["subreddits"],
        days=7,
        per_sub_limit=80,
        user_agent="vacuum-voice-weekly/0.1 (public-json)",
        mode="new",
    )
    items.extend(reddit_items)

    # YouTube MVP: you provide a small list of video ids in config["youtube"]["videos"]
    if "youtube" in config["sources"]:
        videos = config["youtube"].get("videos", [])
        yt_items = fetch_youtube(videos)
        items.extend(yt_items)

    analysis = analyze_corpus(items)
    report = render_weekly_report(template_md, config, analysis)

    out_dir = ROOT / "outputs"
    out_dir.mkdir(exist_ok=True)

    (out_dir / "weekly_report.md").write_text(report, encoding="utf-8")

    # minimal metrics
    metrics = {
        "time_window": config["date_range"].get("preset", "custom"),
        "sources": config["sources"],
        "coverage": {
            "reddit_posts_count": sum(1 for x in items if x["source"] == "reddit"),
            "youtube_videos_count": sum(1 for x in items if x["source"] == "youtube"),
            "brands_count": len(config["product_filter"]["selected_brands"]),
        },
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    print("✅ Done. Output in outputs/weekly_report.md")

if __name__ == "__main__":
    main()
