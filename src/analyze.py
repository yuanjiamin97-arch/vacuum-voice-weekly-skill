from typing import Dict, Any, List
import re
from collections import Counter


FEATURE_LEXICON = {
    "threshold_climbing": [r"threshold", r"door sill", r"climb(ing)? over"],
    "obstacle_avoidance": [r"obstacle", r"avoid(ance)?", r"cable", r"cord", r"poop", r"toy"],
    "mop_automation": [r"mop", r"wash", r"dry", r"self[- ]clean", r"auto[- ]lift"],
    "hair_tangle": [r"tangle", r"hair", r"anti[- ]tangle", r"brush"],
    "carpet_performance": [r"carpet", r"high[- ]pile", r"rug", r"deep clean"],
}

SCENARIO_LEXICON = {
    "pets": [r"pet", r"dog", r"cat", r"fur"],
    "kids_toys": [r"kid", r"child", r"toy", r"lego"],
    "multi_floor": [r"upstairs", r"downstairs", r"multi[- ]floor", r"stairs"],
    "tight_layout": [r"tight", r"chair", r"table", r"narrow"],
}

def _count_tags(text: str, lex: Dict[str, List[str]]) -> Counter:
    c = Counter()
    for tag, patterns in lex.items():
        for p in patterns:
            if re.search(p, text, flags=re.I):
                c[tag] += 1
                break
    return c

def analyze_corpus(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    feature_counts = Counter()
    scenario_counts = Counter()
    source_counts = Counter()
    top_items = []

    for it in items:
        comments_blob = " ".join(comment.get("body", "") for comment in it.get("comments", []))
        if it.get("source") == "reddit":
            blob = f"{it.get('title', '')} {it.get('selftext', '')} {comments_blob}"
        else:
            blob = (
                f"{it.get('title', '')} {it.get('description', '')} "
                f"{it.get('transcript', '')} {comments_blob}"
            )

        feature_counts += _count_tags(blob, FEATURE_LEXICON)
        scenario_counts += _count_tags(blob, SCENARIO_LEXICON)
        source_counts[it.get("source", "unknown")] += 1
        top_items.append(
            {
                "source": it.get("source", ""),
                "title": it.get("title", ""),
                "url": it.get("url", ""),
                "score": int(it.get("score", 0) or 0) + len(it.get("comments", [])),
                "comments": len(it.get("comments", [])),
            }
        )

    top_items.sort(key=lambda item: item["score"], reverse=True)

    return {
        "top_features": feature_counts.most_common(5),
        "top_scenarios": scenario_counts.most_common(5),
        "feature_counts": dict(feature_counts),
        "scenario_counts": dict(scenario_counts),
        "source_counts": dict(source_counts),
        "top_items": top_items[:8],
        "total_items": len(items),
        "total_comments": sum(len(it.get("comments", [])) for it in items),
    }
