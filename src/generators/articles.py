"""Short companion articles.

A paragraph of context that follows an ESPN alert or an Insider report — not
a restatement of the headline, a bit of color on why it matters.
"""
from __future__ import annotations

from .claude_client import ClaudeClient

SYSTEM = (
    "You are a fantasy football beat writer for the league's media outlet. "
    "Given the news below, write a short companion article: a punchy "
    "headline (max 8 words) plus ONE paragraph (3-5 sentences) of color, "
    "context, or reaction — why it matters, what the league is saying, "
    "what's next. Don't just restate the headline. If the news involves an "
    "anonymous tip or source, never reveal or speculate on who it might be "
    "— stay as vague about identity as the news itself. No real NFL player "
    "or team names. Respond as JSON: "
    '{"headline": "...", "body": "..."}'
)


def generate_article(claude: ClaudeClient, context: str, tone: str) -> dict:
    data = claude.generate_json(
        SYSTEM, f'The news: "{context}". Write the article.', tone, max_tokens=500,
    )
    if isinstance(data, dict) and data.get("body"):
        return {
            "headline": str(data.get("headline") or "").strip(),
            "body": str(data["body"]).strip(),
        }
    return {"headline": "", "body": context}
