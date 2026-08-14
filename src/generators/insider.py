"""Turns a manager-submitted tip into an anonymous 'Insider' report.

The fictional insider (@LeagueInsider) rewrites raw tips into breaking-news
insider-speak — never revealing who sent the tip.
"""
from __future__ import annotations

from .claude_client import ClaudeClient

SYSTEM = (
    "You are @LeagueInsider, a fantasy football insider who breaks news from "
    "anonymous sources inside the league. Rewrite the tip below into a short, "
    "punchy insider report (max 280 chars). Attribute it to 'league sources' "
    "or 'sources tell me' — NEVER reveal or hint at who sent the tip. Add a "
    "little intrigue. One emoji max."
)


def generate_insider_report(claude: ClaudeClient, raw_tip: str, tone: str) -> str:
    prompt = f"Tip from an anonymous manager: \"{raw_tip}\". Write the insider report."
    return claude.generate(SYSTEM, prompt, tone, max_tokens=180)
