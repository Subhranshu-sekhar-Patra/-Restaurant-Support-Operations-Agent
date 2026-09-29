"""Agent loop - the core bounded tool-calling loop."""

import json
import time
from uuid import UUID
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.llm_client import LLMClient, LLMError, llm_client
from app.agent.memory import load_history, save_message, remember_order
from app.tools.schemas import TOOL_SCHEMAS
from app.tools.registry import dispatch_tool
from app.security.guardrails import guard_input, InputGuardError
from app.security.redact import redact_secrets
from app.observability.tracing import TraceContext, persist_trace
from app.observability.logging import get_logger

logger = get_logger(__name__)


class ChatResponse:
    """Structured response from the agent."""

    def __init__(
        self,
        session_id: str,
        answer: str,
        authoritative_data: Optional[dict] = None,
        sources: Optional[list] = None,
        tools_used: Optional[list] = None,
        trace_id: Optional[str] = None,
    ):
        self.session_id = session_id
        self.answer = answer
        self.authoritative_data = authoritative_data or {}
        self.sources = sources or []
        self.tools_used = tools_used or []
        self.trace_id = trace_id

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "answer": self.answer,
            "authoritative_data": self.authoritative_data,
            "sources": self.sources,
            "tools_used": self.tools_used,
            "trace_id": self.trace_id,
        }


def _fallback_response(reason: str, session_id: str, trace: TraceContext) -> ChatResponse:
    """Generate a fallback response when something goes wrong."""
    messages = {
        "llm_error": "I'm having trouble processing your request right now. Please try again in a moment, or I can create a support ticket if you need immediate help.",
        "loop_limit": "I've been working on your request but couldn't complete it. Could you try rephrasing your question?",
        "input_guard": "I can't help with that request. I'm here to assist with your restaurant orders, policies, and support tickets.",
    }
    trace.outcome = reason
    return ChatResponse(
        session_id=session_id,
        answer=messages.get(reason, messages["llm_error"]),
        trace_id=str(trace.trace_id),
    )


async def run_agent(
    user_msg: str,
    session_id: str,
    user_id: UUID,
    db: AsyncSession,
    client: Optional[LLMClient] = None,
) -> ChatResponse:
    """
    Main agent loop with bounded tool calls.

    Flow:
    1. Guard input
    2. Load conversation history
    3. LLM call with tool schemas
    4. If tool calls: validate -> authorize -> execute -> loop
    5. If text response: finalize
    """
    trace = TraceContext(session_id=session_id, user_id=user_id)
    trace.user_message_preview = user_msg[:200] if user_msg else ""
    client = client or llm_client

    # Step 1: Input guardrails
    try:
        guard_input(user_msg)
    except InputGuardError as e:
        trace.outcome = "refused"
        await persist_trace(db, trace)
        return ChatResponse(
            session_id=session_id,
            answer=e.message,
            trace_id=str(trace.trace_id),
        )

    # Step 2: Load history
    conv_id, history, last_order_code = await load_history(db, session_id, user_id)

    # Build message list
    messages = history + [{"role": "user", "content": user_msg}]

    # If the user has a remembered order and the message seems like a follow-up
    if last_order_code and not any(
        kw in user_msg.lower() for kw in ["ord-", "order code", "new order"]
    ):
        # Inject context about the last order for follow-up questions
        follow_up_hint = f"\n[System context: The customer's most recently discussed order is {last_order_code}. Use this if the question seems like a follow-up about a previous order.]"
        messages[-1]["content"] = user_msg + follow_up_hint

    # Save user message
    await save_message(db, conv_id, "user", user_msg)

    tool_log = []
    authoritative_data = {}
    sources = []

    # Step 3-4: Bounded agent loop
    for step in range(settings.MAX_TOOL_CALLS + 1):
        # LLM call with retry
        for attempt in range(2):
            try:
                resp = await client.chat(
                    SYSTEM_PROMPT,
                    messages,
                    TOOL_SCHEMAS,
                    timeout=settings.LLM_TIMEOUT_S,
                )
                break
            except LLMError as e:
                if attempt == 0:
                    logger.warning(f"LLM error, retrying: {e}")
                    continue
                await persist_trace(db, trace)
                return _fallback_response("llm_error", session_id, trace)
        else:
            await persist_trace(db, trace)
            return _fallback_response("llm_error", session_id, trace)

        # No tool calls -> finalize
        if not resp.tool_calls:
            answer = redact_secrets(resp.text or "I'm sorry, I couldn't generate a response. Please try again.")

            # Save assistant message and trace
            await save_message(db, conv_id, "assistant", answer)
            trace.outcome = "ok"
            await persist_trace(db, trace)

            return ChatResponse(
                session_id=session_id,
                answer=answer,
                authoritative_data=authoritative_data,
                sources=sources,
                tools_used=tool_log,
                trace_id=str(trace.trace_id),
            )

        # Loop limit check
        if step == settings.MAX_TOOL_CALLS:
            await persist_trace(db, trace)
            return _fallback_response("loop_limit", session_id, trace)

        # Process tool calls
        for call in resp.tool_calls:
            start_time = time.time()

            result = await dispatch_tool(
                tool_name=call.name,
                args=call.arguments,
                user_id=user_id,
                db=db,
                trace_id=trace.trace_id,
                llm_client=client,
            )

            latency_ms = int((time.time() - start_time) * 1000)
            trace.add_tool_call(call.name, result.ok, result.error, latency_ms)
            tool_log.append({"name": call.name, "ok": result.ok})

            # Track authoritative data from order tools
            if result.ok and call.name.startswith("get_order"):
                authoritative_data[call.name] = result.data
                if result.data and "order_code" in result.data:
                    await remember_order(db, session_id, result.data["order_code"])

            # Track sources from policy search
            if result.ok and call.name == "search_policy" and result.data:
                policy_sources = result.data.get("sources", [])
                sources.extend(policy_sources)

            # Build messages for the LLM
            # Assistant message with tool call
            messages.append({
                "role": "assistant",
                "content": "",
                "tool_calls": [{"name": call.name, "arguments": call.arguments}],
            })

            # Tool result message
            result_content = json.dumps(result.model_dump(), default=str)
            messages.append({
                "role": "tool",
                "tool_name": call.name,
                "content": result_content,
            })

    # Should not reach here
    await persist_trace(db, trace)
    return _fallback_response("loop_limit", session_id, trace)
