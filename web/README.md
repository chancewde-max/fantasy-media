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
Sign-in is a Supabase **magic link** (passwordless). On first sign-in the app
adds you to the league so row-level security lets you read the feed. Invite
league-mates by having them sign in with their email.

## Before it looks alive
Run these once in the Supabase SQL Editor (in order):
`supabase/schema.sql` → `schema_v2.sql` → `schema_v3.sql` → `seed_demo.sql`
(the last one drops in sample posts so the feed isn't empty).
