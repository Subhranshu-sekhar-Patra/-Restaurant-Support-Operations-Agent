# Failure Cases Documentation

## 1. Order Lookup Timeout / DB Unavailable
- **Detection**: `asyncio.TimeoutError` or `ConnectionError` from the database
- **Handling**: One read retry, then "Order status is temporarily unavailable. Please try again or I can create a support ticket."
- **Trace outcome**: `tool_error`
- **Key behavior**: No status is invented. The response explicitly states unavailability.
- **Simulation**: `SIMULATE_FAILURE=orders_timeout` or `SIMULATE_FAILURE=db_down`

## 2. LLM Provider Timeout/Error
- **Detection**: Exception in `LLMClient.chat()`
- **Handling**: Retry once with backoff, then fallback reply
- **Trace outcome**: `llm_error`
- **Simulation**: `SIMULATE_FAILURE=llm_down`

## 3. Invalid Structured Output
- **Detection**: `json.JSONDecodeError` or `pydantic.ValidationError` on `ComplaintAnalysis`
- **Handling**: Retry with validation error appended to prompt, then keyword-based fallback with `needs_human=True`
- **Key behavior**: Critical actions never run on unvalidated text

## 4. Tool Loop
- **Detection**: Step counter exceeds `MAX_TOOL_CALLS` (default 5)
- **Handling**: Stop, safe message, `loop_limit` trace
- **Key behavior**: Agent cannot loop infinitely

## 5. Retry Duplicates a Ticket
- **Detection**: `ON CONFLICT (idempotency_key) DO NOTHING` in SQL
- **Handling**: Existing ticket returned with its code
- **Key behavior**: Agent says "you already have ticket TKT-XXXX open for this"

## 6. KB Has No Answer
- **Detection**: No chunk above `min_similarity` threshold
- **Handling**: "That isn't covered in our documented policies. I can create a support ticket so a team member can help."

## 7. Conflicting Policy Documents
- **Detection**: Multiple sources covering the same topic in retrieval results
- **Handling**: Newest `effective_date` wins, conflict disclosed; equal dates escalate
- **Example**: FAQ says 5-day refund window, refund_policy.md says 7-day (newer)

## 8. Invalid / Foreign Order ID
- **Detection**: Regex validation failure or ownership-filtered query returns no rows
- **Handling**: Generic "not found" message (same response whether order doesn't exist or belongs to another user)
- **Key behavior**: No existence leak
