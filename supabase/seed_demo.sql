-- ============================================================================
-- Fantasy Media — demo seed data
-- Inserts a handful of sample posts + fan comments so the feed shows content
-- before the live backend is running. Run in SQL Editor. Delete later with:
--   delete from public.posts where metadata->>'demo' = 'true';
-- ============================================================================

with lg as (
  select id from public.leagues order by created_at limit 1
),
ins as (
  insert into public.posts (league_id, type, author_handle, body, metadata)
  select lg.id, v.type, v.handle, v.body, '{"demo":"true"}'::jsonb
  from lg, (values
    ('espn_notification','ESPN',
     '🚨 Team Chaos drops 148.6 to bury Sofa Kings in a Week 3 blowout.'),
    ('insider_report','@LeagueInsider',
     'Sources around the league tell me a certain 1-2 team is quietly shopping their RB1. Motivated seller. 👀'),
    ('tweet','@degen_danny',
     'no way Chaos put up 148 with their kicker on bye lmaooo #rigged'),
    ('instagram','@LeagueGram',
     'HIGH SCORE OF THE WEEK 👑 148.6 — somebody check on the Sofa Kings.'),
    ('tweet','@sofaking_stan',
     'we don''t talk about week 3. rebuild starts now. 🧱')
  ) as v(type, handle, body)
  returning id, type
)
insert into public.comments (post_id, author_handle, body, is_ai)
select ins.id, c.handle, c.body, true
from ins
join (values
  ('espn_notification','@ball_dont_lie','148 is criminal 😭'),
  ('insider_report','@waiver_wire_willy','my money''s on the 1-2 team being the Kings'),
  ('instagram','@commish_cathy','framing this one 🖼️')
) as c(type, handle, body) on c.type = ins.type;
