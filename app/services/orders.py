"""Order service - database access with ownership-filtered queries."""

from uuid import UUID
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.observability.logging import get_logger
from app.config import settings

logger = get_logger(__name__)


class OrderServiceError(Exception):
    """Raised when order operations fail."""
    pass


async def get_order_status(db: AsyncSession, user_id: UUID, order_code: str) -> Optional[dict]:
    """
    Fetch order status. Always filters by user_id for authorization.
    Returns None if not found or not owned by user (same behavior = no existence leak).
    """
    # Simulate failure if configured
    if settings.SIMULATE_FAILURE == "orders_timeout":
        import asyncio
        raise asyncio.TimeoutError("Simulated order service timeout")
    if settings.SIMULATE_FAILURE == "db_down":
        raise ConnectionError("Simulated database unavailability")

    result = await db.execute(
        text("""
            SELECT o.order_code, o.status, o.payment_status, o.total_amount, o.currency,
                   o.eta_minutes, o.created_at, o.updated_at,
                   r.name as restaurant_name
            FROM orders o
            LEFT JOIN restaurants r ON r.id = o.restaurant_id
            WHERE o.order_code = :order_code AND o.user_id = :user_id
        """),
        {"order_code": order_code, "user_id": str(user_id)},
    )
    row = result.mappings().first()
    if not row:
        return None

    return {
        "order_code": row["order_code"],
        "status": row["status"],
        "payment_status": row["payment_status"],
        "total_amount": float(row["total_amount"]),
        "currency": row["currency"],
        "eta_minutes": row["eta_minutes"],
        "restaurant_name": row["restaurant_name"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


async def get_order_details(db: AsyncSession, user_id: UUID, order_code: str) -> Optional[dict]:
    """
    Fetch full order details including items. Filters by user_id.
    """
    if settings.SIMULATE_FAILURE == "orders_timeout":
        import asyncio
        raise asyncio.TimeoutError("Simulated order service timeout")
    if settings.SIMULATE_FAILURE == "db_down":
        raise ConnectionError("Simulated database unavailability")

    # Get order
    order_result = await db.execute(
        text("""
            SELECT o.id, o.order_code, o.status, o.payment_status, o.total_amount, o.currency,
                   o.eta_minutes, o.created_at, o.updated_at,
                   r.name as restaurant_name, r.address as restaurant_address
            FROM orders o
            LEFT JOIN restaurants r ON r.id = o.restaurant_id
            WHERE o.order_code = :order_code AND o.user_id = :user_id
        """),
        {"order_code": order_code, "user_id": str(user_id)},
    )
    order_row = order_result.mappings().first()
    if not order_row:
        return None

    # Get items
    items_result = await db.execute(
        text("""
            SELECT item_name, quantity, price
            FROM order_items
            WHERE order_id = :order_id
            ORDER BY item_name
        """),
        {"order_id": str(order_row["id"])},
    )
    items = [
        {"item_name": r["item_name"], "quantity": r["quantity"], "price": float(r["price"])}
        for r in items_result.mappings()
    ]

    return {
        "order_code": order_row["order_code"],
        "status": order_row["status"],
        "payment_status": order_row["payment_status"],
        "total_amount": float(order_row["total_amount"]),
        "currency": order_row["currency"],
        "eta_minutes": order_row["eta_minutes"],
        "restaurant_name": order_row["restaurant_name"],
        "restaurant_address": order_row["restaurant_address"],
        "items": items,
        "created_at": order_row["created_at"].isoformat() if order_row["created_at"] else None,
        "updated_at": order_row["updated_at"].isoformat() if order_row["updated_at"] else None,
    }


async def get_order_by_code(db: AsyncSession, order_code: str) -> Optional[dict]:
    """
    Fetch order without user filter (internal use only, for ticket linking).
    Returns order id and user_id for ownership verification.
    """
    result = await db.execute(
        text("SELECT id, user_id, status, payment_status FROM orders WHERE order_code = :order_code"),
        {"order_code": order_code},
    )
    row = result.mappings().first()
    if not row:
        return None
    return {
        "id": str(row["id"]),
        "user_id": str(row["user_id"]),
        "status": row["status"],
        "payment_status": row["payment_status"],
    }
