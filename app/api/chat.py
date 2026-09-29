"""Chat API endpoint - main agent interface."""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, AuthContext
from app.database import get_db
from app.agent.loop import run_agent

router = APIRouter(prefix="/api/agent", tags=["Agent"])


class ChatRequest(BaseModel):
    """Incoming chat message."""
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None


class ChatResponseModel(BaseModel):
    """Chat response schema."""
    session_id: str
    answer: str
    authoritative_data: dict = {}
    sources: list = []
    tools_used: list = []
    trace_id: Optional[str] = None


@router.post("/chat", response_model=ChatResponseModel)
async def chat(
    request: ChatRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Main chat endpoint. Processes user messages through the agent loop.
    User identity is resolved from auth headers, never from the message.
    """
    session_id = request.session_id or f"s-{uuid.uuid4().hex[:12]}"

    try:
        response = await run_agent(
            user_msg=request.message,
            session_id=session_id,
            user_id=auth.user_id,
            db=db,
        )
        return ChatResponseModel(**response.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")
