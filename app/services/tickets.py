"""Ticket service - creates and queries support tickets with idempotency."""

import hashlib
from datetime import date
from uuid import UUID
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.observability.logging import get_logger

logger = get_logger(__name__)


def compute_idempotency_key(user_id: UUID, order_code: Optional[str], category: str) -> str:
    """Deterministic idempotency key: user + order + category + date."""
    raw = f"{user_id}|{order_code or 'none'}|{category}|{date.today()}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def create_ticket(
    db: AsyncSession,
    user_id: UUID,
    order_id: Optional[str],
    category: str,
    priority: str,
    sentiment: str,
    description: str,
    needs_human: bool,
    idempotency_key: str,
) -> dict:
    """
    Create a support ticket idempotently.
    Returns existing ticket if idempotency_key conflicts.
    """
    # Try insert
    result = await db.execute(
        text("""
            INSERT INTO support_tickets (user_id, order_id, category, priority, sentiment,
                                        description, needs_human, idempotency_key)
            VALUES (:user_id, :order_id, :category, :priority, :sentiment,
                    :description, :needs_human, :idempotency_key)
            ON CONFLICT (idempotency_key) DO NOTHING
            RETURNING ticket_code, id, status, created_at
        """),
        {
            "user_id": str(user_id),
            "order_id": order_id,
            "category": category,
            "priority": priority,
            "sentiment": sentiment,
            "description": description,
            "needs_human": needs_human,
            "idempotency_key": idempotency_key,
        },
    )
    await db.commit()

    row = result.mappings().first()
    if row:
        # New ticket created
        return {
            "ticket_code": row["ticket_code"],
            "is_new": True,
            "status": row["status"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }

    # Conflict: ticket already exists
    existing = await db.execute(
        text("SELECT ticket_code, status, created_at FROM support_tickets WHERE idempotency_key = :key"),
        {"key": idempotency_key},
    )
    existing_row = existing.mappings().first()
    if existing_row:
        return {
            "ticket_code": existing_row["ticket_code"],
            "is_new": False,
            "status": existing_row["status"],
            "created_at": existing_row["created_at"].isoformat() if existing_row["created_at"] else None,
        }

    raise RuntimeError("Ticket insert returned no row but no conflict found")


async def log_workflow(
    db: AsyncSession,
    trace_id: Optional[UUID],
    workflow: str,
    analysis: Optional[dict],
    ticket_code: Optional[str],
    notification: Optional[dict],
):
    """Log workflow execution to workflow_log table."""
    import json

    await db.execute(
        text("""
            INSERT INTO workflow_log (trace_id, workflow, analysis, ticket_code, notification)
            VALUES (:trace_id, :workflow, :analysis::jsonb, :ticket_code, :notification::jsonb)
        """),
        {
            "trace_id": str(trace_id) if trace_id else None,
            "workflow": workflow,
            "analysis": json.dumps(analysis) if analysis else None,
            "ticket_code": ticket_code,
            "notification": json.dumps(notification) if notification else None,
        },
    )
    await db.commit()
