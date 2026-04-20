import re

from clustering.streaming_kmeans import StreamingKMeansConfig, WikipediaStreamingKMeansTrainer
from config import load_app_config
from spark.event_parser import parse_retrain_event
from spark.session import create_spark_session


def _build_trainer(spark, app_config) -> WikipediaStreamingKMeansTrainer:
    return WikipediaStreamingKMeansTrainer(
        spark,
        StreamingKMeansConfig(
            k=app_config.model.k,
            decay_factor=app_config.model.decay_factor,
            model_path=app_config.model.model_path,
        ),
        app_config.database,
    )


def listen_and_retrain() -> None:
    app_config = load_app_config()
    spark = create_spark_session()
    trainer = _build_trainer(spark, app_config)

    try:
        trainer.bootstrap_if_missing()
    except Exception as err:
        print(f"[ML] Bootstrap training failed: {err}")

    # subscribePattern uses listTopics() instead of listOffsets() on specific
    # partitions, so it tolerates the topic not existing yet — the stream starts
    # with zero partitions and discovers the topic once it is created.
    topic_pattern = f"^{re.escape(app_config.kafka.retrain_topic)}$"

    event_stream = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", app_config.kafka.kafka_brokers)
        .option("subscribePattern", topic_pattern)
        .option("startingOffsets", app_config.kafka.starting_offsets)
        .option("failOnDataLoss", "false")
        .load()
        .selectExpr("CAST(value AS STRING) AS payload")
    )

    def process_event_batch(batch_df, batch_id):
        rows = batch_df.collect()
        if not rows:
            return

        for row in rows:
            try:
                event_window = parse_retrain_event(row["payload"])
                if event_window is None:
                    continue
                first_id, last_id = event_window
                trainer.retrain_for_id_window(first_id, last_id)
            except Exception as err:
                print(f"[ML] Failed to process retrain event in batch {batch_id}: {err}")

    print(
        f"[ML] Listening on topic pattern={topic_pattern}, "
        f"k={app_config.model.k}, "
        f"decay_factor={app_config.model.decay_factor}, "
        f"model_path={app_config.model.model_path}"
    )

    query = (
        event_stream.writeStream.foreachBatch(process_event_batch)
        .option("checkpointLocation", app_config.listener.checkpoint_path)
        .trigger(processingTime=f"{app_config.listener.trigger_interval_seconds} seconds")
        .start()
    )
    query.awaitTermination()
