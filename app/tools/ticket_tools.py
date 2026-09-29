"""Ticket creation tool - runs the complaint automation workflow."""

from uuid import UUID
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.schemas import ToolResult, CreateSupportTicketArgs
from app.workflows.complaint import run_complaint_workflow
from app.observability.logging import get_logger

logger = get_logger(__name__)


async def tool_create_support_ticket(
    args: dict,
    user_id: UUID,
    db: AsyncSession,
    trace_id=None,
    llm_client=None,
) -> ToolResult:
    """
    Create a support ticket by running the full complaint workflow.
    The LLM never supplies category, sentiment, or priority.
    Those are produced by the workflow's analysis + deterministic rules.
    """
    # Validate args
    try:
        validated = CreateSupportTicketArgs(**args)
    except ValidationError as e:
        return ToolResult(
            ok=False,
            error="invalid_argument",
            message="Please describe the issue (10-1000 characters) and optionally include the order code.",
        )

    try:
        result = await run_complaint_workflow(
            db=db,
            user_id=user_id,
            description=validated.description,
            order_code=validated.order_code,
            trace_id=trace_id,
            llm_client=llm_client,
        )
        return ToolResult(ok=True, data=result)

    except Exception as e:
        logger.error(f"Ticket creation error: {e}")
        return ToolResult(
            ok=False,
            error="internal",
            message="Failed to create support ticket. Please try again or contact support directly.",
        )
