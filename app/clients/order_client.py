"""OrderClient interface - local by default, HTTP optional."""

from typing import Protocol
from uuid import UUID

from app.tools.schemas import ToolResult


class OrderClient(Protocol):
    """Interface for order data access."""
    async def get_status(self, user_id: UUID, order_code: str) -> ToolResult: ...
    async def get_details(self, user_id: UUID, order_code: str) -> ToolResult: ...


class LocalOrderClient:
    """
    Default: calls the service layer / DB directly.
    Fewer moving parts, no self-calling HTTP.
    """

    def __init__(self, db_session_factory):
        self._db_factory = db_session_factory

    async def get_status(self, user_id: UUID, order_code: str) -> ToolResult:
        from app.services.orders import get_order_status

        async with self._db_factory() as db:
            data = await get_order_status(db, user_id, order_code)
            if data is None:
                return ToolResult(ok=False, error="not_found", message="Order not found.")
            return ToolResult(ok=True, data=data)

    async def get_details(self, user_id: UUID, order_code: str) -> ToolResult:
        from app.services.orders import get_order_details

        async with self._db_factory() as db:
            data = await get_order_details(db, user_id, order_code)
            if data is None:
                return ToolResult(ok=False, error="not_found", message="Order not found.")
            return ToolResult(ok=True, data=data)


class HttpOrderClient:
    """
    Optional: calls /api/orders/... with httpx.
    Useful for demonstrating "order API unavailable" scenario.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self._base_url = base_url

    async def get_status(self, user_id: UUID, order_code: str) -> ToolResult:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self._base_url}/api/orders/{order_code}/status",
                    headers={"X-Demo-User": "alice"},  # Would need real auth forwarding
                )
                if resp.status_code == 404:
                    return ToolResult(ok=False, error="not_found", message="Order not found.")
                resp.raise_for_status()
                return ToolResult(ok=True, data=resp.json())
        except httpx.TimeoutException:
            return ToolResult(ok=False, error="timeout", message="Order service timeout.")
        except httpx.HTTPError:
            return ToolResult(ok=False, error="unavailable", message="Order service unavailable.")

    async def get_details(self, user_id: UUID, order_code: str) -> ToolResult:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self._base_url}/api/orders/{order_code}",
                    headers={"X-Demo-User": "alice"},
                )
                if resp.status_code == 404:
                    return ToolResult(ok=False, error="not_found", message="Order not found.")
                resp.raise_for_status()
                return ToolResult(ok=True, data=resp.json())
        except httpx.TimeoutException:
            return ToolResult(ok=False, error="timeout", message="Order service timeout.")
        except httpx.HTTPError:
            return ToolResult(ok=False, error="unavailable", message="Order service unavailable.")
