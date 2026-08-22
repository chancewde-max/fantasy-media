"""Turn league events into real 'sports app' graphic posts.

Each function returns {"caption", "image_path"} (plus "gif_url" where a
reaction GIF fits). These sit alongside the existing tweet/instagram
generators but produce purpose-built graphics — gameday posters, final-score
scoreboards, stat-leader cards, record/milestone cards, and memes — so the
feed reads like a media outlet, not three canned tweets per event.
"""
from __future__ import annotations

from .. import gifs, league_history
from ..events import Event
from ..graphics.render import (
    render_final_score,
    render_gameday_matchup,
    render_meme,
    render_record_card,
    render_stat_leader,
)
from .claude_client import ClaudeClient

_CAPTION_SYSTEM = (
    "You write short, punchy social captions for a fantasy football league's "
    "media account — like a real sports page, not a corny bot. 1-2 lines, at "
    "most a couple emojis and a hashtag or two. The details may include real "
    "league 'lore' (records, rivalries, championships); work it in only when "
    "it fits, like someone who actually follows this league. No real NFL "
    "player or team names."
)


def _caption(claude: ClaudeClient, prompt: str, tone: str) -> str:
    return claude.generate(_CAPTION_SYSTEM, prompt, tone, max_tokens=160)


def _week_label(data: dict) -> str:
    w = data.get("week")
    return f"Week {w}" if w else ""


def gameday_post(claude: ClaudeClient, event: Event, tone: str, out_dir: str) -> dict:
    """Game-of-the-week matchup poster."""
    d = event.data
    a, b = d.get("team_a", ""), d.get("team_b", "")
    lore = d.get("lore") or league_history.league_brief([a, b])
    image_path = render_gameday_matchup(
        out_dir, f"gameday_{event.key}", a, b,
        sub_a=league_history.team_tagline(a),
        sub_b=league_history.team_tagline(b),
        week_label=_week_label(d),
        lore=(d.get("lore") or ""),
    )
    caption = _caption(
        claude,
        f"Game of the Week: {a} vs {b}. Lore: {lore or 'none'}. Write a hype caption.",
        tone,
    )
    return {"caption": caption, "image_path": image_path}


def _badge_for(kind: str, margin: float | None) -> str:
    if kind == "nailbiter":
        return "Nailbiter"
    if kind == "blowout":
        return "Blowout"
    if margin is not None and margin >= 40:
        return "Blowout"
    if margin is not None and margin <= 6:
        return "Nailbiter"
    return ""


def final_score_post(claude: ClaudeClient, event: Event, tone: str, out_dir: str) -> dict:
    """Post-game scoreboard graphic for a finished matchup / blowout."""
    d = event.data
    winner, loser = d.get("winner", ""), d.get("loser", "")
    w_score = d.get("winner_score")
    l_score = d.get("loser_score")
    margin = d.get("margin")
    # blowout events carry only the margin; recover the loser score from it.
    if w_score is None and margin is not None:
        w_score, l_score = margin, 0.0
    image_path = render_final_score(
        out_dir, f"final_{event.key}", winner, float(w_score or 0),
        loser, float(l_score or 0), badge=_badge_for(event.kind, margin),
    )
    caption = _caption(
        claude,
        f"Final: {winner} beat {loser} {w_score}-{l_score} (margin {margin}). "
        "Write a scoreboard caption.",
        tone,
    )
    return {"caption": caption, "image_path": image_path, "gif_url": gifs.search_gif(f"{event.kind} win celebration")}


def stat_leader_post(claude: ClaudeClient, event: Event, tone: str, out_dir: str) -> dict:
    """High/low scorer of the week as a stat-leader card."""
    d = event.data
    team = d.get("team", "")
    score = d.get("score", "")
    is_high = event.kind == "high"
    kicker = "Team of the Week" if is_high else "Low of the Week"
    label = "points" if is_high else "points (yikes)"
    image_path = render_stat_leader(
        out_dir, f"stat_{event.key}", kicker, team, f"{score:g}" if isinstance(score, (int, float)) else score, label,
        sub=league_history.team_tagline(team),
    )
    verb = "torched the league" if is_high else "face-planted"
    caption = _caption(
        claude,
        f"{team} {verb} with {score} points in Week {d.get('week')}. Write a caption.",
        tone,
    )
    return {"caption": caption, "image_path": image_path}


def record_post(out_dir: str, key: str, kicker: str, big_line: str, sub: str = "") -> dict:
    """A record / milestone graphic (caption is the big line itself)."""
    image_path = render_record_card(out_dir, f"record_{key}", kicker, big_line, sub)
    return {"caption": f"{big_line} — {sub}".strip(" —"), "image_path": image_path}


def meme_post(claude: ClaudeClient, context: str, tone: str, out_dir: str, key: str) -> dict:
    """An original league meme: Claude writes top/bottom impact text about the
    situation, rendered as a meme card."""
    data = claude.generate_json(
        (
            "You write ORIGINAL fantasy-football league memes in classic "
            "top-text / bottom-text impact format. Short, punchy, funny, "
            "roasting the team not the person, no slurs, no real NFL names. "
            'Respond as JSON: {"top": "...", "bottom": "..."}'
        ),
        f"Situation: {context}. Write the meme.",
        tone, max_tokens=200,
    )
    top = str((data or {}).get("top", "")).strip()
    bottom = str((data or {}).get("bottom", "")).strip()
    if not top and not bottom:
        return {}
    image_path = render_meme(out_dir, f"meme_{key}", top, bottom)
    caption = _caption(claude, f"Caption a league meme about: {context}.", tone)
    return {"caption": caption, "image_path": image_path}
