# Architecture

See [README.md](../README.md) for the full architecture diagram and responsibility split.

## Key Design Decisions

### 1. Agent Loop vs LangGraph
We use a hand-written bounded loop for simplicity and explainability. The loop maps cleanly to LangGraph nodes if needed:
- `guard` → `llm` → `tools` → `llm` → ... → `finalize`
- Conditional edge on "has tool calls"
- Recursion limit = `MAX_TOOL_CALLS`

### 2. Local OrderClient by Default
The brief's failure scenario is "the order API is unavailable." We implement this with a configurable `OrderClient`:
- `ORDER_CLIENT=local` (default): Direct DB access, fewer moving parts
- `ORDER_CLIENT=http`: HTTP calls to REST endpoints, useful for outage simulation

### 3. Priority Rules in Code
The LLM produces a `ComplaintAnalysis` with an urgency field, but final priority is computed by deterministic rules in `app/workflows/rules.py`. Rules can raise priority but the model can never lower a rule-based HIGH.

### 4. RLS as Defense in Depth
The FastAPI backend uses a service-role connection that bypasses RLS. Application-side authorization (ownership-filtered queries, server-injected `user_id`) is the primary defense. RLS protects direct Supabase client access.

### 5. Idempotent Ticket Creation
`INSERT ... ON CONFLICT (idempotency_key) DO NOTHING` ensures safe retries. The idempotency key is `sha256(user_id|order_code|category|date)`.
