import json
import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

import psycopg2

from config import DatabaseConfig
from db import get_wikipedia_id_bounds

_ARTIFACT_NAME = "tfidf_trending_topics.json"
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
	"a",
	"an",
	"and",
	"are",
	"as",
	"at",
	"be",
	"by",
	"for",
	"from",
	"has",
	"in",
	"is",
	"it",
	"of",
	"on",
	"or",
	"that",
	"the",
	"to",
	"was",
	"were",
	"will",
	"with",
	"wikipedia",
	"wiki",
}


@dataclass
class TfIdfConfig:
	model_path: str
	top_n: int = 10


class TfIdfTrendingTopicsTrainer:
	"""Builds and persists trending topics using a TF-IDF score over wiki titles."""

	def __init__(self, config: TfIdfConfig, db_config: DatabaseConfig) -> None:
		self.config = config
		self.db_config = db_config

	def retrain_for_id_window(self, first_id: int, last_id: int) -> None:
		if first_id is None or last_id is None:
			return

		titles = self._read_titles_window(first_id, last_id)
		if not titles:
			print(f"[ML] No valid titles found for TF-IDF id range [{first_id}, {last_id}].")
			return

		topics = self._build_tfidf_topics(titles)
		if not topics:
			print(f"[ML] No topics generated for TF-IDF id range [{first_id}, {last_id}].")
			return

		previous_mentions = self._load_previous_mentions()
		for topic in topics:
			prev = previous_mentions.get(topic["topic"])
			curr = int(topic["mentions"])
			if prev is None:
				topic["trend"] = "new"
			elif curr >= math.ceil(prev * 1.05):
				topic["trend"] = "up"
			elif curr <= math.floor(prev * 0.95):
				topic["trend"] = "down"
			else:
				topic["trend"] = "stable"

		artifact = {
			"model": "tf-idf",
			"version": 1,
			"window": {
				"first_id": int(first_id),
				"last_id": int(last_id),
				"document_count": len(titles),
			},
			"topics": topics,
		}
		self._save_artifact(artifact)
		print(
			f"[ML] Updated TF-IDF topics for id range [{first_id}, {last_id}] with {len(topics)} topics."
		)

	def bootstrap_if_missing(self) -> bool:
		artifact_path = self._artifact_path()
		if os.path.exists(artifact_path):
			return False

		id_bounds = get_wikipedia_id_bounds(self.db_config)
		if id_bounds is None:
			print("[ML] TF-IDF bootstrap skipped: no rows available in source table yet.")
			return False

		first_id, last_id = id_bounds
		print(f"[ML] Bootstrap TF-IDF model for id range [{first_id}, {last_id}].")
		self.retrain_for_id_window(first_id, last_id)
		return True

	def _artifact_path(self) -> str:
		return os.path.join(self.config.model_path, _ARTIFACT_NAME)

	def _read_titles_window(self, first_id: int, last_id: int) -> list[str]:
		conn = psycopg2.connect(
			host=self.db_config.host,
			port=self.db_config.port,
			dbname=self.db_config.dbname,
			user=self.db_config.user,
			password=self.db_config.password,
		)
		try:
			with conn.cursor() as cur:
				cur.execute(
					f"SELECT title FROM {self.db_config.table} WHERE id BETWEEN %s AND %s",
					(int(first_id), int(last_id)),
				)
				rows = cur.fetchall()
		finally:
			conn.close()

		titles = [str(row[0]).strip() for row in rows if row and row[0] is not None]
		return [title for title in titles if title]

	def _build_tfidf_topics(self, titles: list[str]) -> list[dict[str, Any]]:
		tokenized_docs = [self._extract_terms(title) for title in titles]
		tokenized_docs = [tokens for tokens in tokenized_docs if tokens]
		if not tokenized_docs:
			return []

		num_docs = len(tokenized_docs)
		document_frequency: Counter[str] = Counter()
		term_tf_sum: Counter[str] = Counter()

		for tokens in tokenized_docs:
			token_counts = Counter(tokens)
			total_terms = len(tokens)
			unique_terms = set(tokens)
			for term in unique_terms:
				document_frequency[term] += 1
			for term, count in token_counts.items():
				term_tf_sum[term] += float(count) / float(total_terms)

		scored_topics: list[dict[str, Any]] = []
		for term, tf_sum in term_tf_sum.items():
			df = document_frequency[term]
			idf = math.log((1.0 + num_docs) / (1.0 + df)) + 1.0
			mean_tfidf = (tf_sum / float(num_docs)) * idf
			scored_topics.append(
				{
					"topic": term,
					"mentions": int(df),
					"score": round(float(mean_tfidf), 6),
				}
			)

		scored_topics.sort(key=lambda x: (x["score"], x["mentions"], x["topic"]), reverse=True)
		return scored_topics[: self.config.top_n]

	def _extract_terms(self, text: str) -> list[str]:
		tokens = [tok for tok in _TOKEN_PATTERN.findall(text.lower()) if len(tok) > 2 and tok not in _STOP_WORDS]
		if not tokens:
			return []

		bigrams = [f"{tokens[i]} {tokens[i + 1]}" for i in range(len(tokens) - 1)]
		return tokens + bigrams

	def _load_previous_mentions(self) -> dict[str, int]:
		artifact_path = self._artifact_path()
		if not os.path.exists(artifact_path):
			return {}
		try:
			with open(artifact_path, "r", encoding="utf-8") as artifact_file:
				payload = json.load(artifact_file)
			topics = payload.get("topics", []) or []
			return {
				str(item.get("topic")): int(item.get("mentions", 0) or 0)
				for item in topics
				if item.get("topic")
			}
		except Exception:
			return {}

	def _save_artifact(self, artifact: dict[str, Any]) -> None:
		os.makedirs(self.config.model_path, exist_ok=True)
		with open(self._artifact_path(), "w", encoding="utf-8") as artifact_file:
			json.dump(artifact, artifact_file, indent=2)


def load_tfidf_trending_topics(model_path: str) -> dict[str, Any]:
	artifact_path = os.path.join(model_path, _ARTIFACT_NAME)
	if not os.path.exists(artifact_path):
		raise FileNotFoundError(
			f"TF-IDF model not found at {artifact_path}. Retrain once before querying trending topics."
		)

	with open(artifact_path, "r", encoding="utf-8") as artifact_file:
		payload = json.load(artifact_file)

	return {
		"model": payload.get("model", "tf-idf"),
		"version": int(payload.get("version", 1)),
		"window": payload.get("window", {}),
		"data": payload.get("topics", []) or [],
	}
