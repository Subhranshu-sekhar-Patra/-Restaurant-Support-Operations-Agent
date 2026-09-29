-- Row Level Security (Supabase only)
-- Run AFTER schema.sql on Supabase. Do NOT run on Docker Postgres.
-- auth.uid() only exists on Supabase.

alter table profiles        enable row level security;
alter table orders          enable row level security;
alter table order_items     enable row level security;
alter table support_tickets enable row level security;
alter table conversations   enable row level security;
alter table messages        enable row level security;
alter table kb_documents    enable row level security;
alter table kb_chunks       enable row level security;

create policy profiles_self on profiles for select using (id = auth.uid());

create policy orders_owner on orders for select using (user_id = auth.uid());

create policy order_items_owner on order_items for select using (
  exists (select 1 from orders o where o.id = order_items.order_id and o.user_id = auth.uid()));

create policy tickets_owner on support_tickets for select using (user_id = auth.uid());

create policy conversations_owner on conversations for select using (user_id = auth.uid());

create policy messages_owner on messages for select using (
  exists (select 1 from conversations c where c.id = messages.conversation_id and c.user_id = auth.uid()));

-- Knowledge base is public read-only for signed-in users; writes only via backend.
create policy kb_docs_read   on kb_documents for select using (auth.role() = 'authenticated');
create policy kb_chunks_read on kb_chunks    for select using (auth.role() = 'authenticated');

-- agent_traces and workflow_log: no policies = no client access (backend only).
alter table agent_traces enable row level security;
alter table workflow_log enable row level security;
