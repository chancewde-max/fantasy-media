-- ============================================================================
-- Fantasy Media — schema migration v7
-- Fixes Web Push subscribe, which failed on every device with:
--   "new row violates row-level security policy for table push_subscriptions"
--
-- push_subscriptions intentionally has no SELECT policy (the anon key can
-- register a device but must never read back the subscriber list). Any direct
-- write that returns the row — PostgREST's return=representation, which a
-- plain insert/upsert from supabase-js triggers — runs a SELECT-check against
-- RLS, finds no policy to satisfy, and the whole statement is rejected.
-- Switching to ON CONFLICT DO NOTHING did not help: the RETURNING is the part
-- that fails, not the conflict handling.
--
-- Fix: a SECURITY DEFINER function that performs the upsert server-side and
-- returns void. No representation is ever selected back, so no SELECT policy
-- is needed, and anon still cannot read the table directly.
-- ============================================================================

create or replace function public.register_push_subscription(
  p_league_id uuid,
  p_endpoint  text,
  p_p256dh    text,
  p_auth      text
) returns void
language sql
security definer
set search_path = public
as $$
  insert into public.push_subscriptions (league_id, endpoint, p256dh, auth)
  values (p_league_id, p_endpoint, p_p256dh, p_auth)
  on conflict (endpoint) do update
    set p256dh = excluded.p256dh,
        auth   = excluded.auth;
$$;

revoke all on function public.register_push_subscription(uuid, text, text, text) from public;
grant execute on function public.register_push_subscription(uuid, text, text, text) to anon, authenticated;
