"""Tool registry - fixed dispatcher for all agent tools."""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.schemas import ToolResult
from app.tools.order_tools import tool_get_order_status, tool_get_order_details
from app.tools.ticket_tools import tool_create_support_ticket
from app.tools.policy_tools import tool_search_policy
from app.observability.logging import get_logger

logger = get_logger(__name__)

# Fixed registry - unknown tool names are rejected
TOOL_REGISTRY = {
    "get_order_status": tool_get_order_status,
    "get_order_details": tool_get_order_details,
    "create_support_ticket": tool_create_support_ticket,
    "search_policy": tool_search_policy,
}


async def dispatch_tool(
    tool_name: str,
    args: dict,
    user_id: UUID,
    db: AsyncSession,
    trace_id=None,
    llm_client=None,
    embedder=None,
) -> ToolResult:
    """
    Dispatch a tool call to the appropriate handler.
    Unknown tool names are rejected outright.
    """
    if tool_name not in TOOL_REGISTRY:
        logger.warning(f"Unknown tool requested: {tool_name}")
        return ToolResult(
            ok=False,
            error="invalid_argument",
            message=f"Unknown tool '{tool_name}'. Available tools: {', '.join(TOOL_REGISTRY.keys())}",
        )

    handler = TOOL_REGISTRY[tool_name]

    # Route to the correct handler with appropriate arguments
    if tool_name in ("get_order_status", "get_order_details"):
        return await handler(args, user_id, db)
    elif tool_name == "create_support_ticket":
        return await handler(args, user_id, db, trace_id=trace_id, llm_client=llm_client)
    elif tool_name == "search_policy":
        return await handler(args, db=db, embedder=embedder)

    return ToolResult(ok=False, error="internal", message="Tool dispatch error")
