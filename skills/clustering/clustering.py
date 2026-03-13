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


def _build_weighted_distance_matrix(embeddings: List[List[float]], metadata: List[dict]) -> List[List[float]]:
    size = len(embeddings)
    matrix = [[0.0 for _ in range(size)] for _ in range(size)]
    
    for i in range(size):
        for j in range(i + 1, size):
            # Base cosine distance
            dist = _cosine_distance(embeddings[i], embeddings[j])
            
            # Anchoring Logic:
            # If one is an anchor (keyword) and the other is an article:
            # We want to pull articles TOWARDS their keyword if they are semantically similar.
            type_i = metadata[i].get("type", "article")
            type_j = metadata[j].get("type", "article")
            kw_i = str(metadata[i].get("keyword", "")).strip().lower()
            kw_j = str(metadata[j].get("keyword", "")).strip().lower()

            # If they share the same keyword, reduce distance (pull them together)
            if kw_i and kw_i == kw_j:
                dist *= 0.4 # Strong pull for same keyword
            
            # If one is a keyword anchor and the other is an article for that keyword
            if (type_i == "keyword" and type_j == "article" and kw_i == kw_j) or \
               (type_j == "keyword" and type_i == "article" and kw_i == kw_j):
                dist *= 0.25 # Even stronger pull to anchor

            matrix[i][j] = dist
            matrix[j][i] = dist
    return matrix


def cluster_embeddings(embeddings: List[List[float]], articles: List[dict]) -> Dict[str, int]:
    if not embeddings:
        return {}
    normalized_articles = list(articles or [])
    if len(normalized_articles) < len(embeddings):
        normalized_articles.extend({} for _ in range(len(embeddings) - len(normalized_articles)))
    else:
        normalized_articles = normalized_articles[: len(embeddings)]

    distance_matrix = _build_weighted_distance_matrix(embeddings, normalized_articles)

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
