import json
import math

from app.db.database import get_connection
from app.services.embedding_service import embed_text


def cosine_similarity(
    vector_a: list[float],
    vector_b: list[float],
) -> float:

    dot_product = sum(
        a * b
        for a, b in zip(vector_a, vector_b)
    )

    magnitude_a = math.sqrt(
        sum(a * a for a in vector_a)
    )

    magnitude_b = math.sqrt(
        sum(b * b for b in vector_b)
    )

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (
        magnitude_a * magnitude_b
    )


def retrieve_relevant_chunks(
    query: str,
    top_k: int = 5,
    min_score: float = 0.35,
):
    if not query or not query.strip():
        return []

    query_embedding = embed_text(query)
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT
            id,
            document_id,
            chunk_text,
            embedding
        FROM document_chunks
        """
    ).fetchall()
    connection.close()

    results = []
    for row in rows:
        stored_embedding = json.loads(row["embedding"])
        score = cosine_similarity(query_embedding, stored_embedding)
        if score >= min_score:
            results.append(
                {
                    "chunk_id": row["id"],
                    "document_id": row["document_id"],
                    "chunk_text": row["chunk_text"],
                    "text": row["chunk_text"],
                    "score": score,
                }
            )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]