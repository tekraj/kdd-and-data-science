from __future__ import annotations
from collections import Counter, defaultdict
from typing import Any

def _safe_label(item: dict[str, Any]) -> str:
    return str(item.get("label") or "unknown")

def _safe_score(item: dict[str, Any]) -> float:
    try:
        return float(item.get("score", 0.0))
    except (TypeError, ValueError):
        return 0.0

def map_cluster_insights(raw: dict[str, Any]) -> dict[str, Any]:
    clusters = raw.get("clusters", []) or []
    model_path = str(raw.get("model_path", ""))

    mapped_clusters: list[dict[str, Any]] = []
    wiki_score_totals: dict[str, float] = defaultdict(float)
    type_score_totals: dict[str, float] = defaultdict(float)
    primary_type_counts: Counter[str] = Counter()
    primary_wiki_counts: Counter[str] = Counter()
    
    # New: Track average confidence/score per cluster for stability metrics
    cluster_purity_scores: list[dict[str, Any]] = []

    for cluster in clusters:
        cluster_id = int(cluster.get("cluster_id", -1))
        decoded = cluster.get("decoded", {}) or {}

        raw_wiki = decoded.get("wiki_top_labels", []) or []
        raw_type = decoded.get("type_top_labels", []) or []

        top_wikis = [
            {"label": _safe_label(item), "score": round(_safe_score(item), 6)}
            for item in raw_wiki[:5] # Increased to 5 for better distribution analysis
        ]
        top_types = [
            {"label": _safe_label(item), "score": round(_safe_score(item), 6)}
            for item in raw_type[:3]
        ]

        primary_wiki = top_wikis[0]["label"] if top_wikis else "unknown"
        primary_type = top_types[0]["label"] if top_types else "unknown"
        
        # Calculate 'Purity': How dominant is the primary type?
        # Useful for teaching students if k-means is converging well.
        purity = top_types[0]["score"] if top_types else 0.0
        
        bot_score = round(float(decoded.get("bot_score", 0.0) or 0.0), 6)

        for item in top_wikis:
            wiki_score_totals[item["label"]] += item["score"]
        for item in top_types:
            type_score_totals[item["label"]] += item["score"]

        primary_type_counts[primary_type] += 1
        primary_wiki_counts[primary_wiki] += 1

        mapped_clusters.append({
            "cluster_id": cluster_id,
            "primary_wiki": primary_wiki,
            "primary_type": primary_type,
            "bot_score": bot_score,
            "purity_score": purity, 
            "top_wikis": top_wikis,
            "top_types": top_types,
        })

    # --- Chart Formatting ---

    return {
        "summary": {
            "model_path": model_path,
            "cluster_count": len(mapped_clusters),
            "total_entities_tracked": sum(primary_type_counts.values())
        },
        "clusters": mapped_clusters,
        "charts": {
            "wiki_score_distribution": [
                {"label": k, "score": round(v, 6)} 
                for k, v in sorted(wiki_score_totals.items(), key=lambda x: x[1], reverse=True)[:15]
            ],
            "type_score_distribution": [
                {"label": k, "score": round(v, 6)} 
                for k, v in sorted(type_score_totals.items(), key=lambda x: x[1], reverse=True)
            ],
            "primary_type_cluster_count": [
                {"label": k, "count": v} for k, v in primary_type_counts.most_common()
            ],
            "bot_vandalism_baseline": [
                {"cluster_id": c["cluster_id"], "bot_score": c["bot_score"], "label": c["primary_type"]}
                for c in mapped_clusters
            ],
            "cluster_purity": [
                {"cluster_id": c["cluster_id"], "purity": c["purity_score"]}
                for c in mapped_clusters
            ]
        },
    }