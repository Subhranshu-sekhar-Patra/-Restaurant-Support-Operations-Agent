"""Orders API - REST endpoints for order data."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, AuthContext
from app.database import get_db
from app.services.orders import get_order_status, get_order_details

router = APIRouter(prefix="/api/orders", tags=["Orders"])


@router.get("/{order_code}")
async def get_order(
    order_code: str,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full order details. Ownership-filtered."""
    data = await get_order_details(db, auth.user_id, order_code)
    if not data:
        raise HTTPException(status_code=404, detail="Order not found")
    return data


@router.get("/{order_code}/status")
async def get_status(
    order_code: str,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get order status. Ownership-filtered."""
    data = await get_order_status(db, auth.user_id, order_code)
    if not data:
        raise HTTPException(status_code=404, detail="Order not found")
    return data
