import re
from typing import Dict, Any
from datetime import datetime, timezone


FEATURE_CN = {
    "threshold_climbing": "越门槛/跨障碍",
    "obstacle_avoidance": "稳定避障",
    "mop_automation": "拖布全自动维护",
    "hair_tangle": "防缠绕",
    "carpet_performance": "地毯深度清洁",
}
SCENARIO_CN = {
    "pets": "宠物毛发",
    "kids_toys": "儿童玩具散落",
    "multi_floor": "多楼层",
    "tight_layout": "复杂家具/狭窄动线",
}


def _link_label(item: Dict[str, Any]) -> str:
    title = (item.get("title") or "").strip()
    if not title:
        return item.get("source", "Evidence").title()
    return title[:56] + ("..." if len(title) > 56 else "")


def _link(item: Dict[str, Any]) -> str:
    url = (item.get("url") or "").strip()
    if not url:
        return "N/A"
    return f"[{_link_label(item)}]({url})"


def _link_block(items: list[Dict[str, Any]], limit: int = 2) -> str:
    if not items:
        return "N/A"
    return "<br>".join(_link(item) for item in items[:limit] if item.get("url")) or "N/A"

def render_weekly_report(template_md: str, config: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    brands = config["product_filter"]["selected_brands"]
    sources = ", ".join(config["sources"])
    time_window = config["date_range"].get("preset", "custom")
    runtime_stats = config.get("runtime_stats", {})
    top_features = analysis.get("top_features", [])
    top_scenarios = analysis.get("top_scenarios", [])
    top_items = analysis.get("top_items", [])
    top_reddit_items = [item for item in top_items if item.get("source") == "reddit"]
    top_youtube_items = [item for item in top_items if item.get("source") == "youtube"]

    rows = []
    for idx, (feat, cnt) in enumerate(top_features, start=1):
        evidence = _link_block(top_reddit_items or top_items, limit=2)
        rows.append(
            f"| {idx} | {feat} | {FEATURE_CN.get(feat,'')} | {cnt} | → |  |  | {evidence} |"
        )
    top5_table = "\n".join(rows) if rows else "| 1 |  |  |  |  |  |  |  |"

    if top_features:
        top_name, top_count = top_features[0]
        cn_takeaway_1 = f"本周需求Top为：{FEATURE_CN.get(top_name, top_name)}（提及 {top_count} 次）。"
        en_takeaway_1 = f"Top demand: {top_name} ({top_count} mentions)."
    else:
        cn_takeaway_1 = "本周有效样本不足，暂时无法形成稳定需求排序。"
        en_takeaway_1 = "There was not enough signal this week for a stable demand ranking."

    out = template_md
    out = out.replace("{{time_window}}", time_window)
    out = out.replace("{{sources}}", sources)
    out = out.replace("{{filter_mode}}", config["product_filter"]["mode"])
    out = out.replace("{{selected_brands}}", str(brands))
    out = out.replace("{{selected_models}}", str(config["product_filter"].get("selected_models", [])))
    out = out.replace("{{channels_count}}", str(len(config.get("youtube", {}).get("channels", []))))
    out = out.replace("{{videos_count}}", str(analysis.get("source_counts", {}).get("youtube", 0)))
    out = out.replace("{{reddit_posts}}", str(analysis.get("source_counts", {}).get("reddit", 0)))
    out = out.replace("{{comments_total}}", str(analysis.get("total_comments", 0)))
    out = out.replace("{{brands_count}}", str(len(brands)))
    out = out.replace("{{models_count}}", "0")
    out = out.replace("{{transcript_coverage}}", "best-effort")

    out = out.replace("{{cn_takeaway_1}}", cn_takeaway_1)
    out = out.replace("{{en_takeaway_1}}", en_takeaway_1)
    out = out.replace("{{cn_takeaway_2}}", "高频抱怨主要集中在自动化中断与人工干预成本。")
    out = out.replace("{{cn_takeaway_3}}", "跨平台共同信号集中在避障、门槛和毛发处理。")
    out = out.replace("{{en_takeaway_2}}", "Negative signal clusters around interrupted automation and manual intervention.")
    out = out.replace("{{en_takeaway_3}}", "Cross-platform signal still concentrates on obstacles, thresholds, and hair.")

    empty_top5_block = "\n".join(
        [
            "| 1 |  |  |  |  |  |  |  |",
            "| 2 |  |  |  |  |  |  |  |",
            "| 3 |  |  |  |  |  |  |  |",
            "| 4 |  |  |  |  |  |  |  |",
            "| 5 |  |  |  |  |  |  |  |",
        ]
    )
    if empty_top5_block in out:
        out = out.replace(empty_top5_block, top5_table)

    reddit_links = [item["url"] for item in top_reddit_items if item["url"]][:2]
    youtube_links = [item["url"] for item in top_youtube_items if item["url"]][:2]
    top_scenario = top_scenarios[0][0] if top_scenarios else "mixed-home layouts"

    replacements = {
        "{{signal_1}}": top_features[0][0] if len(top_features) > 0 else "No strong signal",
        "{{trigger_1}}": top_scenario,
        "{{cn_trigger_1}}": top_scenario,
        "{{signal_2}}": "Obstacle avoidance consistency",
        "{{trigger_2}}": "Repeated rescue complaints",
        "{{cn_trigger_2}}": "重复出现卡困和人工解救",
        "{{signal_3}}": "Lower maintenance cleaning",
        "{{trigger_3}}": "Hair and brush upkeep mentions",
        "{{cn_trigger_3}}": "毛发和滚刷维护被反复提及",
        "{{p0_feature_1}}": top_features[0][0] if len(top_features) > 0 else "threshold_climbing",
        "{{p0_feature_2}}": top_features[1][0] if len(top_features) > 1 else "obstacle_avoidance",
        "{{p0_feature_3}}": top_features[2][0] if len(top_features) > 2 else "hair_tangle",
        "{{scenarios_1}}": top_scenario,
        "{{failure_modes_1}}": "Missed rooms or manual repositioning",
        "{{pm_impl_1}}": "Validate in real homes, not lab-only claims",
        "{{mkt_impl_1}}": "Use real-world threshold proof content",
        "{{scenarios_2}}": "toys, cords, clutter",
        "{{failure_modes_2}}": "stuck runs and false avoidance",
        "{{pm_impl_2}}": "Improve detection and recovery",
        "{{mkt_impl_2}}": "Lead with unattended reliability",
        "{{scenarios_3}}": "pet hair and long-hair homes",
        "{{failure_modes_3}}": "brush wrap and frequent maintenance",
        "{{pm_impl_3}}": "Reduce brush cleaning burden",
        "{{mkt_impl_3}}": "Translate into lower-maintenance messaging",
        "{{reddit_link_1}}": reddit_links[0] if len(reddit_links) > 0 else "None captured",
        "{{reddit_link_2}}": reddit_links[1] if len(reddit_links) > 1 else "None captured",
        "{{yt_link_1}}": youtube_links[0] if len(youtube_links) > 0 else "None captured",
        "{{yt_link_2}}": youtube_links[1] if len(youtube_links) > 1 else "None captured",
        "{{new_model_1}}": "None auto-detected",
        "{{new_model_2}}": "None auto-detected",
        "{{missing_notes}}": (
            "Generated from live fetches on "
            f"{datetime.now(timezone.utc).isoformat()} "
            f"(raw_reddit_hits={runtime_stats.get('raw_reddit_hits', 0)}, "
            f"analyzed_reddit_hits={runtime_stats.get('analyzed_reddit_hits', 0)}, "
            f"raw_youtube_hits={runtime_stats.get('raw_youtube_hits', 0)}, "
            f"analyzed_youtube_hits={runtime_stats.get('analyzed_youtube_hits', 0)}, "
            f"retry_used={runtime_stats.get('retry_used', False)})"
        ),
    }
    for key, value in replacements.items():
        out = out.replace(key, value)

    product_rows = "\n".join(
        [
            (
                f"| {', '.join(config['product_filter'].get('selected_models', []) or config['product_filter'].get('selected_brands', [])) or 'Target'} "
                f"| Active social discussion; visible comparison context; usable evidence base "
                f"| Public sample may still skew toward support / shopping threads; platform bias applies "
                f"| Comparison, shopping, and ownership "
                f"| {_link_block(top_reddit_items, limit=3)} |"
            ),
            (
                f"| Broader Context "
                f"| Adds category context and adjacent alternatives "
                f"| Can dilute exact-model clarity if overused "
                f"| Review and discovery "
                f"| {_link_block(top_youtube_items, limit=2)} |"
            ),
        ]
    )
    empty_product_block = "\n".join(
        [
            "|  |  |  |  |  |",
            "|  |  |  |  |  |",
        ]
    )
    if empty_product_block in out:
        out = out.replace(empty_product_block, product_rows)

    out = re.sub(r"\{\{[^}]+\}\}", "N/A", out)

    return out
