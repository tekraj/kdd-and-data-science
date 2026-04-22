from pyspark.sql import DataFrame
from pyspark.sql.functions import col, lit, lower, trim, when
from pyspark.sql.types import StructType


_META_FIELDS = [
	"uri",
	"request_id",
	"id",
	"dt",
	"domain",
	"stream",
]


def _normalize_text_column(df: DataFrame, column_name: str) -> DataFrame:
	"""Trim whitespace and collapse empty strings to null for a text column."""
	return df.withColumn(
		column_name,
		when(trim(col(column_name)) == "", None).otherwise(trim(col(column_name))),
	)


def _flatten_meta(df: DataFrame) -> DataFrame:
	"""Flatten `meta` struct into `meta_*` columns expected by downstream sinks."""
	meta_data_type = df.schema["meta"].dataType if "meta" in df.columns else None
	has_meta_struct = isinstance(meta_data_type, StructType)

	for field_name in _META_FIELDS:
		target_column = f"meta_{field_name}"
		if target_column in df.columns:
			continue
		if has_meta_struct:
			df = df.withColumn(target_column, col(f"meta.{field_name}"))
		else:
			df = df.withColumn(target_column, lit(None).cast("string"))

	if "meta" in df.columns:
		df = df.drop("meta")

	return df


def preprocess_wikimedia_events(df: DataFrame) -> DataFrame:
	"""
	Apply data quality and normalization steps before writing downstream.

	Steps:
	- Drop rows with missing required identifiers/timestamps.
	- Normalize text fields.
	- Fill stable defaults for nullable fields.
	- Flatten nested `meta` object into top-level columns.
	"""
	required_columns = {"id", "timestamp", "type", "title", "user", "wiki", "bot"}
	missing_columns = sorted(required_columns.difference(df.columns))
	if missing_columns:
		raise ValueError(
			"Missing required columns for preprocessing: " + ", ".join(missing_columns)
		)

	clean_df = df.filter(col("id").isNotNull() & col("timestamp").isNotNull())

	for text_column in ["type", "title", "user", "wiki"]:
		clean_df = _normalize_text_column(clean_df, text_column)

	clean_df = clean_df.withColumn("wiki", lower(col("wiki")))
	clean_df = clean_df.fillna(
		{
			"type": "unknown",
			"title": "untitled",
			"user": "unknown",
			"wiki": "unknown",
			"bot": False,
		}
	)

	return _flatten_meta(clean_df)
