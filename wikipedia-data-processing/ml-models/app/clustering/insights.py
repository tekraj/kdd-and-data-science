import json
import os
from typing import Any

from pyspark import SparkConf, SparkContext
from pyspark.mllib.clustering import StreamingKMeansModel

from config import load_app_config


def _load_model_metadata(model_root_path: str) -> dict[str, Any]:
    metadata_path = os.path.join(model_root_path, "streaming_kmeans_metadata.json")
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(
            f"Metadata not found at {metadata_path}. Retrain once to generate decoding metadata."
        )

    with open(metadata_path, "r", encoding="utf-8") as metadata_file:
        return json.load(metadata_file)


def _get_spark_context() -> SparkContext:
    spark_conf = (
        SparkConf()
        .setAppName("WikipediaInsightsAPI")
        .setMaster(os.getenv("SPARK_MASTER", "local[*]"))
        .set("spark.ui.enabled", "false")
    )
    return SparkContext.getOrCreate(conf=spark_conf)


def _decode_top_labels(values: list[float], labels: list[str], top_n: int = 3) -> list[dict[str, Any]]:
    ranked = sorted(enumerate(values), key=lambda x: x[1], reverse=True)
    decoded: list[dict[str, Any]] = []
    for idx, score in ranked[:top_n]:
        label = labels[idx] if idx < len(labels) else "unknown"
        decoded.append(
            {
                "label": label,
                "score": round(float(score), 6),
            }
        )
    return decoded


def load_cluster_insights() -> dict[str, Any]:
    config = load_app_config()
    model_root_path = config.model.model_path
    model_dir = os.path.join(model_root_path, "streaming_kmeans")

    if not os.path.exists(model_dir):
        raise FileNotFoundError(
            f"Model not found at {model_dir}. Retrain once before querying insights."
        )

    metadata = _load_model_metadata(model_root_path)
    wiki_size = int(metadata["wiki"]["size"])
    type_size = int(metadata["type"]["size"])
    bot_index = int(metadata["bot"]["index"])
    wiki_labels = metadata["wiki"]["labels"]
    type_labels = metadata["type"]["labels"]

    sc = _get_spark_context()
    model = StreamingKMeansModel.load(sc, model_dir)

    clusters: list[dict[str, Any]] = []
    for cluster_id, center_vector in enumerate(model.centers):
        center = [float(v) for v in center_vector.toArray().tolist()]
        wiki_scores = center[:wiki_size]
        type_scores = center[wiki_size : wiki_size + type_size]
        bot_score = center[bot_index] if bot_index < len(center) else 0.0

        clusters.append(
            {
                "cluster_id": cluster_id,
                "decoded": {
                    "wiki_top_labels": _decode_top_labels(wiki_scores, wiki_labels),
                    "type_top_labels": _decode_top_labels(type_scores, type_labels),
                    "bot_score": round(float(bot_score), 6),
                },
                "centroid_raw": center,
            }
        )

    return {
        "model_path": model_dir,
        "clusters": clusters,
        "feature_metadata": metadata,
    }
