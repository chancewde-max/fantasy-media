"""Two fixed, recurring pundits — Dan Orlovsky and Stephen A. Smith — who
react to Insider drops.

Unlike the crowd of invented fan reaction tweets (reactions.py), these are
NOT a random pile-on: they're two consistent, recognizable voices that
always react to a just-published Insider report, arguing about and
analyzing what Dianna Russinni already reported. They never invent new
scoops or facts of their own — that's the Insider's job, not theirs.
"""
from __future__ import annotations

import logging

from .claude_client import ClaudeClient

log = logging.getLogger(__name__)

PUNDITS_SYSTEM = (
    "You are writing a two-take debate-show reaction to a fantasy football "
    "league's insider report — in the voices of two real ESPN personalities, "
    "playing themselves for comedic effect on a parody fantasy football "
    "debate show. They are reacting to and arguing about news that has "
    "ALREADY been reported — never invent new facts, scoops, or details "
    "beyond what's in the report below.\n\n"
    "DAN ORLOVSKY (@danorlovsky7): a hyper-analytical ex-QB who breaks "
    "everything down like it's game film, painfully earnest, applies "
    "serious football-analysis language to a silly fantasy football gossip "
    "story, confident even when the take is a stretch.\n\n"
    "STEPHEN A. SMITH (@stephenasmith): loud, bombastic, moralizing, "
    "dramatic pauses written as '...', calls people 'brother', treats "
    "fantasy football drama like it's the biggest story in sports, big "
    "declarative statements, mock outrage.\n\n"
    "Write ONE short take from each (max 220 characters each, one tweet's "
    "worth), reacting to the SAME report — bonus points if they end up "
    "disagreeing with each other, the way they do on TV.\n\n"
    'Return a JSON array of exactly two objects, in this order: '
    '[{"handle": "@danorlovsky7", "text": "..."}, '
    '{"handle": "@stephenasmith", "text": "..."}]'
)

# Canonical handle -> itself, keyed lowercase for matching. Anything Claude
# returns that isn't one of these two exact personas is dropped rather than
# published — these are fixed characters, not a slot for an invented third.
_PUNDITS = {"@danorlovsky7": "@danorlovsky7", "@stephenasmith": "@stephenasmith"}


def generate_pundit_takes(claude: ClaudeClient, report_body: str, tone: str) -> list[dict]:
    """Dan Orlovsky's and Stephen A. Smith's reactions to an already-published
    Insider report.

    Returns up to two ``{"handle", "text"}`` dicts (fewer if Claude drops a
    persona or misbehaves — never raises, and never publishes a persona that
    wasn't one of the two fixed ones)."""
    data = claude.generate_json(
        PUNDITS_SYSTEM,
        f'The insider report: "{report_body}". Write both reactions.',
        tone, max_tokens=400,
    )
    return _clean(data)


def _clean(data) -> list[dict]:
    out = []
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict) or not item.get("text"):
                continue
            handle = str(item.get("handle") or "").strip()
            if not handle.startswith("@"):
                handle = "@" + handle
            canonical = _PUNDITS.get(handle.lower())
            if not canonical:
                continue
            out.append({"handle": canonical, "text": str(item["text"]).strip()})
    return out[:2]
