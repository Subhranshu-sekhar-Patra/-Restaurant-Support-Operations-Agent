"""Pydantic schemas for tool arguments and results."""

from pydantic import BaseModel, Field
from typing import Optional, Literal
import re


class ToolResult(BaseModel):
    """Universal tool result envelope."""
    ok: bool
    data: Optional[dict] = None
    error: Optional[Literal["invalid_argument", "not_found", "unavailable", "timeout", "forbidden", "internal"]] = None
    message: Optional[str] = None


class GetOrderStatusArgs(BaseModel):
    """Arguments for get_order_status tool."""
    order_code: str = Field(..., pattern=r"^ORD-\d{4,6}$", description="Order code like ORD-1005")


class GetOrderDetailsArgs(BaseModel):
    """Arguments for get_order_details tool."""
    order_code: str = Field(..., pattern=r"^ORD-\d{4,6}$", description="Order code like ORD-1005")


class CreateSupportTicketArgs(BaseModel):
    """Arguments for create_support_ticket tool."""
    description: str = Field(..., min_length=10, max_length=1000, description="Description of the issue")
    order_code: Optional[str] = Field(None, pattern=r"^ORD-\d{4,6}$", description="Related order code if applicable")


class SearchPolicyArgs(BaseModel):
    """Arguments for search_policy tool."""
    query: str = Field(..., min_length=3, max_length=500, description="Search query for policy documents")


# Tool schemas for the LLM (function calling format)
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "Get the current status of a customer's order. Use when the user asks about their order status, tracking, or delivery ETA.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_code": {
                        "type": "string",
                        "description": "The order code (format: ORD-XXXX, e.g. ORD-1005)",
                        "pattern": "^ORD-\\d{4,6}$",
                    }
                },
                "required": ["order_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_details",
            "description": "Get full details of a customer's order including items, prices, restaurant, and payment status. Use when the user asks what's in their order or about specific items.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_code": {
                        "type": "string",
                        "description": "The order code (format: ORD-XXXX, e.g. ORD-1005)",
                        "pattern": "^ORD-\\d{4,6}$",
                    }
                },
                "required": ["order_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_support_ticket",
            "description": "Create a support ticket for a customer complaint or issue. Use when the user reports a problem like payment issues, delivery problems, wrong items, or any complaint that needs follow-up.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Detailed description of the customer's issue or complaint",
                    },
                    "order_code": {
                        "type": "string",
                        "description": "The related order code if applicable (format: ORD-XXXX)",
                        "pattern": "^ORD-\\d{4,6}$",
                    },
                },
                "required": ["description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_policy",
            "description": "Search the knowledge base for restaurant policies, FAQs, cancellation rules, refund policies, delivery information, and other operational guidelines. Use when the user asks about policies, procedures, or general information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query about a policy or FAQ topic",
                    }
                },
                "required": ["query"],
            },
        },
    },
]
