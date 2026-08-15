"""The Insider: turns manager tips into anonymous reports.

Rules (per product design):
  * Every tip gets reported as its own Insider drop as soon as it's received —
    no waiting, no corroboration threshold. Tips stay anonymous; the report
    never reveals who sent it.
  * If no tip has come in recently, a scheduled job (3x/day) invents a
    plausible-sounding rumor so the Insider still has something to say.
"""
from __future__ import annotations

REPORT_SYSTEM = (
    "You are @LeagueInsider, a fantasy football insider who breaks news from "
    "anonymous sources. Write a short, punchy insider report (max 280 chars) "
    "based on the tip below. Attribute it to 'a source' or 'word around the "
    "league' — NEVER reveal who tipped it, and don't repeat the tip verbatim, "
    "rephrase it like a scoop. One emoji max."
)

FABRICATE_SYSTEM = (
    "You are @LeagueInsider, a fantasy football insider who breaks news from "
    "anonymous sources. No real tip has come in — invent a plausible-sounding "
    "rumor or bit of league gossip (a trade being shopped, a lineup snub, "
    "beef between two managers, waiver-wire drama). Keep it vague enough to "
    "sound like real unconfirmed gossip, not a fact. Max 280 chars, one "
    "emoji max, attribute to 'sources' the way real insiders do."
)


def generate_insider_report(claude, tip_text: str, tone: str) -> str:
    """Rewrite one raw manager tip into a punchy anonymous report."""
    prompt = f"Tip: \"{tip_text}\". Write the insider report."
    return claude.generate(REPORT_SYSTEM, prompt, tone, max_tokens=180)


def generate_fabricated_rumor(claude, tone: str) -> str:
    """Invent a rumor from nothing, for the scheduled 'nothing to report' slot."""
    return claude.generate(
        FABRICATE_SYSTEM, "No tips today. Invent one and write the report.",
        tone, max_tokens=180,
    )
