# Fantasy Media 🏈📱

An always-on bot that watches your **private ESPN fantasy football league**,
detects noteworthy weekly events, and auto-generates a fake "media ecosystem"
around them — ESPN-style breaking-news alerts, parody beat-reporter tweets,
Instagram-style posts with graphics, and power-ranking cards with movement
arrows — then fires them into your league's group chat.

This is a **tier-3, fully automatic** build: it polls ESPN on a schedule and
pushes content out with no manual triggering.

---

## How it works

```
fetch ESPN state ─▶ detect events ─▶ de-dup (SQLite) ─▶ generate (Claude + Pillow) ─▶ deliver (webhook)
```

| Module | Job |
| --- | --- |
| `src/espn_client.py` | Wraps `espn-api`, returns a plain `LeagueSnapshot`. Auth vs. fetch errors are separated. |
| `src/state.py` | SQLite de-dup so an event never fires twice. |
| `src/events.py` | Detects matchup results, blowout, nailbiter, high/low scorer, transactions, ranking movement. Event keys are season-scoped, so a new season never collides with last year's de-dup history. |
| `src/storylines.py` | Persistent narrative memory for the Insider's manufactured drama — a rumor can start, escalate, or wrap up a running storyline instead of resetting every drop. Heat decays daily so old bits fade out on their own. |
| `src/generators/` | Four content types — notifications, tweets, instagram, rankings — plus `insider.py` (anonymous scoops), `reactions.py` (crowd reaction tweets/comments), and `pundits.py` (Dan Orlovsky + Stephen A. Smith reacting to every Insider drop). |
| `src/graphics/render.py` | Pillow-rendered post + power-ranking cards (easy to restyle at the top of the file). |
| `src/delivery.py` | Discord / Slack / GroupMe webhook push. |
| `src/scheduler.py` | APScheduler polling loop; a bad cycle never kills the service. |
| `src/pipeline.py` | Wires one cycle together. |
| `main.py` | Entrypoint. |

---

## Setup

### 1. Install
```bash
pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env
# then edit .env
```

`.env` is gitignored — **never commit it**. The ESPN cookies are effectively
keys to your ESPN session; they stay in `.env`, out of git, and out of logs.

| Var | What |
| --- | --- |
| `LEAGUE_ID` | From your ESPN league URL. |
| `SEASON` | `auto` (default) figures out the current fantasy season from today's date and rolls over on its own every year — set an explicit year (e.g. `2026`) only to override. |
| `ESPN_S2`, `SWID` | Auth cookies (below). |
| `ANTHROPIC_API_KEY` | For Claude text generation. |
| `WEBHOOK_PROVIDER` | `discord` \| `slack` \| `groupme`. |
| `WEBHOOK_URL` | Incoming webhook (Discord/Slack). |
| `GROUPME_BOT_ID` | GroupMe bot id (GroupMe only). |
| `TONE` | Default `hype` or `roast`; per-type overrides available. |
| `POLL_INTERVAL` | Minutes between polls. |
| `RUN_ONCE` | `true` to run one cycle and exit (handy for cron/testing). |

**Tone** is a config option: `roast` (trash-talk) or `hype` (broadcast).
Defaults are `roast` for notifications/tweets/IG and `hype` for rankings; each
is independently overridable via `TONE_NOTIFICATIONS`, `TONE_TWEETS`,
`TONE_INSTAGRAM`, `TONE_RANKINGS`.

### How to get `espn_s2` and `SWID`
1. Log into your ESPN fantasy league in a browser.
2. DevTools → Application/Storage → Cookies → the `espn.com` domain.
3. Copy `espn_s2` and `SWID` (**include the braces on `SWID`**, e.g. `{AAAA-BBBB}`).
4. Paste into `.env`.

### 3. Run
```bash
python main.py          # starts the scheduler (polls immediately, then on interval)
RUN_ONCE=true python main.py   # single cycle
```

---

## Deploy (always-on)

### Docker
```bash
docker build -t fantasy-media .
docker run --env-file .env -v $PWD/data:/app/data -v $PWD/out:/app/out fantasy-media
```
Mount `/app/data` (SQLite state + previous standings) so de-dup survives
restarts, and `/app/out` if you want to keep generated images.

### Hosting options
- **Railway / Fly.io** — push the repo, set env vars in the dashboard, deploy the
  Dockerfile. Cheapest hands-off option.
- **Small VPS** (DigitalOcean/Hetzner ~$5/mo) — `docker run` with `--restart unless-stopped`.
- **Raspberry Pi at home** — same Docker command; free if you already have one.
- **Cron instead of the built-in loop** — set `RUN_ONCE=true` and schedule
  `python main.py` (e.g. hourly on game days) via system cron.

Suggested cadence: hourly during game days, less often otherwise — tune
`POLL_INTERVAL`. Keep request volume modest; the ESPN endpoints are private and
unofficial, so be a good citizen.

---

## Known caveats (built defensively around these)

1. **`espn-api` is unofficial.** ESPN's private endpoints can change without
   notice. Every ESPN call is wrapped; a bad poll is logged and skipped, never
   crashes the scheduler.
2. **Cookies expire.** When auth fails, the bot logs a clear message *and* posts
   a heads-up to your group chat telling you to refresh `espn_s2` / `SWID`.
3. **ToS gray area.** Personal, single-league hobby tool pulling your own league.
   Low risk in practice — keep volume modest.
4. **Secrets hygiene.** Cookies live only in `.env`; never in git, logs, or output.
5. **De-duplication.** SQLite state guarantees the same event never spams twice.

---

## Tests
```bash
pip install pytest
pytest tests/ -q
```
Covers event detection and ranking-movement logic (no network needed).

---

## Restyling graphics
Open `src/graphics/render.py` — the color constants and card layouts are at the
top. Drop in a TTF via `_load_font` for sharper text, or swap Pillow for an
HTML-to-image approach if you prefer template-driven styling.
