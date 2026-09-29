"""Request tracing - generates trace IDs and persists agent traces."""

import uuid
import time
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.observability.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TraceContext:
    """Holds trace information for a single request."""

    trace_id: UUID = field(default_factory=uuid.uuid4)
    session_id: Optional[str] = None
    user_id: Optional[UUID] = None
    start_time: float = field(default_factory=time.time)
    tools_called: list = field(default_factory=list)
    outcome: Optional[str] = None
    user_message_preview: Optional[str] = None

    def add_tool_call(self, name: str, ok: bool, error: Optional[str] = None, latency_ms: int = 0):
        self.tools_called.append({
            "name": name,
            "ok": ok,
            "error": error,
            "latency_ms": latency_ms,
        })

    @property
    def latency_ms(self) -> int:
        return int((time.time() - self.start_time) * 1000)


async def persist_trace(db: AsyncSession, trace: TraceContext):
    """Save the trace to agent_traces table."""
    try:
        import json
        preview = trace.user_message_preview
        if preview and len(preview) > 200:
            preview = preview[:200] + "..."

        await db.execute(
            text("""
                INSERT INTO agent_traces (trace_id, session_id, user_id, user_message_preview,
                                         tools_called, outcome, latency_ms)
                VALUES (:trace_id, :session_id, :user_id, :preview, :tools_called::jsonb,
                        :outcome, :latency_ms)
            """),
            {
                "trace_id": str(trace.trace_id),
                "session_id": trace.session_id,
                "user_id": str(trace.user_id) if trace.user_id else None,
                "preview": preview,
                "tools_called": json.dumps(trace.tools_called),
                "outcome": trace.outcome,
                "latency_ms": trace.latency_ms,
            },
        )
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to persist trace: {e}")
