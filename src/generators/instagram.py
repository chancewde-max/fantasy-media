"""Instagram-style post: caption + a generated square graphic."""
from __future__ import annotations

from ..events import Event
from ..graphics.render import render_post_card
from .claude_client import ClaudeClient

SYSTEM = (
    "You write Instagram captions for a fantasy football league's parody "
    "media account. 1-3 short lines, punchy, 3-5 hashtags at the end, "
    "a couple of emojis. Keep it under 300 characters."
)


def generate_instagram(claude: ClaudeClient, event: Event, tone: str, out_dir: str) -> dict:
    caption = claude.generate(
        SYSTEM, f"Event: {event.title}. Details: {event.data}. Write the caption.",
        tone, max_tokens=200,
    )
    headline = event.title
    image_path = render_post_card(
        out_dir=out_dir,
        name=f"ig_{event.key}",
        headline=headline,
        subtext=_subtext(event),
    )
    return {"caption": caption, "image_path": image_path}


def _subtext(event: Event) -> str:
    d = event.data
    if event.kind == "matchup_final":
        return f"{d['winner_score']} - {d['loser_score']}"
    if "score" in d:
        return f"{d['score']} pts"
    if "margin" in d:
        return f"by {d['margin']} pts"
    return ""
