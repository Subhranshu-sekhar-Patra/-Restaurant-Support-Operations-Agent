-- Restaurant Support & Operations Agent: Database Schema
-- Runs on both Supabase Postgres and local Docker Postgres

create extension if not exists vector;
create extension if not exists pgcrypto;

-- Customers. In jwt mode, id equals the Supabase auth user id.
create table if not exists profiles (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  email       text unique,
  role        text not null default 'CUSTOMER' check (role in ('CUSTOMER','SUPPORT_AGENT','ADMIN')),
  created_at  timestamptz not null default now()
);

create table if not exists restaurants (
  id uuid primary key default gen_random_uuid(),
  name text not null, address text, phone text
);

create table if not exists orders (
  id             uuid primary key default gen_random_uuid(),
  order_code     text not null unique check (order_code ~ '^ORD-[0-9]{4,6}$'),
  user_id        uuid not null references profiles(id),
  restaurant_id  uuid references restaurants(id),
  status         text not null check (status in
                   ('PLACED','CONFIRMED','PREPARING','READY','OUT_FOR_DELIVERY','DELIVERED','CANCELLED','FAILED')),
  payment_status text not null check (payment_status in ('PENDING','PAID','FAILED','REFUNDED','DEDUCTED_NOT_CONFIRMED')),
  total_amount   numeric(10,2) not null,
  currency       text not null default 'INR',
  eta_minutes    int,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);
create index if not exists idx_orders_user_id on orders(user_id);

create table if not exists order_items (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references orders(id) on delete cascade,
  item_name text not null, quantity int not null check (quantity > 0), price numeric(10,2) not null
);

create sequence if not exists ticket_seq start 1000;

create table if not exists support_tickets (
  id              uuid primary key default gen_random_uuid(),
  ticket_code     text unique not null default ('TKT-' || nextval('ticket_seq')),
  user_id         uuid not null references profiles(id),
  order_id        uuid references orders(id),
  category        text not null check (category in ('PAYMENT','ORDER','DELIVERY','REFUND','TECHNICAL','OTHER')),
  priority        text not null check (priority in ('LOW','MEDIUM','HIGH')),
  sentiment       text not null check (sentiment in ('NEGATIVE','NEUTRAL','POSITIVE')),
  description     text not null,
  needs_human     boolean not null default false,
  idempotency_key text not null unique,
  status          text not null default 'OPEN',
  created_at      timestamptz not null default now()
);

create table if not exists conversations (
  id uuid primary key default gen_random_uuid(),
  session_id text unique not null,
  user_id uuid not null references profiles(id),
  last_order_code text,
  created_at timestamptz not null default now()
);

create table if not exists messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references conversations(id) on delete cascade,
  role text not null check (role in ('user','assistant','tool')),
  content text not null,
  created_at timestamptz not null default now()
);
create index if not exists idx_messages_conv_created on messages(conversation_id, created_at);

create table if not exists kb_documents (
  id uuid primary key default gen_random_uuid(),
  title text not null, source text not null unique,
  effective_date date not null, version int not null default 1,
  content text not null
);

create table if not exists kb_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references kb_documents(id) on delete cascade,
  section text,
  content text not null,
  embedding vector(1536) not null
);
create index if not exists idx_kb_chunks_embedding on kb_chunks using hnsw (embedding vector_cosine_ops);

create table if not exists agent_traces (
  trace_id uuid primary key default gen_random_uuid(),
  session_id text, user_id uuid,
  user_message_preview text,
  tools_called jsonb not null default '[]',
  outcome text,
  latency_ms int, created_at timestamptz not null default now()
);

create table if not exists workflow_log (
  id uuid primary key default gen_random_uuid(),
  trace_id uuid, workflow text not null,
  analysis jsonb, ticket_code text, notification jsonb,
  created_at timestamptz not null default now()
);

-- Retrieval function for RAG
create or replace function match_chunks(query_embedding vector(1536), match_count int, min_similarity float)
returns table (chunk_id uuid, content text, section text, source text,
               effective_date date, similarity float)
language sql stable as $$
  select c.id, c.content, c.section, d.source, d.effective_date,
         1 - (c.embedding <=> query_embedding) as similarity
  from kb_chunks c join kb_documents d on d.id = c.document_id
  where 1 - (c.embedding <=> query_embedding) >= min_similarity
  order by c.embedding <=> query_embedding
  limit match_count;
$$;
