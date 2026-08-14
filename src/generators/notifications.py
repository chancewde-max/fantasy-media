"""ESPN-style breaking-news notification blurbs."""
from __future__ import annotations

from ..events import Event
from .claude_client import ClaudeClient

SYSTEM = (
    "You write short ESPN-style breaking-news fantasy football alerts. "
    "One or two sentences. Lead with a siren emoji. No hashtags. "
    "Keep it under 240 characters."
)


def generate_notification(claude: ClaudeClient, event: Event, tone: str) -> str:
    prompt = _prompt_for(event)
    return claude.generate(SYSTEM, prompt, tone, max_tokens=160)


def _prompt_for(event: Event) -> str:
    d = event.data
    if event.kind == "matchup_final":
        return (
            f"Week {d['week']}: {d['winner']} beat {d['loser']} "
            f"{d['winner_score']} to {d['loser_score']} (margin {d['margin']}). "
            "Write the alert."
        )
    if event.kind == "blowout":
        return (
            f"Week {d['week']} biggest blowout: {d['winner']} destroyed "
            f"{d['loser']} by {d['margin']} points. Write the alert."
        )
    if event.kind == "nailbiter":
        return (
            f"Week {d['week']} closest game: {d['teams'][0]} vs {d['teams'][1]}, "
            f"decided by just {d['margin']} points. Write the alert."
        )
    if event.kind == "high":
        return f"Week {d['week']} high scorer: {d['team']} with {d['score']} points."
    if event.kind == "low":
        return f"Week {d['week']} lowest scorer: {d['team']} with only {d['score']} points."
    if event.kind == "transaction":
        return f"League transaction: {d['summary']}. Write the alert."
    return event.title
