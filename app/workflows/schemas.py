"""Pydantic schemas for complaint analysis structured output."""

from pydantic import BaseModel, Field
from typing import Optional, Literal


class ComplaintAnalysis(BaseModel):
    """LLM-produced structured analysis of a customer complaint."""

    category: Literal["PAYMENT", "ORDER", "DELIVERY", "REFUND", "TECHNICAL", "OTHER"]
    sentiment: Literal["NEGATIVE", "NEUTRAL", "POSITIVE"]
    urgency: Literal["LOW", "MEDIUM", "HIGH"]
    summary: str = Field(max_length=300)
    order_code: Optional[str] = Field(default=None, pattern=r"^ORD-\d{4,6}$")
    needs_human: bool = False
