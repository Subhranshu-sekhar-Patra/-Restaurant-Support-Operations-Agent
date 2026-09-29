"""RAG retriever - queries pgvector for semantically similar KB chunks."""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.config import settings
from app.rag.embedder import embed_text
from app.database import async_session
from app.observability.logging import get_logger

logger = get_logger(__name__)


async def retrieve_chunks(
    query: str,
    db: Optional[AsyncSession] = None,
    embedder=None,
    top_k: Optional[int] = None,
    min_similarity: Optional[float] = None,
) -> List[dict]:
    """
    Retrieve semantically similar KB chunks for a query.
    Uses the match_chunks SQL function with pgvector.
    """
    top_k = top_k or settings.RAG_TOP_K
    min_similarity = min_similarity or settings.RAG_MIN_SIMILARITY

    # Generate query embedding
    if embedder:
        query_embedding = await embedder(query)
    else:
        query_embedding = await embed_text(query)

    # Format embedding for pgvector
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    # Use provided session or create a new one
    should_close = False
    if db is None:
        db = async_session()
        should_close = True

    try:
        result = await db.execute(
            text("""
                SELECT chunk_id, content, section, source, effective_date, similarity
                FROM match_chunks(:embedding::vector, :match_count, :min_similarity)
            """),
            {
                "embedding": embedding_str,
                "match_count": top_k,
                "min_similarity": min_similarity,
            },
        )
        rows = result.mappings().all()

        chunks = []
        for row in rows:
            chunks.append({
                "chunk_id": str(row["chunk_id"]),
                "content": row["content"],
                "section": row["section"],
                "source": row["source"],
                "effective_date": str(row["effective_date"]) if row["effective_date"] else None,
                "similarity": float(row["similarity"]),
            })

        logger.info(f"RAG retrieval: query='{query[:50]}', found={len(chunks)} chunks")
        return chunks

    except Exception as e:
        logger.error(f"RAG retrieval error: {e}")
        return []
    finally:
        if should_close:
            await db.close()
