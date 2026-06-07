-- Answer dispute reports from students (practice questions).
-- Safe to re-run.

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

alter table public.answer_disputes enable row level security;

do $$ begin
  create policy "students_own_disputes"
  on public.answer_disputes for all using (auth.uid() = user_id);
exception when duplicate_object then null;
end $$;
