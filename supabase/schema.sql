-- ============================================================================
-- Fantasy League Media — Supabase schema
-- Paste into Supabase Dashboard → SQL Editor → New query → Run.
-- Safe to re-run: uses IF NOT EXISTS / CREATE OR REPLACE throughout.
--
-- Design notes:
--   * Every content row carries league_id → private now, multi-league later
--     with zero rearchitecting.
--   * Row-Level Security (RLS) so a manager only sees their own league(s).
--   * The Python backend writes with the SERVICE ROLE key, which bypasses RLS.
--     The mobile web app reads/writes with the ANON key, which RLS enforces.
-- ============================================================================

-- gen_random_uuid() is built into Postgres 13+, no extension needed.

-- ---------------------------------------------------------------------------
-- LEAGUES
-- ---------------------------------------------------------------------------
create table if not exists public.leagues (
  id             uuid primary key default gen_random_uuid(),
  name           text not null,
  espn_league_id text,                       -- e.g. "537837235"
  season         int,                        -- e.g. 2026
  created_at     timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- MEMBERSHIPS  (which auth user belongs to which league; supports multi-league)
-- ---------------------------------------------------------------------------
create table if not exists public.memberships (
  id           uuid primary key default gen_random_uuid(),
  league_id    uuid not null references public.leagues(id) on delete cascade,
  user_id      uuid not null references auth.users(id) on delete cascade,
  display_name text,
  team_name    text,
  is_admin     boolean not null default false,
  created_at   timestamptz not null default now(),
  unique (league_id, user_id)
);
create index if not exists memberships_user_idx  on public.memberships(user_id);
create index if not exists memberships_league_idx on public.memberships(league_id);

-- ---------------------------------------------------------------------------
-- POSTS  (the feed: espn_notification | tweet | instagram | insider_report)
-- ---------------------------------------------------------------------------
create table if not exists public.posts (
  id           uuid primary key default gen_random_uuid(),
  league_id    uuid not null references public.leagues(id) on delete cascade,
  type         text not null check (type in
                 ('espn_notification','tweet','instagram','insider_report')),
  author_handle text,                        -- e.g. "@LeagueInsider", "ESPN"
  body         text not null,
  image_url    text,                         -- Supabase Storage URL, nullable
  event_key    text,                         -- de-dup key from the engine
  metadata     jsonb not null default '{}',  -- scores, week, arrows, etc.
  created_at   timestamptz not null default now()
);
create index if not exists posts_league_created_idx on public.posts(league_id, created_at desc);
-- Prevent the engine from posting the same detected event twice per league.
create unique index if not exists posts_league_eventkey_uidx
  on public.posts(league_id, event_key) where event_key is not null;

-- ---------------------------------------------------------------------------
-- REACTIONS  (❤️ 🔥 😂 … one row per user+post+emoji)
-- ---------------------------------------------------------------------------
create table if not exists public.reactions (
  id         uuid primary key default gen_random_uuid(),
  post_id    uuid not null references public.posts(id) on delete cascade,
  user_id    uuid not null references auth.users(id) on delete cascade,
  emoji      text not null,
  created_at timestamptz not null default now(),
  unique (post_id, user_id, emoji)
);
create index if not exists reactions_post_idx on public.reactions(post_id);

-- ---------------------------------------------------------------------------
-- COMMENTS
-- ---------------------------------------------------------------------------
create table if not exists public.comments (
  id         uuid primary key default gen_random_uuid(),
  post_id    uuid not null references public.posts(id) on delete cascade,
  user_id    uuid not null references auth.users(id) on delete cascade,
  body       text not null,
  created_at timestamptz not null default now()
);
create index if not exists comments_post_idx on public.comments(post_id, created_at);

-- ---------------------------------------------------------------------------
-- TIPS  (managers text the Insider; backend turns pending → published post)
-- ---------------------------------------------------------------------------
create table if not exists public.tips (
  id           uuid primary key default gen_random_uuid(),
  league_id    uuid not null references public.leagues(id) on delete cascade,
  raw_text     text not null,                -- what the manager texted in
  source_phone text,                         -- Twilio 'From' (kept private)
  status       text not null default 'pending'
                 check (status in ('pending','published','rejected')),
  post_id      uuid references public.posts(id) on delete set null,
  created_at   timestamptz not null default now()
);
create index if not exists tips_league_status_idx on public.tips(league_id, status);

-- ============================================================================
-- ROW-LEVEL SECURITY
-- Members can read/write within leagues they belong to. The service-role key
-- (used by the Python backend) bypasses all of this automatically.
-- ============================================================================
alter table public.leagues     enable row level security;
alter table public.memberships enable row level security;
alter table public.posts       enable row level security;
alter table public.reactions   enable row level security;
alter table public.comments    enable row level security;
alter table public.tips        enable row level security;

-- Helper: is the current user a member of this league?
create or replace function public.is_league_member(target uuid)
returns boolean
language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.memberships m
    where m.league_id = target and m.user_id = auth.uid()
  );
$$;

-- LEAGUES: a member can see their league.
drop policy if exists leagues_select on public.leagues;
create policy leagues_select on public.leagues
  for select using (public.is_league_member(id));

-- MEMBERSHIPS: you can see rows for leagues you're in; you can insert yourself.
drop policy if exists memberships_select on public.memberships;
create policy memberships_select on public.memberships
  for select using (public.is_league_member(league_id));
drop policy if exists memberships_insert_self on public.memberships;
create policy memberships_insert_self on public.memberships
  for insert with check (user_id = auth.uid());

-- POSTS: members read; posts are written by the backend (service role).
drop policy if exists posts_select on public.posts;
create policy posts_select on public.posts
  for select using (public.is_league_member(league_id));

-- REACTIONS: members read all in their league; write only their own.
drop policy if exists reactions_select on public.reactions;
create policy reactions_select on public.reactions
  for select using (exists (
    select 1 from public.posts p
    where p.id = post_id and public.is_league_member(p.league_id)));
drop policy if exists reactions_write on public.reactions;
create policy reactions_write on public.reactions
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- COMMENTS: members read; write only their own.
drop policy if exists comments_select on public.comments;
create policy comments_select on public.comments
  for select using (exists (
    select 1 from public.posts p
    where p.id = post_id and public.is_league_member(p.league_id)));
drop policy if exists comments_write on public.comments;
create policy comments_write on public.comments
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- TIPS: members may read published/their-league tips (source_phone stays
-- server-side in practice). Inserts come from the backend (Twilio webhook).
drop policy if exists tips_select on public.tips;
create policy tips_select on public.tips
  for select using (public.is_league_member(league_id));

-- ============================================================================
-- SEED: your league row. Grab the printed id to put in the backend config.
-- ============================================================================
insert into public.leagues (name, espn_league_id, season)
values ('My League', '537837235', 2026)
on conflict do nothing;

select id, name, espn_league_id, season from public.leagues;
