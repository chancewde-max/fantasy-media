"""Parody beat-reporter tweets."""
from __future__ import annotations

from ..events import Event
from .claude_client import ClaudeClient

SYSTEM = (
    "You are Dianna Russinni, a fictional fantasy football beat reporter with "
    "a huge ego and a nose for drama. Write a single tweet (max 280 chars) "
    "reporting on the event like it's league-shaking news. Use 1-2 hashtags "
    "and at most one emoji. Do not use real NFL player or team names."
)


def generate_tweet(claude: ClaudeClient, event: Event, tone: str) -> str:
    d = event.data
    prompt = f"Event: {event.title}. Details: {d}. Write the tweet."
    return claude.generate(SYSTEM, prompt, tone, max_tokens=180)
