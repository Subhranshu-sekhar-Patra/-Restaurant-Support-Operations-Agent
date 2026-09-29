"""Support tickets API - REST endpoint for ticket creation."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, AuthContext
from app.database import get_db
from app.workflows.complaint import run_complaint_workflow
from app.agent.llm_client import llm_client

router = APIRouter(prefix="/api/support", tags=["Support"])


class TicketRequest(BaseModel):
    """Support ticket creation request."""
    description: str = Field(..., min_length=10, max_length=1000)
    order_code: Optional[str] = Field(None, pattern=r"^ORD-\d{4,6}$")


@router.post("/tickets")
async def create_ticket(
    request: TicketRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a support ticket via REST.
    Runs the same complaint workflow as the agent tool.
    Priority is never client-supplied.
    """
    try:
        result = await run_complaint_workflow(
            db=db,
            user_id=auth.user_id,
            description=request.description,
            order_code=request.order_code,
            llm_client=llm_client,
        )
        status_code = 201 if result.get("is_new") else 200
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create support ticket")
