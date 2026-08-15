-- ============================================================================
-- Fantasy Media — schema migration v5
-- Web Push subscriptions: lets the bot notify installed/subscribed devices
-- when new posts land. No auth (matches v4's public model) — anyone with the
-- anon key can register a device, but only the service role can read the
-- table back, so subscriptions can't be enumerated or scraped.
-- ============================================================================

create table if not exists public.push_subscriptions (
  id uuid primary key default gen_random_uuid(),
  league_id uuid not null references public.leagues(id) on delete cascade,
  endpoint text not null unique,
  p256dh text not null,
  auth text not null,
  created_at timestamptz not null default now()
);

alter table public.push_subscriptions enable row level security;

-- No select policy: the anon key can register/update a subscription but
-- can't read the table. The bot uses the service role key, which bypasses
-- RLS entirely.
drop policy if exists push_subscriptions_insert on public.push_subscriptions;
create policy push_subscriptions_insert on public.push_subscriptions
  for insert with check (true);

drop policy if exists push_subscriptions_update on public.push_subscriptions;
create policy push_subscriptions_update on public.push_subscriptions
  for update using (true) with check (true);
