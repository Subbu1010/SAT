-- Enable extension
create extension if not exists vector;

-- Core users table (app metadata, independent from auth.users)
create table if not exists public.users (
  user_id uuid primary key references auth.users(id) on delete cascade,
  first_name text not null,
  last_name text not null,
  email text unique not null,
  role text not null check (role in ('admin','teacher','student')),
  is_disabled boolean not null default false,
  created_at timestamptz not null default now(),
  last_login timestamptz
);

create table if not exists public.student_profiles (
  profile_id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(user_id) on delete cascade,
  grade text,
  target_score int,
  created_at timestamptz not null default now()
);

create table if not exists public.questions (
  question_id uuid primary key default gen_random_uuid(),
  exam_type text not null check (exam_type in ('SAT','PSAT','PSAT 8/9')),
  subject text not null check (subject in ('Math','Reading','Writing')),
  topic text not null,
  difficulty text not null check (difficulty in ('Easy','Medium','Hard')),
  skill_category text,
  question_text text not null,
  passage text,
  options jsonb not null,
  answer text not null,
  explanation text not null,
  strategy_tip text,
  estimated_time int default 60,
  source text,
  created_at timestamptz not null default now()
);

create table if not exists public.practice_attempts (
  attempt_id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(user_id) on delete cascade,
  question_id uuid not null references public.questions(question_id) on delete cascade,
  selected_answer text not null,
  is_correct boolean not null,
  time_spent int,
  flagged boolean not null default false,
  saved_for_later boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists public.mock_exams (
  exam_id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(user_id) on delete cascade,
  score int not null,
  accuracy numeric(5,2) not null,
  duration int not null,
  subject_breakdown jsonb,
  topic_breakdown jsonb,
  completed_at timestamptz not null default now()
);

create table if not exists public.ai_conversations (
  conversation_id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(user_id) on delete cascade,
  question_id uuid references public.questions(question_id),
  prompt text not null,
  response text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.performance_analytics (
  analytics_id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(user_id) on delete cascade,
  topic text not null,
  accuracy numeric(5,2) not null,
  total_attempts int not null default 0,
  last_updated timestamptz not null default now()
);

-- Security audit log for login, logout, failed, and disabled auth events.
-- ip_address: client IP (or "localhost" in local dev).
-- location: approximate city/region/country from IP geolocation.
-- status: success | failed | logout | disabled
create table if not exists public.login_history (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.users(user_id),
  email text,
  ip_address text,
  location text,
  status text not null,
  created_at timestamptz not null default now()
);

-- Student-reported answer disputes for third-party question imports.
create table if not exists public.answer_disputes (
  dispute_id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(user_id) on delete cascade,
  question_id uuid not null references public.questions(question_id) on delete cascade,
  selected_answer text not null,
  stored_answer text not null,
  proposed_answer text not null,
  reason text not null,
  status text not null default 'pending'
    check (status in ('pending','accepted','rejected')),
  admin_notes text,
  reviewed_by uuid references public.users(user_id),
  reviewed_at timestamptz,
  created_at timestamptz not null default now()
);

create unique index if not exists idx_answer_disputes_pending_user_question
  on public.answer_disputes (user_id, question_id)
  where status = 'pending';

create table if not exists public.embeddings (
  id uuid primary key default gen_random_uuid(),
  content text not null,
  content_type text not null,
  source text,
  metadata jsonb,
  embedding vector(768) not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_embeddings_hnsw on public.embeddings using hnsw (embedding vector_cosine_ops);

create or replace function public.match_embeddings(
  query_embedding vector(768),
  match_count int default 5
)
returns table (
  id uuid,
  content text,
  content_type text,
  source text,
  similarity float
)
language sql
as $$
  select
    e.id,
    e.content,
    e.content_type,
    e.source,
    1 - (e.embedding <=> query_embedding) as similarity
  from public.embeddings e
  order by e.embedding <=> query_embedding
  limit match_count;
$$;

-- RLS
alter table public.users enable row level security;
alter table public.student_profiles enable row level security;
alter table public.practice_attempts enable row level security;
alter table public.mock_exams enable row level security;
alter table public.ai_conversations enable row level security;
alter table public.performance_analytics enable row level security;
alter table public.login_history enable row level security;
alter table public.answer_disputes enable row level security;

-- Login history: only service role (admin app) should read/write via SUPABASE_SECRET_KEY.
-- No client policies = anon/authenticated users cannot access directly.

do $$ begin
  create policy "students_own_user_profile"
  on public.users for select using (auth.uid() = user_id);
exception when duplicate_object then null;
end $$;

do $$ begin
  create policy "students_own_profiles"
  on public.student_profiles for all using (auth.uid() = user_id);
exception when duplicate_object then null;
end $$;

do $$ begin
  create policy "students_own_attempts"
  on public.practice_attempts for all using (auth.uid() = user_id);
exception when duplicate_object then null;
end $$;

do $$ begin
  create policy "students_own_mock_exams"
  on public.mock_exams for all using (auth.uid() = user_id);
exception when duplicate_object then null;
end $$;

do $$ begin
  create policy "students_own_ai_conversations"
  on public.ai_conversations for all using (auth.uid() = user_id);
exception when duplicate_object then null;
end $$;

do $$ begin
  create policy "students_own_analytics"
  on public.performance_analytics for all using (auth.uid() = user_id);
exception when duplicate_object then null;
end $$;

do $$ begin
  create policy "students_own_disputes"
  on public.answer_disputes for all using (auth.uid() = user_id);
exception when duplicate_object then null;
end $$;

-- ---------------------------------------------------------------------------
-- Incremental upgrades for databases created before a column was added.
-- Safe to re-run. See app/database/migrations/ for the same statements.
-- ---------------------------------------------------------------------------
alter table public.login_history add column if not exists location text;
