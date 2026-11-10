create extension if not exists pgcrypto with schema extensions;

create table if not exists public.teachers (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null default 'Teacher',
  created_at timestamptz not null default now()
);

create table if not exists public.students (
  id uuid primary key default gen_random_uuid(),
  teacher_id uuid not null references public.teachers(id) on delete cascade,
  display_name text not null,
  created_at timestamptz not null default now(),
  unique (teacher_id, display_name)
);

create table if not exists public.folders (
  id uuid primary key default gen_random_uuid(),
  teacher_id uuid not null references public.teachers(id) on delete cascade,
  local_id text not null,
  name text not null,
  is_built_in boolean not null default false,
  created_at timestamptz not null default now(),
  unique (teacher_id, local_id),
  unique (teacher_id, name)
);

create table if not exists public.vocabularies (
  id uuid primary key default gen_random_uuid(),
  teacher_id uuid not null references public.teachers(id) on delete cascade,
  local_id text not null,
  folder_id uuid references public.folders(id) on delete set null,
  chinese text not null,
  pinyin text not null,
  translations jsonb not null default '{}'::jsonb,
  image jsonb,
  provenance jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (teacher_id, local_id),
  unique (teacher_id, chinese)
);

create table if not exists public.practices (
  id uuid primary key default gen_random_uuid(),
  teacher_id uuid not null references public.teachers(id) on delete cascade,
  local_id text not null,
  folder_id uuid references public.folders(id) on delete set null,
  student_id uuid references public.students(id) on delete set null,
  name text not null,
  student_name text,
  language text not null check (language in ('en', 'de', 'fr', 'es', 'it')),
  settings jsonb not null default '{}'::jsonb,
  status text not null default 'draft' check (status in ('draft', 'published', 'archived')),
  share_code text unique,
  published_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.practice_items (
  id uuid primary key default gen_random_uuid(),
  practice_id uuid not null references public.practices(id) on delete cascade,
  vocabulary_id uuid references public.vocabularies(id) on delete set null,
  position integer not null,
  snapshot jsonb not null,
  correct_answer text not null,
  unique (practice_id, position)
);

create table if not exists public.practice_sessions (
  id uuid primary key default gen_random_uuid(),
  practice_id uuid not null references public.practices(id) on delete cascade,
  student_id uuid references public.students(id) on delete set null,
  student_name text not null,
  started_at timestamptz not null default now(),
  completed_at timestamptz
);

create table if not exists public.answers (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.practice_sessions(id) on delete cascade,
  practice_item_id uuid not null references public.practice_items(id) on delete cascade,
  selected_answer text not null,
  display_answer text,
  is_correct boolean not null,
  answered_at timestamptz not null default now(),
  unique (session_id, practice_item_id)
);

create table if not exists public.practice_results (
  id uuid primary key default gen_random_uuid(),
  practice_id uuid not null references public.practices(id) on delete cascade,
  session_id uuid not null unique references public.practice_sessions(id) on delete cascade,
  student_id uuid references public.students(id) on delete set null,
  student_name text not null,
  started_at timestamptz not null,
  completed_at timestamptz not null,
  score integer not null,
  max_score integer not null,
  accuracy numeric(5, 2) not null,
  stars integer not null,
  created_at timestamptz not null default now()
);

create index if not exists practices_teacher_folder_idx on public.practices (teacher_id, folder_id, updated_at desc);
create index if not exists practices_share_code_idx on public.practices (share_code) where status = 'published';
create index if not exists results_teacher_practice_idx on public.practice_results (practice_id, completed_at desc);

alter table public.teachers enable row level security;
alter table public.students enable row level security;
alter table public.folders enable row level security;
alter table public.vocabularies enable row level security;
alter table public.practices enable row level security;
alter table public.practice_items enable row level security;
alter table public.practice_sessions enable row level security;
alter table public.answers enable row level security;
alter table public.practice_results enable row level security;

create policy "teachers manage own profile" on public.teachers for all to authenticated using (id = auth.uid()) with check (id = auth.uid());
create policy "teachers manage own students" on public.students for all to authenticated using (teacher_id = auth.uid()) with check (teacher_id = auth.uid());
create policy "teachers read own folders" on public.folders for select to authenticated using (teacher_id = auth.uid());
create policy "teachers insert own folders" on public.folders for insert to authenticated with check (teacher_id = auth.uid());
create policy "teachers update custom folders" on public.folders for update to authenticated using (teacher_id = auth.uid() and not is_built_in) with check (teacher_id = auth.uid() and not is_built_in);
create policy "teachers delete custom folders" on public.folders for delete to authenticated using (teacher_id = auth.uid() and not is_built_in);
create policy "teachers manage own vocabulary" on public.vocabularies for all to authenticated using (teacher_id = auth.uid()) with check (teacher_id = auth.uid());
create policy "teachers manage own practices" on public.practices for all to authenticated using (teacher_id = auth.uid()) with check (teacher_id = auth.uid());
create policy "teachers read own practice items" on public.practice_items for select to authenticated using (exists (select 1 from public.practices p where p.id = practice_id and p.teacher_id = auth.uid()));
create policy "teachers insert draft practice items" on public.practice_items for insert to authenticated with check (exists (select 1 from public.practices p where p.id = practice_id and p.teacher_id = auth.uid() and p.status = 'draft'));
create policy "teachers update draft practice items" on public.practice_items for update to authenticated using (exists (select 1 from public.practices p where p.id = practice_id and p.teacher_id = auth.uid() and p.status = 'draft')) with check (exists (select 1 from public.practices p where p.id = practice_id and p.teacher_id = auth.uid() and p.status = 'draft'));
create policy "teachers delete draft practice items" on public.practice_items for delete to authenticated using (exists (select 1 from public.practices p where p.id = practice_id and p.teacher_id = auth.uid() and p.status = 'draft'));
create policy "teachers view own sessions" on public.practice_sessions for select to authenticated using (exists (select 1 from public.practices p where p.id = practice_id and p.teacher_id = auth.uid()));
create policy "teachers view own answers" on public.answers for select to authenticated using (exists (select 1 from public.practice_sessions s join public.practices p on p.id = s.practice_id where s.id = session_id and p.teacher_id = auth.uid()));
create policy "teachers view own results" on public.practice_results for select to authenticated using (exists (select 1 from public.practices p where p.id = practice_id and p.teacher_id = auth.uid()));

create or replace function public.get_published_practice(input_share_code text)
returns jsonb
language sql
security definer
set search_path = public
as $$
  select jsonb_build_object(
    'id', p.id,
    'shareCode', p.share_code,
    'name', p.name,
    'teacherName', t.display_name,
    'language', p.language,
    'settings', p.settings,
    'items', coalesce((
      select jsonb_agg(jsonb_build_object('id', i.id, 'word', i.snapshot - 'answer' - 'position') order by i.position)
      from public.practice_items i where i.practice_id = p.id
    ), '[]'::jsonb)
  )
  from public.practices p
  join public.teachers t on t.id = p.teacher_id
  where p.share_code = input_share_code and p.status = 'published'
  limit 1;
$$;

create or replace function public.start_practice_attempt(input_share_code text, input_student_name text)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  selected_practice public.practices%rowtype;
  new_session_id uuid;
  new_student_id uuid;
begin
  if length(trim(input_student_name)) not between 1 and 80 then
    raise exception 'Please enter a name between 1 and 80 characters.';
  end if;
  select * into selected_practice from public.practices where share_code = input_share_code and status = 'published';
  if not found then raise exception 'This practice is unavailable.'; end if;
  insert into public.students (teacher_id, display_name)
  values (selected_practice.teacher_id, trim(input_student_name))
  on conflict (teacher_id, display_name) do update set display_name = excluded.display_name
  returning id into new_student_id;
  insert into public.practice_sessions (practice_id, student_id, student_name)
  values (selected_practice.id, new_student_id, trim(input_student_name)) returning id into new_session_id;
  return new_session_id;
end;
$$;

create or replace function public.submit_practice_attempt(input_attempt_id uuid, input_answers jsonb)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  attempt public.practice_sessions%rowtype;
  total_count integer;
  submitted_count integer;
  correct_count integer := 0;
  star_count integer := 0;
  correct_streak integer := 0;
  answer_row record;
  is_answer_correct boolean;
  final_score integer;
  final_accuracy numeric(5, 2);
  end_time timestamptz := now();
  wrong_items jsonb;
begin
  select * into attempt from public.practice_sessions where id = input_attempt_id for update;
  if not found or attempt.completed_at is not null then raise exception 'Attempt is unavailable or already submitted.'; end if;
  select count(*) into total_count from public.practice_items where practice_id = attempt.practice_id;
  if total_count = 0 then raise exception 'Practice has no vocabulary items.'; end if;

  for answer_row in
    select value ->> 'itemId' as item_id, value ->> 'answer' as selected_answer, value ->> 'displayAnswer' as display_answer, ordinality
    from jsonb_array_elements(coalesce(input_answers, '[]'::jsonb)) with ordinality
    order by ordinality
  loop
    if exists (select 1 from public.answers a where a.session_id = attempt.id and a.practice_item_id = answer_row.item_id::uuid) then
      continue;
    end if;
    select (i.correct_answer = answer_row.selected_answer) into is_answer_correct
    from public.practice_items i where i.id = answer_row.item_id::uuid and i.practice_id = attempt.practice_id;
    if not found then continue; end if;
    insert into public.answers (session_id, practice_item_id, selected_answer, display_answer, is_correct)
    values (attempt.id, answer_row.item_id::uuid, coalesce(answer_row.selected_answer, ''), coalesce(answer_row.display_answer, ''), coalesce(is_answer_correct, false))
    on conflict (session_id, practice_item_id) do nothing;
    if is_answer_correct then
      correct_count := correct_count + 1;
      correct_streak := correct_streak + 1;
      star_count := star_count + 1;
      if correct_streak = 3 then star_count := star_count + 1; end if;
      if correct_streak = 5 then star_count := star_count + 2; end if;
    else
      correct_streak := 0;
    end if;
  end loop;

  select count(*) into submitted_count from public.answers where session_id = attempt.id;
  if submitted_count <> total_count then raise exception 'Please submit an answer for every practice item.'; end if;
  final_score := correct_count * 10;
  final_accuracy := round((correct_count::numeric * 100) / total_count, 2);
  star_count := star_count + 3;
  select coalesce(jsonb_agg(jsonb_build_object(
    'chinese', i.snapshot ->> 'chinese',
    'pinyin', i.snapshot ->> 'pinyin',
    'translation', i.snapshot -> 'translations',
    'selected', coalesce(a.display_answer, a.selected_answer)
  ) order by i.position), '[]'::jsonb) into wrong_items
  from public.answers a join public.practice_items i on i.id = a.practice_item_id
  where a.session_id = attempt.id and not a.is_correct;

  update public.practice_sessions set completed_at = end_time where id = attempt.id;
  insert into public.practice_results (practice_id, session_id, student_id, student_name, started_at, completed_at, score, max_score, accuracy, stars)
  values (attempt.practice_id, attempt.id, attempt.student_id, attempt.student_name, attempt.started_at, end_time, final_score, total_count * 10, final_accuracy, star_count);
  return jsonb_build_object('score', final_score, 'maxScore', total_count * 10, 'accuracy', final_accuracy, 'stars', star_count, 'incorrect', wrong_items, 'startTime', attempt.started_at, 'endTime', end_time);
end;
$$;

grant execute on function public.get_published_practice(text) to anon, authenticated;
grant execute on function public.start_practice_attempt(text, text) to anon, authenticated;
grant execute on function public.submit_practice_attempt(uuid, jsonb) to anon, authenticated;