import logging
import math
from typing import Dict, List

from config.config import settings

logger = logging.getLogger(__name__)


def _cosine_distance(vec_a: List[float], vec_b: List[float]) -> float:
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 1.0
    similarity = dot / (norm_a * norm_b)
    similarity = max(-1.0, min(1.0, similarity))
    return 1.0 - similarity


def _build_weighted_distance_matrix(embeddings: List[List[float]], keywords: List[str]) -> List[List[float]]:
    size = len(embeddings)
    matrix = [[0.0 for _ in range(size)] for _ in range(size)]
    for i in range(size):
        for j in range(i + 1, size):
            base_distance = _cosine_distance(embeddings[i], embeddings[j])
            distance = base_distance * 0.8
            if keywords[i] and keywords[i] == keywords[j]:
                distance *= 0.5
            matrix[i][j] = distance
            matrix[j][i] = distance
    return matrix


def cluster_embeddings(embeddings: List[List[float]], articles: List[dict]) -> Dict[str, int]:
    if not embeddings:
        return {}
    normalized_articles = list(articles or [])
    if len(normalized_articles) < len(embeddings):
        normalized_articles.extend({} for _ in range(len(embeddings) - len(normalized_articles)))
    else:
        normalized_articles = normalized_articles[: len(embeddings)]

    keywords = [str((article or {}).get("keyword", "")).strip().lower() for article in normalized_articles]
    distance_matrix = _build_weighted_distance_matrix(embeddings, keywords)

    article_ids = [str((article or {}).get("article_id") or idx) for idx, article in enumerate(normalized_articles)]
    try:
        import numpy as np
        import hdbscan
    except Exception as exc:
        raise RuntimeError(f"HDBSCAN dependencies are unavailable: {exc}") from exc

    matrix = np.asarray(distance_matrix, dtype=float)
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=settings.clustering_min_cluster_size, 
        metric="precomputed"
    )
    labels = clusterer.fit_predict(matrix)
    mapping = {article_ids[idx]: int(label) for idx, label in enumerate(labels)}
    logger.info("Generated %d cluster labels with HDBSCAN", len(mapping))
    return mapping
