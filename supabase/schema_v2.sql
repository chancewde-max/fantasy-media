-- ============================================================================
-- Fantasy Media — schema migration v2
-- Adds AI "fan" comments (no auth user) + reaction-tweet support.
-- Run AFTER schema.sql, in Supabase Dashboard → SQL Editor. Safe to re-run.
-- ============================================================================

-- Allow AI-generated fan comments that aren't tied to a real auth user.
alter table public.comments
  alter column user_id drop not null;

alter table public.comments
  add column if not exists author_handle text;   -- e.g. "@degen_dan"

alter table public.comments
  add column if not exists is_ai boolean not null default false;

-- Reaction tweets reference the post they react to via posts.metadata->>'reacting_to'.
-- No column needed; metadata is jsonb. This index speeds "show reactions to X".
create index if not exists posts_reacting_to_idx
  on public.posts ((metadata->>'reacting_to'))
  where metadata ? 'reacting_to';

-- RLS: members already read comments on posts in their league (schema.sql).
-- AI comments have user_id = null and are covered by that same policy since it
-- keys off the post's league, not the commenter. Nothing to change.
