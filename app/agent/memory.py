"""Conversation memory - load and persist messages."""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.observability.logging import get_logger

logger = get_logger(__name__)


async def load_history(
    db: AsyncSession,
    session_id: str,
    user_id: UUID,
    limit: int = 10,
) -> tuple[Optional[str], List[dict], Optional[str]]:
    """
    Load conversation history.
    Returns (conversation_id, messages, last_order_code).
    Creates conversation if it doesn't exist.
    """
    # Get or create conversation
    result = await db.execute(
        text("""
            SELECT id, last_order_code FROM conversations
            WHERE session_id = :session_id
        """),
        {"session_id": session_id},
    )
    row = result.mappings().first()

    if row:
        conv_id = str(row["id"])
        last_order_code = row["last_order_code"]
    else:
        # Create new conversation
        result = await db.execute(
            text("""
                INSERT INTO conversations (session_id, user_id)
                VALUES (:session_id, :user_id)
                RETURNING id
            """),
            {"session_id": session_id, "user_id": str(user_id)},
        )
        await db.commit()
        conv_id = str(result.scalar_one())
        last_order_code = None

    # Load recent messages
    msg_result = await db.execute(
        text("""
            SELECT role, content FROM messages
            WHERE conversation_id = :conv_id
            ORDER BY created_at DESC
            LIMIT :limit
        """),
        {"conv_id": conv_id, "limit": limit},
    )
    rows = msg_result.mappings().all()

    # Reverse to chronological order
    messages = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    return conv_id, messages, last_order_code


async def save_message(
    db: AsyncSession,
    conversation_id: str,
    role: str,
    content: str,
):
    """Save a single message to the conversation."""
    await db.execute(
        text("""
            INSERT INTO messages (conversation_id, role, content)
            VALUES (:conv_id, :role, :content)
        """),
        {"conv_id": conversation_id, "role": role, "content": content},
    )
    await db.commit()


async def remember_order(
    db: AsyncSession,
    session_id: str,
    order_code: str,
):
    """Store the last discussed order code for follow-up questions."""
    await db.execute(
        text("""
            UPDATE conversations SET last_order_code = :order_code
            WHERE session_id = :session_id
        """),
        {"order_code": order_code, "session_id": session_id},
    )
    await db.commit()
