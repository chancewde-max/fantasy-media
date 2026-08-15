-- ============================================================================
-- Fantasy Media — schema migration v4
-- Removes the sign-in wall: the feed, reactions, and tips are now fully public
-- (anon key, no auth.uid() required). Run AFTER schema.sql + v2 + v3.
-- ============================================================================

-- Reactions no longer need a real auth user behind them.
alter table public.reactions drop constraint if exists reactions_user_id_fkey;
alter table public.reactions alter column user_id drop not null;

-- Open reads to everyone (anon key), not just league members.
drop policy if exists leagues_select on public.leagues;
create policy leagues_select on public.leagues for select using (true);

drop policy if exists posts_select on public.posts;
create policy posts_select on public.posts for select using (true);

drop policy if exists comments_select on public.comments;
create policy comments_select on public.comments for select using (true);

drop policy if exists reactions_select on public.reactions;
create policy reactions_select on public.reactions for select using (true);

drop policy if exists tips_select on public.tips;
create policy tips_select on public.tips for select using (true);

-- Open the writes the (now login-free) web app makes: tips + reactions.
drop policy if exists tips_insert on public.tips;
create policy tips_insert on public.tips for insert with check (true);

drop policy if exists reactions_write on public.reactions;
create policy reactions_insert on public.reactions for insert with check (true);
