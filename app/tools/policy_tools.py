"""Policy search tool - RAG-based knowledge retrieval."""

from pydantic import ValidationError
from app.tools.schemas import ToolResult, SearchPolicyArgs
from app.rag.retriever import retrieve_chunks
from app.observability.logging import get_logger

logger = get_logger(__name__)


async def tool_search_policy(args: dict, db=None, embedder=None) -> ToolResult:
    """Search the knowledge base for policy information."""
    # Validate args
    try:
        validated = SearchPolicyArgs(**args)
    except ValidationError as e:
        return ToolResult(
            ok=False,
            error="invalid_argument",
            message="Please provide a search query of at least 3 characters.",
        )

    try:
        chunks = await retrieve_chunks(validated.query, db=db, embedder=embedder)

        if not chunks:
            return ToolResult(
                ok=True,
                data={"results": [], "message": "No relevant policy information found for this query."},
            )

        # Check for conflicts (multiple sources covering the same topic)
        sources = {}
        for chunk in chunks:
            src = chunk.get("source", "unknown")
            if src not in sources:
                sources[src] = []
            sources[src].append(chunk)

        has_conflict = len(sources) > 1
        conflict_note = None

        if has_conflict:
            # Sort by effective_date desc within each source group
            sorted_chunks = sorted(
                chunks,
                key=lambda c: c.get("effective_date", "1900-01-01"),
                reverse=True,
            )
            newest_date = sorted_chunks[0].get("effective_date")
            oldest_date = sorted_chunks[-1].get("effective_date")

            if newest_date != oldest_date:
                conflict_note = (
                    f"Multiple sources found. The most recent policy (effective {newest_date}) "
                    f"takes precedence. Older documents may contain outdated information."
                )
            else:
                conflict_note = (
                    "Multiple sources with the same effective date found. "
                    "This may need escalation to a support agent for clarification."
                )

        return ToolResult(
            ok=True,
            data={
                "results": chunks,
                "conflict_note": conflict_note,
                "sources": list(sources.keys()),
            },
        )

    except Exception as e:
        logger.error(f"Policy search error: {e}")
        return ToolResult(
            ok=False,
            error="internal",
            message="Policy search encountered an error. Please try again.",
        )
