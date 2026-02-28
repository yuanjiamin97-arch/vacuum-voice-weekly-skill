from typing import Dict, Any, List
from datetime import datetime


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

def render_weekly_report(template_md: str, config: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    brands = config["product_filter"]["selected_brands"]
    sources = ", ".join(config["sources"])
    time_window = config["date_range"].get("preset", "custom")

    # Build simple rows for Top 5
    rows = []
    for idx, (feat, cnt) in enumerate(analysis["top_features"], start=1):
        rows.append(
            f"| {idx} | {feat} | {FEATURE_CN.get(feat,'')} | {cnt} | → |  |  |  |"
        )
    top5_table = "\n".join(rows) if rows else "| 1 |  |  |  |  |  |  |  |"

    # very light snapshot
    cn_takeaway_1 = f"本周需求Top为：{FEATURE_CN.get(analysis['top_features'][0][0],'')}（提及 {analysis['top_features'][0][1]} 次）。" if analysis["top_features"] else "本周需求Top尚不足以统计。"
    en_takeaway_1 = f"Top demand: {analysis['top_features'][0][0]} ({analysis['top_features'][0][1]} mentions)." if analysis["top_features"] else "Not enough data for top demand."

    # Replace a few placeholders (your template already has many)
    out = template_md
    out = out.replace("{{time_window}}", time_window)
    out = out.replace("{{sources}}", sources)
    out = out.replace("{{filter_mode}}", config["product_filter"]["mode"])
    out = out.replace("{{selected_brands}}", str(brands))
    out = out.replace("{{selected_models}}", str(config["product_filter"].get("selected_models", [])))

    out = out.replace("{{cn_takeaway_1}}", cn_takeaway_1)
    out = out.replace("{{en_takeaway_1}}", en_takeaway_1)
    out = out.replace("{{cn_takeaway_2}}", "（MVP阶段：口碑与竞品模块待接入更细粒度抽取）")
    out = out.replace("{{cn_takeaway_3}}", "（MVP阶段：竞争信号待接入YouTube视频列表与Reddit对比）")
    out = out.replace("{{en_takeaway_2}}", "(MVP: reputation extraction TBD)")
    out = out.replace("{{en_takeaway_3}}", "(MVP: competitive signals TBD)")

    # Drop in the top5 rows by replacing the empty table body block crudely:
    marker = "| 1 |  |  |  |  |  |  |  |"
    if marker in out:
        out = out.replace(marker, top5_table)

    # Stamp
    out = out.replace("{{missing_notes}}", f"MVP run at {datetime.utcnow().isoformat()}Z")

    return out
