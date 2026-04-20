import os
import shutil
import json
from dataclasses import dataclass

from pyspark.ml.clustering import KMeans
from pyspark.ml.feature import OneHotEncoder, StringIndexer, VectorAssembler
from pyspark.mllib.clustering import StreamingKMeansModel
from pyspark.mllib.linalg import Vectors as OldVectors
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, coalesce, lower, trim, when

from config import DatabaseConfig
from db import get_wikipedia_id_bounds, read_wikipedia_window


@dataclass
class StreamingKMeansConfig:
    k: int
    decay_factor: float
    model_path: str


class WikipediaStreamingKMeansTrainer:
    """Incremental clustering trainer using StreamingKMeansModel.update."""

    def __init__(
        self,
        spark: SparkSession,
        config: StreamingKMeansConfig,
        db_config: DatabaseConfig,
    ) -> None:
        self.spark = spark
        self.config = config
        self.db_config = db_config
        self._streaming_model: StreamingKMeansModel | None = None
        self._feature_metadata: dict | None = None

    def retrain_for_id_window(self, first_id: int, last_id: int) -> None:
        if first_id is None or last_id is None:
            return

        training_df = self._load_training_window(first_id, last_id)
        if training_df.rdd.isEmpty():
            print(f"[ML] No rows found for id range [{first_id}, {last_id}].")
            return

        feature_df = self._build_features(training_df)
        if feature_df.rdd.isEmpty():
            print(f"[ML] No feature rows available for id range [{first_id}, {last_id}].")
            return

        feature_rdd = feature_df.select("features").rdd.map(
            lambda row: OldVectors.dense(row["features"].toArray().tolist())
        )

        if self._streaming_model is None:
            self._streaming_model = self._initialize_model(feature_df)
        if self._streaming_model is None:
            raise RuntimeError("StreamingKMeans model could not be initialized.")

        # Incremental update: move centers toward latest window while retaining prior state.
        self._streaming_model.update(feature_rdd, self.config.decay_factor, "batches")
        self._save_model()

        print(
            f"[ML] Updated StreamingKMeans model for id range [{first_id}, {last_id}] "
            f"with decay_factor={self.config.decay_factor}."
        )

    def bootstrap_if_missing(self) -> bool:
        """Train an initial model from all available IDs when model artifacts are absent."""
        save_path = os.path.join(self.config.model_path, "streaming_kmeans")
        if os.path.exists(save_path):
            return False

        id_bounds = get_wikipedia_id_bounds(self.db_config)
        if id_bounds is None:
            print("[ML] Bootstrap skipped: no rows available in source table yet.")
            return False

        first_id, last_id = id_bounds
        print(f"[ML] Bootstrap training model for id range [{first_id}, {last_id}].")
        self.retrain_for_id_window(first_id, last_id)
        return True

    def _load_training_window(self, first_id: int, last_id: int) -> DataFrame:
        return read_wikipedia_window(
            spark=self.spark,
            db_config=self.db_config,
            first_id=first_id,
            last_id=last_id,
        )

    def _build_features(self, df: DataFrame) -> DataFrame:
        cleaned_df = (
            df.withColumn("wiki", when(trim(col("wiki")) == "", None).otherwise(lower(trim(col("wiki")))))
            .withColumn("type", when(trim(col("type")) == "", None).otherwise(lower(trim(col("type")))))
            .fillna({"wiki": "unknown", "type": "unknown", "bot": False})
            .withColumn("bot_val", coalesce(col("bot").cast("double"), col("bot").cast("int").cast("double")))
        )

        wiki_indexer = StringIndexer(inputCol="wiki", outputCol="wiki_idx", handleInvalid="keep")
        type_indexer = StringIndexer(inputCol="type", outputCol="type_idx", handleInvalid="keep")

        wiki_model = wiki_indexer.fit(cleaned_df)
        indexed_df = wiki_model.transform(cleaned_df)

        type_model = type_indexer.fit(indexed_df)
        indexed_df = type_model.transform(indexed_df)

        encoder = OneHotEncoder(
            inputCols=["wiki_idx", "type_idx"],
            outputCols=["wiki_vec", "type_vec"],
            handleInvalid="keep",
            dropLast=False,
        )
        encoder_model = encoder.fit(indexed_df)
        encoded_df = encoder_model.transform(indexed_df)

        wiki_size = int(encoder_model.categorySizes[0])
        type_size = int(encoder_model.categorySizes[1])
        wiki_labels = list(wiki_model.labels)
        type_labels = list(type_model.labels)

        if len(wiki_labels) < wiki_size:
            wiki_labels.extend(["unknown"] * (wiki_size - len(wiki_labels)))
        if len(type_labels) < type_size:
            type_labels.extend(["unknown"] * (type_size - len(type_labels)))

        self._feature_metadata = {
            "version": 1,
            "wiki": {"size": wiki_size, "labels": wiki_labels},
            "type": {"size": type_size, "labels": type_labels},
            "bot": {"index": wiki_size + type_size},
        }

        assembler = VectorAssembler(
            inputCols=["wiki_vec", "type_vec", "bot_val"],
            outputCol="features",
            handleInvalid="keep",
        )
        return assembler.transform(encoded_df).select("features")

    def _initialize_model(self, feature_df: DataFrame) -> StreamingKMeansModel:
        base_model = KMeans().setK(self.config.k).setSeed(1).fit(feature_df)
        # clusterCenters() returns numpy arrays in PySpark 3.4, not ml.linalg.Vector,
        # so use OldVectors.dense() directly instead of fromML().
        centers = base_model.clusterCenters()
        old_centers = [OldVectors.dense(c.tolist()) for c in centers]
        weights = [1.0] * len(old_centers)

        print(f"[ML] Initialized StreamingKMeans model with k={self.config.k}.")
        return StreamingKMeansModel(old_centers, weights)

    def _save_model(self) -> None:
        if self._streaming_model is None:
            return

        # Save into a fixed subdirectory so the bind-mounted parent directory
        # (which already exists) does not trigger "Output directory already exists".
        save_path = os.path.join(self.config.model_path, "streaming_kmeans")
        if os.path.exists(save_path):
            shutil.rmtree(save_path)
        self._streaming_model.save(self.spark.sparkContext, save_path)
        print(f"[ML] Model saved to {save_path}.")

        if self._feature_metadata is not None:
            metadata_path = os.path.join(self.config.model_path, "streaming_kmeans_metadata.json")
            with open(metadata_path, "w", encoding="utf-8") as metadata_file:
                json.dump(self._feature_metadata, metadata_file, indent=2)
            print(f"[ML] Model metadata saved to {metadata_path}.")
