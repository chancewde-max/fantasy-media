"""Historical season backfill.

Turns real past-season standings + playoff results into the same kind of
AI-generated posts the live pipeline produces — ESPN alerts, tweets, and
Instagram-style recaps with real rendered graphics — backdated to when those
games actually happened, and published through the same SupabaseWriter (real
Storage image uploads, not a manual one-off).

Run via `python backfill_history.py` (see repo root), not imported by the
normal polling pipeline.
"""
from __future__ import annotations

import logging

from .generators.claude_client import ClaudeClient
from .generators.instagram import SYSTEM as INSTAGRAM_SYSTEM
from .generators.notifications import SYSTEM as NOTIFICATION_SYSTEM
from .generators.reactions import generate_fan_comments
from .generators.tweets import SYSTEM as TWEET_SYSTEM
from .graphics.render import render_champion_card, render_standings_card
from .supabase_writer import SupabaseError, SupabaseWriter

log = logging.getLogger(__name__)

OUT_DIR = "out"

SEASONS = [
    {
        "year": 2024,
        "standings": [
            {"rank": 1, "team": "Njiqbas in Paris", "wins": 8, "losses": 5},
            {"rank": 2, "team": "Need More Beers", "wins": 7, "losses": 5},
            {"rank": 3, "team": "Meat on Meat", "wins": 5, "losses": 7},
            {"rank": 4, "team": "The Juice is Loose in Hell", "wins": 6, "losses": 7},
            {"rank": 5, "team": "Team of Collusion", "wins": 9, "losses": 4},
            {"rank": 6, "team": "Jabawockeez", "wins": 5, "losses": 7},
            {"rank": 7, "team": "Tha Hoodie Gang", "wins": 8, "losses": 5},
            {"rank": 8, "team": "Garren's Great Team", "wins": 8, "losses": 5},
            {"rank": 9, "team": "B50Beast", "wins": 5, "losses": 8},
            {"rank": 10, "team": "White Diggs", "wins": 4, "losses": 9},
            {"rank": 11, "team": "Patrick's Team", "wins": 5, "losses": 8},
        ],
        "standings_when": "2025-01-06T12:00:00+00:00",
        "champion": "Njiqbas in Paris",
        "runner_up": "Need More Beers",
        "champ_score": "249.28 - 232.56",
        "champ_when": "2025-01-05T21:00:00+00:00",
        "games": [
            {
                "key": "r1_upset", "when": "2024-12-22T20:05:00+00:00",
                "facts": "Round 1 of the 2024 playoffs: #8 seed MEAT ON MEAT "
                         "upset #1 seed Team of Collusion, 148.24 to 102.50.",
                "notable": "upset",
            },
            {
                "key": "r1_juice", "when": "2024-12-22T21:00:00+00:00",
                "facts": "Round 1 of the 2024 playoffs: The Juice Is Loose In "
                         "Hell beat Garren's Great Team 156.48 to 93.70.",
                "notable": None,
            },
            {
                "key": "r2_nmb", "when": "2024-12-29T20:00:00+00:00",
                "facts": "Round 2 of the 2024 playoffs: Need More Beers beat "
                         "MEAT ON MEAT 172.94 to 160.22 to reach the championship.",
                "notable": None,
            },
            {
                "key": "r2_njiqbas", "when": "2024-12-29T20:30:00+00:00",
                "facts": "Round 2 of the 2024 playoffs: Njiqbas in Paris "
                         "eliminated The Juice Is Loose In Hell 132.74 to 110.16 "
                         "to reach the championship.",
                "notable": None,
            },
        ],
    },
    {
        "year": 2025,
        "standings": [
            {"rank": 1, "team": "So Good That It Hurts", "wins": 9, "losses": 5},
            {"rank": 2, "team": "Flaccid Winners", "wins": 9, "losses": 5},
            {"rank": 3, "team": "Need More Beers", "wins": 9, "losses": 5},
            {"rank": 4, "team": "The Flee The Scenes", "wins": 9, "losses": 5},
            {"rank": 5, "team": "Tha Hoodie Gang", "wins": 8, "losses": 6},
            {"rank": 6, "team": "B50Beast", "wins": 6, "losses": 8},
            {"rank": 7, "team": "Jabawockeez", "wins": 8, "losses": 6},
            {"rank": 8, "team": "Patrick's Team", "wins": 5, "losses": 9},
            {"rank": 9, "team": "Team of Collusion", "wins": 2, "losses": 12},
            {"rank": 10, "team": "I Chase White Women", "wins": 5, "losses": 9},
        ],
        "standings_when": "2026-01-05T12:00:00+00:00",
        "champion": "So Good That It Hurts",
        "runner_up": "Flaccid Winners",
        "champ_score": "257.42 - 212.70",
        "champ_when": "2026-01-04T21:00:00+00:00",
        "games": [
            {
                "key": "r1_nailbiter", "when": "2025-12-21T20:00:00+00:00",
                "facts": "Round 1 of the 2025 playoffs: So Good That It Hurts "
                         "barely survived B50Beast, 156.90 to 154.86 — decided "
                         "by about 2 points.",
                "notable": "nailbiter",
            },
            {
                "key": "r1_flee", "when": "2025-12-21T21:00:00+00:00",
                "facts": "Round 1 of the 2025 playoffs: The Flee The Scenes beat "
                         "Jabawockeez 159.70 to 142.88.",
                "notable": None,
            },
            {
                "key": "r2_upset", "when": "2025-12-28T20:00:00+00:00",
                "facts": "Round 2 of the 2025 playoffs: Flaccid Winners upset "
                         "#1 seed Need More Beers 150.30 to 135.80, knocking out "
                         "the top seed.",
                "notable": "upset",
            },
            {
                "key": "r2_sgtih", "when": "2025-12-28T20:30:00+00:00",
                "facts": "Round 2 of the 2025 playoffs: So Good That It Hurts "
                         "blew past The Flee The Scenes 136.50 to 91.08 to reach "
                         "the championship.",
                "notable": None,
            },
        ],
    },
]

COMMISSIONER_NOTE = {
    "when": "2026-08-14T23:00:00+00:00",
    "quote": "Welcome to the 2026 season. Juan's squad is still dawgshit, famo!",
}


def run_backfill(claude: ClaudeClient, supabase: SupabaseWriter, tone: str = "roast") -> None:
    for season in SEASONS:
        _publish_season(claude, supabase, season, tone)
    _publish_commissioner_note(claude, supabase)
    log.info("Historical backfill complete.")


def _publish_season(claude: ClaudeClient, supabase: SupabaseWriter, season: dict, tone: str) -> None:
    year = season["year"]

    for game in season["games"]:
        note = claude.generate(
            NOTIFICATION_SYSTEM, f"{game['facts']} Write the alert.", tone, max_tokens=160,
        )
        _publish(
            claude, supabase, "espn_notification", note, "ESPN",
            event_key=f"hist:{year}:{game['key']}:note", when=game["when"], tone=tone,
        )
        if game["notable"]:
            tweet = claude.generate(
                TWEET_SYSTEM, f"{game['facts']} Write the tweet.", tone, max_tokens=180,
            )
            _publish(
                claude, supabase, "tweet", tweet, "@degen_danny",
                event_key=f"hist:{year}:{game['key']}:tweet", when=game["when"], tone=tone,
                with_fan_comments=False,
            )

    champ_facts = (
        f"{season['champion']} won the {year} league championship, beating "
        f"{season['runner_up']} {season['champ_score']} in the title game."
    )
    champ_alert = claude.generate(
        NOTIFICATION_SYSTEM, f"{champ_facts} Write the alert.", tone, max_tokens=160,
    )
    _publish(
        claude, supabase, "espn_notification", champ_alert, "ESPN",
        event_key=f"hist:{year}:champ:alert", when=season["champ_when"], tone=tone,
    )

    champ_caption = claude.generate(
        INSTAGRAM_SYSTEM, f"{champ_facts} Write the caption.", tone, max_tokens=200,
    )
    champ_image = render_champion_card(
        OUT_DIR, f"hist_champ_{year}", f"{year} SEASON", season["champion"], season["champ_score"],
    )
    _publish(
        claude, supabase, "instagram", champ_caption, "@LeagueGram",
        event_key=f"hist:{year}:champ:ig", when=season["champ_when"], tone=tone, image_path=champ_image,
    )

    standings_lines = ", ".join(
        f"{r['rank']}. {r['team']} ({r['wins']}-{r['losses']})" for r in season["standings"]
    )
    standings_facts = f"{year} final standings, in order: {standings_lines}."
    standings_caption = claude.generate(
        INSTAGRAM_SYSTEM, f"{standings_facts} Write the caption.", tone, max_tokens=200,
    )
    standings_image = render_standings_card(
        OUT_DIR, f"hist_standings_{year}", f"{year} SEASON", season["standings"],
    )
    _publish(
        claude, supabase, "instagram", standings_caption, "@LeagueGram",
        event_key=f"hist:{year}:standings:ig", when=season["standings_when"], tone=tone,
        image_path=standings_image,
    )


def _publish_commissioner_note(claude: ClaudeClient, supabase: SupabaseWriter) -> None:
    body = (
        f"\U0001F4CC Commissioner's note for the 2026 season: "
        f"\"{COMMISSIONER_NOTE['quote']}\" Some things never change."
    )
    _publish(
        claude, supabase, "espn_notification", body, "Commissioner",
        event_key="hist:2026:commish_note", when=COMMISSIONER_NOTE["when"], tone="roast",
        with_fan_comments=False,
    )


def _publish(
    claude: ClaudeClient, supabase: SupabaseWriter, post_type: str, body: str, author_handle: str,
    event_key: str, when: str, tone: str, image_path: str | None = None, with_fan_comments: bool = True,
) -> None:
    try:
        post_id = supabase.insert_post(
            post_type=post_type, body=body, author_handle=author_handle,
            image_path=image_path, event_key=event_key,
            metadata={"historical": True}, created_at=when,
        )
    except SupabaseError as exc:
        log.error("Failed to publish %s: %s", event_key, exc)
        return

    if post_id is None:
        log.info("Skipping %s (already published).", event_key)
        return

    if with_fan_comments:
        try:
            comments = generate_fan_comments(claude, body, tone, n=2)
            for c in comments:
                supabase.insert_fan_comment(post_id, c["handle"], c["text"], created_at=when)
        except Exception as exc:  # noqa: BLE001
            log.warning("Fan comments failed for %s: %s", event_key, exc)
