"""Order tools - get_order_status and get_order_details."""

import time
import asyncio
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from app.tools.schemas import ToolResult, GetOrderStatusArgs, GetOrderDetailsArgs
from app.services.orders import get_order_status, get_order_details
from app.observability.logging import get_logger

logger = get_logger(__name__)


async def tool_get_order_status(args: dict, user_id: UUID, db: AsyncSession) -> ToolResult:
    """Execute get_order_status tool with validation and authorization."""
    start = time.time()

    # Validate args
    try:
        validated = GetOrderStatusArgs(**args)
    except ValidationError as e:
        return ToolResult(
            ok=False,
            error="invalid_argument",
            message=f"Invalid order code format. Please provide a valid order code like ORD-1005.",
        )

    # Execute with timeout and retry
    for attempt in range(2):
        try:
            data = await asyncio.wait_for(
                get_order_status(db, user_id, validated.order_code),
                timeout=5.0,
            )
            if data is None:
                return ToolResult(ok=False, error="not_found", message="Order not found.")

            return ToolResult(ok=True, data=data)

        except asyncio.TimeoutError:
            if attempt == 0:
                logger.warning(f"Order status timeout, retrying: {validated.order_code}")
                continue
            return ToolResult(
                ok=False,
                error="timeout",
                message="Order status is temporarily unavailable. Please try again in a moment.",
            )
        except (ConnectionError, OSError) as e:
            if attempt == 0:
                logger.warning(f"Order service error, retrying: {e}")
                continue
            return ToolResult(
                ok=False,
                error="unavailable",
                message="Order service is temporarily unavailable. Please try again later.",
            )
        except Exception as e:
            logger.error(f"Unexpected error in get_order_status: {e}")
            return ToolResult(ok=False, error="internal", message="An internal error occurred.")

    return ToolResult(ok=False, error="unavailable", message="Service unavailable after retries.")


async def tool_get_order_details(args: dict, user_id: UUID, db: AsyncSession) -> ToolResult:
    """Execute get_order_details tool with validation and authorization."""

    # Validate args
    try:
        validated = GetOrderDetailsArgs(**args)
    except ValidationError as e:
        return ToolResult(
            ok=False,
            error="invalid_argument",
            message=f"Invalid order code format. Please provide a valid order code like ORD-1005.",
        )

    # Execute with timeout and retry
    for attempt in range(2):
        try:
            data = await asyncio.wait_for(
                get_order_details(db, user_id, validated.order_code),
                timeout=5.0,
            )
            if data is None:
                return ToolResult(ok=False, error="not_found", message="Order not found.")

            return ToolResult(ok=True, data=data)

        except asyncio.TimeoutError:
            if attempt == 0:
                continue
            return ToolResult(
                ok=False,
                error="timeout",
                message="Order details are temporarily unavailable. Please try again in a moment.",
            )
        except (ConnectionError, OSError) as e:
            if attempt == 0:
                continue
            return ToolResult(
                ok=False,
                error="unavailable",
                message="Order service is temporarily unavailable.",
            )
        except Exception as e:
            logger.error(f"Unexpected error in get_order_details: {e}")
            return ToolResult(ok=False, error="internal", message="An internal error occurred.")

    return ToolResult(ok=False, error="unavailable", message="Service unavailable after retries.")
