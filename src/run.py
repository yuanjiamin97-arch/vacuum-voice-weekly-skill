import json
import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv

from src.analyze import analyze_corpus
from src.fetch_reddit_public import fetch_reddit_global_search, fetch_reddit_public
from src.fetch_youtube import fetch_youtube
from src.render import render_weekly_report

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUBREDDITS = ["RobotVacuums", "VacuumCleaners", "Roborock", "homeautomation"]
DEFAULT_YOUTUBE_CHANNELS = ["Vacuum Wars", "Smart Home Solver", "The Hook Up"]
DEFAULT_KEYWORDS = [
    "robot vacuum",
    "robotic vacuum",
    "mopping",
    "carpet",
    "pet hair",
    "obstacle avoidance",
]
MIN_ANALYZED_ITEMS = {
    "weekly_monitoring": 8,
    "ad_hoc_research": 12,
}


def _build_search_queries(config: dict) -> List[str]:
    targets = config.get("product_filter", {})
    brands = list(targets.get("selected_brands", []))
    models = list(targets.get("selected_models", []))
    keywords = list(config.get("reddit", {}).get("query_keywords", []))
    focus_terms = list(config.get("focus", []))
    mode = str(config.get("mode", "weekly_monitoring"))
    queries: List[str] = []

    for model in models:
        queries.append(f"\"{model}\"")
        for brand in brands:
            queries.append(f"\"{brand}\" \"{model}\"")

    for brand in brands:
        queries.append(f"\"{brand}\"")
        queries.append(f"\"{brand}\" robot vacuum")

    if len(brands) > 1:
        lead_brand = brands[0]
        for competitor in brands[1:3]:
            queries.append(f"\"{lead_brand}\" \"{competitor}\"")

    if mode == "weekly_monitoring":
        queries.extend(keywords[:2])
        queries.extend(focus_terms[:1])
        max_queries = 10
    else:
        queries.extend(keywords[:4])
        queries.extend(focus_terms[:3])
        max_queries = 16

    seen: set[str] = set()
    out: List[str] = []
    for query in queries:
        clean = query.strip()
        if clean and clean not in seen:
            out.append(clean)
            seen.add(clean)
        if len(out) >= max_queries:
            break
    return out


def _days_from_window(window: dict) -> int:
    preset = str(window.get("preset", "")).lower()
    if preset.startswith("last_") and preset.endswith("_days"):
        middle = preset.removeprefix("last_").removesuffix("_days")
        if middle.isdigit():
            return max(1, int(middle))
    return 7


def _should_retry_with_deeper_fetch(config: dict, items: list[dict], reddit_diagnostics: list[dict]) -> bool:
    mode = str(config.get("mode", "weekly_monitoring"))
    threshold = MIN_ANALYZED_ITEMS.get(mode, 8)
    analyzed_count = len(items)
    any_reddit_ok = any(
        entry.get("status") == "ok" and entry.get("results", 0) > 0
        for entry in reddit_diagnostics
        if entry.get("source") in {"reddit_search", "reddit_listing"}
    )
    return analyzed_count < threshold or not any_reddit_ok


def _deepened_reddit_config(reddit_config: dict) -> dict:
    return {
        **reddit_config,
        "per_query_limit": max(int(reddit_config.get("per_query_limit", 6)), 20),
        "per_sub_limit": max(int(reddit_config.get("per_sub_limit", 6)), 16),
        "per_post_comment_limit": max(int(reddit_config.get("per_post_comment_limit", 6)), 12),
    }


def _deepened_youtube_config(youtube_config: dict) -> dict:
    return {
        **youtube_config,
        "max_videos_per_channel": max(int(youtube_config.get("max_videos_per_channel", 2)), 4),
        "max_videos_total": max(int(youtube_config.get("max_videos_total", 5)), 12),
    }


def _pick_config_path() -> Path:
    requested = os.environ.get("VACUUM_VOICE_CONFIG", "").strip()
    if requested:
        candidate = Path(requested)
        if not candidate.is_absolute():
            candidate = ROOT / candidate
        return candidate

    for name in ("input.weekly.json", "input.example.json"):
        candidate = ROOT / name
        if candidate.exists():
            return candidate
    return ROOT / "input.weekly.json"


def _normalize_config(raw_config: dict) -> dict:
    if "targets" not in raw_config and "scope" not in raw_config:
        return raw_config

    mode = raw_config.get("mode", "weekly_monitoring")
    targets = raw_config.get("targets", {})
    scope = raw_config.get("scope", {})
    product_filter = raw_config.get("product_filter", {})

    selected_brands = list(targets.get("brands", []))
    if not selected_brands:
        selected_brands = list(product_filter.get("selected_brands", []))

    if scope.get("include_competitors", False):
        for brand in scope.get("competitor_brands", []):
            if brand not in selected_brands:
                selected_brands.append(brand)

    selected_models = list(targets.get("models", []))
    if not selected_models:
        selected_models = list(product_filter.get("selected_models", []))

    filter_mode = "model" if selected_models else "brand"

    window = raw_config.get("time_window", raw_config.get("date_range", {"preset": "last_7_days"}))
    output = raw_config.get("output", {"language": "bilingual", "format": "markdown"})

    reddit_raw = raw_config.get("reddit", {})
    youtube_raw = raw_config.get("youtube", {})
    sources = list(raw_config.get("sources", ["reddit", "youtube"]))

    return {
        "mode": mode,
        "date_range": window,
        "sources": sources,
        "product_filter": {
            "mode": filter_mode,
            "selected_brands": selected_brands,
            "selected_models": selected_models,
        },
        "scope": {
            "our_brand": scope.get("our_brand", ""),
            "include_competitors": bool(scope.get("include_competitors", False)),
            "competitor_brands": list(scope.get("competitor_brands", [])),
            "exact_match_required": bool(scope.get("exact_match_required", False)),
            "allow_family_context": bool(scope.get("allow_family_context", True)),
        },
        "focus": list(raw_config.get("focus", [])),
        "research_goal": raw_config.get("research_goal", ""),
        "reddit": {
            "subreddits": list(reddit_raw.get("subreddits", DEFAULT_SUBREDDITS)),
            "query_keywords": list(reddit_raw.get("query_keywords", DEFAULT_KEYWORDS)),
            "global_search_first": bool(reddit_raw.get("global_search_first", True)),
            "per_query_limit": int(reddit_raw.get("per_query_limit", 6 if mode == "weekly_monitoring" else 12)),
            "per_sub_limit": int(reddit_raw.get("per_sub_limit", 6 if mode == "weekly_monitoring" else 12)),
            "per_post_comment_limit": int(
                reddit_raw.get("per_post_comment_limit", 6 if mode == "weekly_monitoring" else 10)
            ),
        },
        "youtube": {
            "channels": list(youtube_raw.get("channels", DEFAULT_YOUTUBE_CHANNELS)),
            "include": list(youtube_raw.get("include", ["transcript", "title_desc", "comments"])),
            "auto_discovery": bool(youtube_raw.get("auto_discovery", True)),
            "max_videos_per_channel": int(youtube_raw.get("max_videos_per_channel", 2)),
            "global_search_first": bool(youtube_raw.get("global_search_first", True)),
            "max_videos_total": int(youtube_raw.get("max_videos_total", 5 if mode == "weekly_monitoring" else 8)),
            "videos": list(youtube_raw.get("videos", [])),
        },
        "output": output,
    }


def main():
    load_dotenv(ROOT / ".env")

    config_path = _pick_config_path()
    raw_config = json.loads(config_path.read_text(encoding="utf-8"))
    config = _normalize_config(raw_config)
    template_md = (ROOT / "weekly_report.template.md").read_text(encoding="utf-8")
    days = _days_from_window(config.get("date_range", {}))
    items = []
    reddit_diagnostics = []
    youtube_diagnostics = []
    search_queries = _build_search_queries(config)

    reddit_config = config.get("reddit", {})
    youtube_config = config.get("youtube", {})

    def _collect(run_reddit_config: dict, run_youtube_config: dict, run_label: str) -> tuple[list[dict], list[dict], list[dict]]:
        collected_items: list[dict] = []
        collected_reddit_diagnostics: list[dict] = []
        collected_youtube_diagnostics: list[dict] = []

        if "reddit" in config.get("sources", []):
            if run_reddit_config.get("global_search_first", True):
                collected_items.extend(
                    fetch_reddit_global_search(
                        queries=search_queries,
                        days=days,
                        per_query_limit=int(run_reddit_config.get("per_query_limit", 6)),
                        per_post_comment_limit=int(run_reddit_config.get("per_post_comment_limit", 6)),
                        user_agent=f"vacuum-voice-weekly/0.3 ({run_label}-global-search)",
                        diagnostics=collected_reddit_diagnostics,
                    )
                )
            collected_items.extend(
                fetch_reddit_public(
                    subreddits=run_reddit_config.get("subreddits", []),
                    days=days,
                    per_sub_limit=int(run_reddit_config.get("per_sub_limit", 6)),
                    per_post_comment_limit=int(run_reddit_config.get("per_post_comment_limit", 6)),
                    user_agent=f"vacuum-voice-weekly/0.2 ({run_label}-public-json)",
                    mode="new",
                    diagnostics=collected_reddit_diagnostics,
                )
            )

        if "youtube" in config.get("sources", []):
            collected_items.extend(
                fetch_youtube(
                    videos=run_youtube_config.get("videos", []),
                    channels=run_youtube_config.get("channels", []),
                    search_queries=search_queries if run_youtube_config.get("global_search_first", True) else [],
                    days=days,
                    max_videos_per_channel=int(run_youtube_config.get("max_videos_per_channel", 1)),
                    max_videos_total=int(run_youtube_config.get("max_videos_total", 5)),
                    include_comments="comments" in run_youtube_config.get("include", []),
                    diagnostics=collected_youtube_diagnostics,
                )
            )

        return collected_items, collected_reddit_diagnostics, collected_youtube_diagnostics

    items, reddit_diagnostics, youtube_diagnostics = _collect(reddit_config, youtube_config, "initial")

    retry_used = False
    if _should_retry_with_deeper_fetch(config, items, reddit_diagnostics):
        retry_used = True
        retry_items, retry_reddit_diagnostics, retry_youtube_diagnostics = _collect(
            _deepened_reddit_config(reddit_config),
            _deepened_youtube_config(youtube_config),
            "retry",
        )
        if len(retry_items) > len(items):
            items = retry_items
            reddit_diagnostics = retry_reddit_diagnostics
            youtube_diagnostics = retry_youtube_diagnostics

    raw_reddit_hits = sum(
        entry.get("results", 0)
        for entry in reddit_diagnostics
        if entry.get("source") in {"reddit_search", "reddit_listing"}
    )
    raw_youtube_hits = sum(
        entry.get("results", 0)
        for entry in youtube_diagnostics
        if entry.get("source") in {"youtube_search", "youtube_seed", "youtube_listing"}
    )

    config["runtime_stats"] = {
        "raw_reddit_hits": raw_reddit_hits,
        "raw_youtube_hits": raw_youtube_hits,
        "analyzed_reddit_hits": sum(1 for item in items if item.get("source") == "reddit"),
        "analyzed_youtube_hits": sum(1 for item in items if item.get("source") == "youtube"),
        "retry_used": retry_used,
    }

    analysis = analyze_corpus(items)
    report = render_weekly_report(template_md, config, analysis)

    out_dir = ROOT / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "weekly_report.md").write_text(report, encoding="utf-8")

    metrics = {
        "mode": config.get("mode", "weekly_monitoring"),
        "config_path": str(config_path),
        "time_window": config.get("date_range", {}).get("preset", "custom"),
        "sources": config.get("sources", []),
        "focus": config.get("focus", []),
        "search_queries": search_queries,
        "diagnostics": {
            "reddit": reddit_diagnostics,
            "youtube": youtube_diagnostics,
        },
        "coverage": {
            "raw_reddit_hits": raw_reddit_hits,
            "raw_youtube_hits": raw_youtube_hits,
            "reddit_posts_count": sum(1 for item in items if item.get("source") == "reddit"),
            "youtube_videos_count": sum(1 for item in items if item.get("source") == "youtube"),
            "comments_count": sum(len(item.get("comments", [])) for item in items),
            "brands_count": len(config.get("product_filter", {}).get("selected_brands", [])),
        },
        "retry_used": retry_used,
    }
    (out_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Done. Output in outputs/weekly_report.md (config: {config_path.name})")


if __name__ == "__main__":
    main()
