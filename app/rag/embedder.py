"""Embedder - generates embeddings using Google or OpenAI."""

from typing import List
from app.config import settings
from app.observability.logging import get_logger

logger = get_logger(__name__)

_client = None


def _get_google_client():
    """Lazy-init Google GenAI client."""
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=settings.LLM_API_KEY)
    return _client


async def embed_text(text: str) -> List[float]:
    """Generate embedding for a single text string."""
    return (await embed_texts([text]))[0]


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a list of texts."""
    if settings.EMBEDDING_PROVIDER == "google":
        return await _embed_google(texts)
    elif settings.EMBEDDING_PROVIDER == "openai":
        return await _embed_openai(texts)
    else:
        raise ValueError(f"Unknown embedding provider: {settings.EMBEDDING_PROVIDER}")


async def _embed_google(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using Google's embedding API."""
    import asyncio
    client = _get_google_client()

    def _sync_embed():
        result = client.models.embed_content(
            model=f"models/{settings.EMBEDDING_MODEL}",
            contents=texts,
        )
        return [list(e.values) for e in result.embeddings]

    return await asyncio.get_event_loop().run_in_executor(None, _sync_embed)


async def _embed_openai(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using OpenAI's API."""
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
            json={"model": settings.EMBEDDING_MODEL, "input": texts},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]
