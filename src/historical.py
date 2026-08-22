"""Feed backfill / retrofit.

Rebuilds the feed from the authoritative ESPN export (league_history) using the
current graphics engine — champion cards, playoff-moment breaking graphics,
final-standings boards, plus current-season storylines (reigning champ,
rivalry previews). Everything is backdated to when it happened and published
through the same SupabaseWriter, with stable event_keys so re-running is
idempotent.

Bumping BACKFILL_VERSION changes the event_key namespace, so a new retrofit
publishes fresh posts instead of colliding with an older run.
"""
from __future__ import annotations

import itertools
import logging
import os

from . import league_history, lore
from .generators.claude_client import ClaudeClient
from .generators.instagram import SYSTEM as INSTAGRAM_SYSTEM
from .generators.notifications import SYSTEM as NOTIFICATION_SYSTEM
from .generators.reactions import generate_fan_comments
from .graphics import html_render, logos, players, templates
from .graphics.render import (
    render_champion_card,
    render_gameday_matchup,
    render_post_card,
    render_power_rankings,
    render_record_card,
)
from .supabase_writer import SupabaseError, SupabaseWriter

log = logging.getLogger(__name__)

OUT_DIR = "out"
BACKFILL_VERSION = "v3"


def _graphic(html: str, name: str, fallback) -> str:
    """Render via the HTML engine; if that fails, use the Pillow fallback so a
    graphic post is never left without an image."""
    path = html_render.render_html(html, os.path.join(OUT_DIR, f"{name}.png"))
    if path:
        return path
    try:
        return fallback()
    except Exception as exc:  # noqa: BLE001
        log.warning("Pillow fallback failed for %s: %s", name, exc)
        return None


def _logo(team: str):
    try:
        return logos.logo_data_uri(team)
    except Exception:  # noqa: BLE001
        return None


def _hero(team: str):
    try:
        return players.hero_for_team(team)[0]
    except Exception:  # noqa: BLE001
        return None


def run_backfill(claude: ClaudeClient, supabase: SupabaseWriter, tone: str = "roast") -> None:
    for year in league_history.completed_years():
        _publish_season(claude, supabase, year, tone)
    _publish_current_storylines(claude, supabase, tone)
    log.info("Feed backfill complete.")


def _publish_season(claude: ClaudeClient, supabase: SupabaseWriter, year: int, tone: str) -> None:
    summary = league_history.season_summary(year)
    if not summary:
        return
    champ = summary["champion"]
    jan = f"{year + 1}-01-05T21:00:00+00:00"

    # Champion card
    facts = f"{champ} won the {year} league championship"
    if summary["runner_up"]:
        facts += f", beating {summary['runner_up']} {summary['champ_score']}".rstrip()
    caption = claude.generate(INSTAGRAM_SYSTEM, f"{facts}. Write the caption.", tone, max_tokens=200)
    sub = (f"def. {summary['runner_up']} {summary['champ_score']}").strip()
    html = templates.record_html(
        f"{year} CHAMPION", champ, sub, champ, ghost=str(year), logo=_logo(champ), hero=_hero(champ),
    )
    img = _graphic(html, f"hist_{year}_champ",
                   lambda: render_champion_card(OUT_DIR, f"hist_{year}_champ", f"{year} SEASON",
                                                champ, summary["champ_score"]))
    _publish(claude, supabase, "instagram", caption, "@LeagueGram",
             event_key=f"hist:{BACKFILL_VERSION}:{year}:champ", when=jan, tone=tone, image_path=img)

    # Playoff moments -> breaking graphics
    for i, fact in enumerate(league_history.playoff_facts().get(year, [])):
        team = league_history.detect_team(fact) or champ
        cap = claude.generate(NOTIFICATION_SYSTEM, f"{fact} Write the alert.", tone, max_tokens=160)
        headline = _short(fact)
        bhtml = templates.breaking_html(headline, team=team, logo=_logo(team), hero=_hero(team))
        bimg = _graphic(bhtml, f"hist_{year}_po{i}",
                        lambda h=headline: render_post_card(OUT_DIR, f"hist_{year}_po{i}", h, "THE INSIDER"))
        _publish(claude, supabase, "instagram", cap, "@LeagueGram",
                 event_key=f"hist:{BACKFILL_VERSION}:{year}:po{i}",
                 when=f"{year}-12-22T20:0{i}:00+00:00", tone=tone, image_path=bimg,
                 with_fan_comments=False)

    # Final standings board
    rows = summary["standings"]
    if rows:
        sfacts = f"{year} final standings: " + ", ".join(
            f"{r['rank']}. {r['team']} ({r['wins']}-{r['losses']})" for r in rows)
        scap = claude.generate(INSTAGRAM_SYSTEM, f"{sfacts} Write the caption.", tone, max_tokens=200)
        simg = render_power_rankings(OUT_DIR, f"hist_{year}_standings",
                                     title="FINAL STANDINGS", subtitle=f"{year} SEASON",
                                     rows=rows, show_arrows=False)
        _publish(claude, supabase, "instagram", scap, "@LeagueGram",
                 event_key=f"hist:{BACKFILL_VERSION}:{year}:standings",
                 when=f"{year + 1}-01-06T12:00:00+00:00", tone=tone, image_path=simg)


def _publish_current_storylines(claude: ClaudeClient, supabase: SupabaseWriter, tone: str) -> None:
    year = league_history.current_year()

    # Reigning champ record card
    years = league_history.completed_years()
    if years:
        last = years[-1]
        champ_last = league_history.season_summary(last)["champion"]
        # follow to their current-year team name
        fn = lore._owner_for(champ_last, last)
        cur_team = league_history.owner_teams().get(fn, {}).get(year, champ_last) if fn else champ_last
        chips = league_history.manager_profiles().get(fn, {}).get("championships", []) if fn else []
        big = f"{len(chips)}x Champ" if len(chips) > 1 else "Reigning Champ"
        cap = claude.generate(INSTAGRAM_SYSTEM,
                              f"{cur_team} enters {year} as the reigning champ. Write hype.", tone, max_tokens=180)
        html = templates.record_html(f"{year} SEASON", big, f"{cur_team} runs it back",
                                     cur_team, ghost=(f"{len(chips)}x" if len(chips) > 1 else str(last)),
                                     logo=_logo(cur_team), hero=_hero(cur_team))
        img = _graphic(html, f"hist_{year}_reigning",
                       lambda: render_record_card(OUT_DIR, f"hist_{year}_reigning", f"{year} SEASON",
                                                  big, f"{cur_team} runs it back"))
        _publish(claude, supabase, "instagram", cap, "@LeagueGram",
                 event_key=f"hist:{BACKFILL_VERSION}:{year}:reigning",
                 when=f"{year}-08-20T18:00:00+00:00", tone=tone, image_path=img)

    # Top rivalry previews
    for i, (a_team, b_team, note) in enumerate(_top_rivalries(year, n=2)):
        cap = claude.generate(INSTAGRAM_SYSTEM,
                              f"Preseason rivalry: {a_team} vs {b_team}. {note} Write hype.", tone, max_tokens=180)
        html = templates.matchup_html(
            a_team, b_team, league_history.team_tagline(a_team), league_history.team_tagline(b_team),
            f"{year} RIVALRY", note, logo_a=_logo(a_team), logo_b=_logo(b_team),
            hero_a=_hero(a_team), hero_b=_hero(b_team),
        )
        img = _graphic(html, f"hist_{year}_rivalry{i}",
                       lambda a=a_team, b=b_team, nt=note: render_gameday_matchup(
                           OUT_DIR, f"hist_{year}_rivalry{i}", a, b,
                           sub_a=league_history.team_tagline(a), sub_b=league_history.team_tagline(b),
                           week_label=f"{year} RIVALRY", lore=nt))
        _publish(claude, supabase, "instagram", cap, "@LeagueGram",
                 event_key=f"hist:{BACKFILL_VERSION}:{year}:rivalry{i}",
                 when=f"{year}-08-21T18:0{i}:00+00:00", tone=tone, image_path=img)


def _top_rivalries(year: int, n: int = 2) -> list[tuple[str, str, str]]:
    """Pick the juiciest current-team rivalries by games played, as
    (team_a, team_b, note)."""
    owners = [o for o in league_history.owner_teams() if league_history.owner_teams()[o].get(year)]
    scored = []
    for a, b in itertools.combinations(owners, 2):
        h2h = lore.head_to_head(a, b)
        if len(h2h["games"]) >= 3:
            note = lore.rivalry_note(a, b) or ""
            ta = league_history.owner_teams()[a][year]
            tb = league_history.owner_teams()[b][year]
            scored.append((len(h2h["games"]), abs(h2h["wins"] - h2h["losses"]), ta, tb, note))
    # most games, then closest series
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [(ta, tb, note) for _, _, ta, tb, note in scored[:n]]


def _short(text: str, words: int = 9) -> str:
    parts = text.replace("In the", "").split()
    return " ".join(parts[:words]).rstrip(",.") if len(parts) > words else text.rstrip(".")


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
            for c in generate_fan_comments(claude, body, tone, n=2):
                supabase.insert_fan_comment(post_id, c["handle"], c["text"], created_at=when)
        except Exception as exc:  # noqa: BLE001
            log.warning("Fan comments failed for %s: %s", event_key, exc)
