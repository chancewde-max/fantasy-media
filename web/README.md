# Fantasy Media — web app

Mobile-first feed (Vite + React) that reads your league's Supabase feed:
ESPN-style alerts, tweets, Instagram posts, and Insider reports — with fan
comments and reactions. Plus a **Submit a Tip** tab (anonymous, in-app —
no Twilio).

## Run locally
```bash
cd web
cp .env.example .env.local     # fill in your anon key
npm install
npm run dev                     # http://localhost:5173
```

`.env.local` values (all public/anon — safe in the browser, RLS protects data):
- `VITE_SUPABASE_URL` — your project URL
- `VITE_SUPABASE_ANON_KEY` — Settings → API → anon public key
- `VITE_LEAGUE_ID` — your league row id

## Deploy to Vercel (recommended)
1. Push to GitHub (done).
2. vercel.com → **New Project** → import `chancewde-max/fantasy-media`.
3. Set **Root Directory** to `web`.
4. Framework preset: **Vite** (auto-detected). Build: `npm run build`, output `dist`.
5. Add the three `VITE_*` env vars in the Vercel dashboard.
6. Deploy → open the URL on your phone → **Add to Home Screen** for an app feel.

## Auth
There isn't any. The feed, reactions, tip form, and comments are open to
anyone with the link — no sign-in screen, no email. Row-level security still
protects writes to tables the app doesn't touch (e.g. `memberships`), but
reads and the writes the app makes (tips, reactions, comments) are public.
Reactions aren't deduped per-person since there's no login to key them on —
every tap adds one. Comments get a lightweight per-device handle (stored in
`localStorage`, editable by tapping it in the composer) so a person's
comments look consistent across visits — not a real identity, same trust
level as tips and reactions.

## Before it looks alive
Run these once in the Supabase SQL Editor, in order: `schema.sql` →
`schema_v2.sql` → `schema_v3.sql` → `schema_v4.sql` → `schema_v5.sql` →
`schema_v6.sql` → `schema_v7.sql` → `schema_v8.sql` → `seed_demo.sql` (the
last one drops in sample posts so the feed isn't empty). `schema_v8.sql` is
required for the comment composer to work — without it, comment writes are
silently rejected by RLS.
