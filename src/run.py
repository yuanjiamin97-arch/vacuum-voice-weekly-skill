import json
from pathlib import Path

from dotenv import load_dotenv

from src.analyze import analyze_corpus
from src.fetch_reddit_public import fetch_reddit_public
from src.fetch_youtube import fetch_youtube
from src.render import render_weekly_report

ROOT = Path(__file__).resolve().parents[1]


def _days_from_config(config: dict) -> int:
    preset = str(config.get("date_range", {}).get("preset", "")).lower()
    if preset.startswith("last_") and preset.endswith("_days"):
        middle = preset.removeprefix("last_").removesuffix("_days")
        if middle.isdigit():
            return max(1, int(middle))
    return 7


def main():
    load_dotenv(ROOT / ".env")

    config = json.loads((ROOT / "input.example.json").read_text(encoding="utf-8"))
    template_md = (ROOT / "weekly_report.template.md").read_text(encoding="utf-8")
    days = _days_from_config(config)
    items = []

    if "reddit" in config.get("sources", []):
        items.extend(
            fetch_reddit_public(
                subreddits=config.get("reddit", {}).get("subreddits", []),
                days=days,
                per_sub_limit=15,
                per_post_comment_limit=10,
                user_agent="vacuum-voice-weekly/0.2 (public-json)",
                mode="new",
            )
        )

    if "youtube" in config.get("sources", []):
        youtube_config = config.get("youtube", {})
        items.extend(
            fetch_youtube(
                videos=youtube_config.get("videos", []),
                channels=youtube_config.get("channels", []),
                days=days,
                max_videos_per_channel=int(youtube_config.get("max_videos_per_channel", 1)),
                include_comments="comments" in youtube_config.get("include", []),
            )
        )

    analysis = analyze_corpus(items)
    report = render_weekly_report(template_md, config, analysis)

    out_dir = ROOT / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "weekly_report.md").write_text(report, encoding="utf-8")

    metrics = {
        "time_window": config.get("date_range", {}).get("preset", "custom"),
        "sources": config.get("sources", []),
        "coverage": {
            "reddit_posts_count": sum(1 for item in items if item.get("source") == "reddit"),
            "youtube_videos_count": sum(1 for item in items if item.get("source") == "youtube"),
            "comments_count": sum(len(item.get("comments", [])) for item in items),
            "brands_count": len(config.get("product_filter", {}).get("selected_brands", [])),
        },
    }
    (out_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Done. Output in outputs/weekly_report.md")


if __name__ == "__main__":
    main()
