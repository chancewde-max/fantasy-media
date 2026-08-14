-- ============================================================================
-- Fantasy Media — schema migration v3
-- Lets managers submit tips from the app, and turns on realtime for the feed.
-- Run AFTER schema.sql + schema_v2.sql. Safe to re-run.
-- ============================================================================

-- Members may submit tips to their own league (insert only; reads already
-- covered by tips_select in schema.sql).
drop policy if exists tips_insert on public.tips;
create policy tips_insert on public.tips
  for insert with check (public.is_league_member(league_id));

-- Realtime: let the app receive new posts/comments/reactions live.
-- (Ignore "already member of publication" errors — they mean it's done.)
do $$
begin
  begin
    alter publication supabase_realtime add table public.posts;
  exception when duplicate_object then null; end;
  begin
    alter publication supabase_realtime add table public.comments;
  exception when duplicate_object then null; end;
  begin
    alter publication supabase_realtime add table public.reactions;
  exception when duplicate_object then null; end;
end $$;
