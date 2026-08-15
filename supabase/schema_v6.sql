-- ============================================================================
-- Fantasy Media — schema migration v6
-- Adds the "article" post type (short companion pieces following an ESPN
-- alert or Insider report). The original check constraint on posts.type
-- didn't allow it, so every article insert was silently rejected.
-- ============================================================================

alter table public.posts drop constraint if exists posts_type_check;
alter table public.posts add constraint posts_type_check check (
  type in ('espn_notification', 'tweet', 'instagram', 'insider_report', 'article')
);
