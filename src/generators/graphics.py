"""Turn league events into real 'sports app' graphic posts.

Each function returns {"caption", "image_path"} (plus "gif_url" where a
reaction GIF fits). Graphics are rendered as HTML/CSS through headless
Chromium (moody team-colored gradients, ghosted numerals, gold accents,
grain, real team logos) — with the flat Pillow renderers kept as an automatic
fallback if Chromium isn't available, so the feed never breaks.
"""
from __future__ import annotations

import os

from .. import gifs, league_history
from ..events import Event
from ..graphics import html_render, logos, render, templates
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
    return f"WEEK {w}" if w else ""


def _logo(team: str):
    try:
        return logos.logo_data_uri(team)
    except Exception:  # noqa: BLE001 - never let a logo lookup break a post
        return None


def _render(html: str, name: str, out_dir: str) -> str | None:
    return html_render.render_html(html, os.path.join(out_dir, f"{name}.png"))


# ---------------------------------------------------------------------------
def gameday_post(claude: ClaudeClient, event: Event, tone: str, out_dir: str) -> dict:
    d = event.data
    a, b = d.get("team_a", ""), d.get("team_b", "")
    lore = d.get("lore", "")
    html = templates.matchup_html(
        a, b, league_history.team_tagline(a), league_history.team_tagline(b),
        _week_label(d), lore, logo_a=_logo(a), logo_b=_logo(b),
    )
    image_path = _render(html, f"gameday_{event.key}", out_dir)
    if image_path is None:  # Pillow fallback
        image_path = render.render_gameday_matchup(
            out_dir, f"gameday_{event.key}", a, b,
            sub_a=league_history.team_tagline(a), sub_b=league_history.team_tagline(b),
            week_label=_week_label(d), lore=lore,
        )
    caption = _caption(
        claude,
        f"Game of the Week: {a} vs {b}. Lore: {lore or league_history.league_brief([a, b]) or 'none'}. "
        "Write a hype caption.",
        tone,
    )
    return {"caption": caption, "image_path": image_path}


def _badge_for(kind: str, margin: float | None) -> str:
    if kind == "nailbiter":
        return "NAILBITER"
    if kind == "blowout":
        return "BLOWOUT"
    if margin is not None and margin >= 40:
        return "BLOWOUT"
    if margin is not None and margin <= 6:
        return "NAILBITER"
    return ""


def final_score_post(claude: ClaudeClient, event: Event, tone: str, out_dir: str) -> dict:
    d = event.data
    winner, loser = d.get("winner", ""), d.get("loser", "")
    w_score, l_score, margin = d.get("winner_score"), d.get("loser_score"), d.get("margin")
    if w_score is None and margin is not None:
        w_score, l_score = margin, 0.0
    w_score = float(w_score or 0)
    l_score = float(l_score or 0)
    badge = _badge_for(event.kind, margin)
    html = templates.final_score_html(
        winner, w_score, loser, l_score, badge, "", _week_label(d),
        logo_w=_logo(winner), logo_l=_logo(loser),
    )
    image_path = _render(html, f"final_{event.key}", out_dir)
    if image_path is None:
        image_path = render.render_final_score(
            out_dir, f"final_{event.key}", winner, w_score, loser, l_score, badge=badge,
        )
    caption = _caption(
        claude,
        f"Final: {winner} beat {loser} {w_score:g}-{l_score:g} (margin {margin}). "
        "Write a scoreboard caption.",
        tone,
    )
    return {"caption": caption, "image_path": image_path,
            "gif_url": gifs.search_gif(f"{event.kind} football win celebration")}


def stat_leader_post(claude: ClaudeClient, event: Event, tone: str, out_dir: str) -> dict:
    d = event.data
    team, score = d.get("team", ""), d.get("score", "")
    is_high = event.kind == "high"
    kicker = "TEAM OF THE WEEK" if is_high else "LOW OF THE WEEK"
    label = "POINTS" if is_high else "POINTS · YIKES"
    value = f"{score:g}" if isinstance(score, (int, float)) else str(score)
    html = templates.stat_leader_html(
        kicker, team, value, label, league_history.team_tagline(team),
        ghost="1" if is_high else "L", logo=_logo(team),
    )
    image_path = _render(html, f"stat_{event.key}", out_dir)
    if image_path is None:
        image_path = render.render_stat_leader(
            out_dir, f"stat_{event.key}", kicker, team, value, label,
            sub=league_history.team_tagline(team),
        )
    verb = "torched the league" if is_high else "face-planted"
    caption = _caption(
        claude, f"{team} {verb} with {score} points in Week {d.get('week')}. Write a caption.", tone,
    )
    return {"caption": caption, "image_path": image_path}


def record_post(out_dir: str, key: str, kicker: str, big_line: str, sub: str, team: str, ghost: str = "") -> dict:
    html = templates.record_html(kicker, big_line, sub, team, ghost=ghost, logo=_logo(team))
    image_path = _render(html, f"record_{key}", out_dir)
    if image_path is None:
        image_path = render.render_record_card(out_dir, f"record_{key}", kicker, big_line, sub)
    return {"caption": f"{big_line} — {sub}".strip(" —"), "image_path": image_path}


def meme_post(claude: ClaudeClient, context: str, tone: str, out_dir: str, key: str, team: str = "") -> dict:
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
    html = templates.meme_html(top, bottom, team=team)
    image_path = _render(html, f"meme_{key}", out_dir)
    if image_path is None:
        image_path = render.render_meme(out_dir, f"meme_{key}", top, bottom)
    caption = _caption(claude, f"Caption a league meme about: {context}.", tone)
    return {"caption": caption, "image_path": image_path}
