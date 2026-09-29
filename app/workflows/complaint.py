"""Complaint automation workflow - the heart of ticket creation."""

import json
import re
from uuid import UUID
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from app.workflows.schemas import ComplaintAnalysis
from app.workflows.rules import compute_priority
from app.services.tickets import create_ticket, compute_idempotency_key, log_workflow
from app.services.orders import get_order_by_code
from app.observability.logging import get_logger

logger = get_logger(__name__)

ANALYSIS_PROMPT = """Analyze this customer complaint and respond with a JSON object matching this exact schema:
{{
  "category": one of "PAYMENT", "ORDER", "DELIVERY", "REFUND", "TECHNICAL", "OTHER",
  "sentiment": one of "NEGATIVE", "NEUTRAL", "POSITIVE",
  "urgency": one of "LOW", "MEDIUM", "HIGH",
  "summary": "Brief summary of the issue (max 300 chars)",
  "order_code": "ORD-XXXX if mentioned, else null",
  "needs_human": true/false (whether this needs human escalation)
}}

Customer complaint: {description}

Respond ONLY with the JSON object, no markdown, no explanation."""


def keyword_fallback_classify(description: str) -> ComplaintAnalysis:
    """
    Keyword-based fallback classifier when LLM structured output fails.
    Always sets needs_human=True since we can't trust the classification.
    """
    desc_lower = description.lower()

    # Category detection
    if any(w in desc_lower for w in ["payment", "charged", "deducted", "money", "refund", "amount"]):
        category = "PAYMENT"
    elif any(w in desc_lower for w in ["deliver", "late", "waiting", "driver", "arrive", "eta"]):
        category = "DELIVERY"
    elif any(w in desc_lower for w in ["cancel", "cancelled"]):
        category = "ORDER"
    elif any(w in desc_lower for w in ["refund", "return"]):
        category = "REFUND"
    elif any(w in desc_lower for w in ["app", "bug", "error", "crash", "technical"]):
        category = "TECHNICAL"
    else:
        category = "OTHER"

    # Extract order code if present
    order_match = re.search(r"ORD-\d{4,6}", description)
    order_code = order_match.group(0) if order_match else None

    return ComplaintAnalysis(
        category=category,
        sentiment="NEGATIVE",
        urgency="MEDIUM",
        summary=description[:300],
        order_code=order_code,
        needs_human=True,
    )


async def analyze_complaint(description: str, llm_client=None) -> ComplaintAnalysis:
    """
    Use LLM to analyze complaint with structured output.
    Retry once on validation failure, then fall back to keyword classifier.
    """
    if llm_client is None:
        logger.warning("No LLM client for complaint analysis, using keyword fallback")
        return keyword_fallback_classify(description)

    prompt = ANALYSIS_PROMPT.format(description=description)

    for attempt in range(2):
        try:
            response = await llm_client.generate(prompt, json_mode=True)

            # Parse JSON from response
            text = response.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\s*\n?", "", text)
                text = re.sub(r"\n?```\s*$", "", text)

            data = json.loads(text)
            analysis = ComplaintAnalysis(**data)
            return analysis

        except (json.JSONDecodeError, ValidationError) as e:
            if attempt == 0:
                logger.warning(f"Complaint analysis attempt 1 failed: {e}, retrying with error context")
                prompt += f"\n\nYour previous response had this validation error: {str(e)}\nPlease fix it and respond with valid JSON."
                continue
            else:
                logger.warning(f"Complaint analysis failed after retry, using keyword fallback: {e}")
                return keyword_fallback_classify(description)
        except Exception as e:
            logger.error(f"LLM error during complaint analysis: {e}")
            return keyword_fallback_classify(description)

    return keyword_fallback_classify(description)


async def run_complaint_workflow(
    db: AsyncSession,
    user_id: UUID,
    description: str,
    order_code: Optional[str] = None,
    trace_id=None,
    llm_client=None,
) -> dict:
    """
    Full complaint automation workflow:
    1. LLM structured analysis
    2. Validation with retry/fallback
    3. Deterministic priority rules
    4. Order ownership check if order_code present
    5. Idempotent ticket insert
    6. Workflow log + notification stub
    """
    # Step 1-2: Analyze complaint
    analysis = await analyze_complaint(description, llm_client=llm_client)

    # Use order_code from args or from analysis
    effective_order_code = order_code or analysis.order_code

    # Step 3: Ownership check and get order context
    order_id = None
    payment_status = None
    order_status = None

    if effective_order_code:
        order_data = await get_order_by_code(db, effective_order_code)
        if order_data:
            # Verify ownership
            if order_data["user_id"] == str(user_id):
                order_id = order_data["id"]
                payment_status = order_data["payment_status"]
                order_status = order_data["status"]
            else:
                # Order exists but belongs to another user - don't link it
                logger.warning(f"Order {effective_order_code} ownership mismatch for user {user_id}")
                effective_order_code = None

    # Step 4: Deterministic priority rules
    final_priority = compute_priority(
        category=analysis.category,
        sentiment=analysis.sentiment,
        model_urgency=analysis.urgency,
        description=description,
        payment_status=payment_status,
        order_status=order_status,
    )

    # Step 5: Idempotent ticket insert
    idempotency_key = compute_idempotency_key(user_id, effective_order_code, analysis.category)

    ticket_result = await create_ticket(
        db=db,
        user_id=user_id,
        order_id=order_id,
        category=analysis.category,
        priority=final_priority,
        sentiment=analysis.sentiment,
        description=description,
        needs_human=analysis.needs_human,
        idempotency_key=idempotency_key,
    )

    # Step 6: Workflow log
    notification = {
        "type": "ticket_created" if ticket_result["is_new"] else "ticket_exists",
        "ticket_code": ticket_result["ticket_code"],
        "priority": final_priority,
        "category": analysis.category,
        "needs_human": analysis.needs_human,
    }

    await log_workflow(
        db=db,
        trace_id=trace_id,
        workflow="complaint",
        analysis=analysis.model_dump(),
        ticket_code=ticket_result["ticket_code"],
        notification=notification,
    )

    logger.info(
        f"Complaint workflow complete",
        extra={"extra_data": {
            "ticket_code": ticket_result["ticket_code"],
            "is_new": ticket_result["is_new"],
            "category": analysis.category,
            "priority": final_priority,
        }},
    )

    return {
        "ticket_code": ticket_result["ticket_code"],
        "is_new": ticket_result["is_new"],
        "category": analysis.category,
        "priority": final_priority,
        "sentiment": analysis.sentiment,
        "needs_human": analysis.needs_human,
        "status": ticket_result["status"],
    }
