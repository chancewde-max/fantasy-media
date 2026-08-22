-- ============================================================================
-- Fantasy Media — schema migration v8
-- Lets real fans comment on posts. Run AFTER schema.sql + v2-v7.
--
-- comments_write (schema.sql) still requires auth.uid() = user_id, but the
-- app has no sign-in wall (v4 opened everything else up) — so today no real
-- fan can ever post a comment; only the backend's AI fan comments land.
-- Same fix shape as v7's push-subscription RPC: a SECURITY DEFINER function
-- that performs the insert server-side, so no broad "anyone can write
-- comments" RLS policy is needed and the anon key still can't do anything
-- but call this one narrow function.
-- ============================================================================

create or replace function public.post_fan_comment(
  p_post_id uuid,
  p_handle  text,
  p_body    text
) returns void
language sql
security definer
set search_path = public
as $$
  insert into public.comments (post_id, author_handle, body, is_ai)
  select
    p_post_id,
    left(coalesce(nullif(trim(p_handle), ''), '@fan'), 30),
    left(trim(p_body), 500),
    false
  where length(trim(coalesce(p_body, ''))) > 0
    and exists (select 1 from public.posts where id = p_post_id);
$$;

revoke all on function public.post_fan_comment(uuid, text, text) from public;
grant execute on function public.post_fan_comment(uuid, text, text) to anon, authenticated;
