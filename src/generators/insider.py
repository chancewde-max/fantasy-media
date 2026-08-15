"""The Insider: turns manager tips into anonymous reports.

Rules (per product design):
  * Every tip gets reported as its own Insider drop as soon as it's received —
    no waiting, no corroboration threshold. Tips stay anonymous; the report
    never reveals who sent it.
  * If no tip has come in recently, a scheduled job (3x/day) invents a
    plausible-sounding rumor so the Insider still has something to say.
  * A tip is never published verbatim, and a tip that isn't safe to run as
    real-world claims about a real person gets reshaped into fictional
    in-league fantasy football drama instead — never dropped, never leaked
    as a refusal.
"""
from __future__ import annotations

REPORT_SYSTEM = (
    "You are Dianna Russinni, a fantasy football league's insider reporter who "
    "breaks news from anonymous sources. Turn the tip below into a short, "
    "punchy insider report (max 280 chars). Attribute it to 'a source' or "
    "'word around the league' — NEVER reveal who tipped it, and don't repeat "
    "the tip verbatim, rephrase it like a scoop. One emoji max.\n\n"
    "This is a fantasy football gossip column, not real news. If the tip is "
    "in-league fantasy football drama (a trade, a benching, a lineup call, "
    "waiver activity, a rivalry, league beef), report on it normally. If the "
    "tip instead makes a claim about a real person's actual private life, "
    "health, relationships, or political views — or anything outside fantasy "
    "football — do not report that claim as real. Instead keep only the "
    "general flavor of the tip and reinvent it as fictional in-league "
    "drama: swap the real person for a generic league-manager persona, and "
    "swap the real situation for an equivalent fantasy-team situation (a "
    "shady trade, a petty bench decision, a waiver heist, etc). Always "
    "produce a usable, in-universe report — never explain, refuse, or "
    'mention that anything was changed. Respond as JSON: {"report": "..."}'
)

FALLBACK_SYSTEM = (
    "You are Dianna Russinni, a fantasy football league's insider reporter who "
    "breaks news from anonymous sources. Invent a short, punchy, purely "
    "fictional bit of in-league fantasy football gossip (a trade being "
    "shopped, a lineup snub, waiver-wire drama, manager beef). Max 280 "
    "chars, one emoji max, attribute to 'sources' the way real insiders do. "
    'Respond as JSON: {"report": "..."}'
)

FABRICATE_SYSTEM = (
    "You are Dianna Russinni, a fantasy football league's insider reporter who "
    "breaks news from anonymous sources. No real tip has come in — invent a "
    "plausible-sounding rumor or bit of league gossip (a trade being shopped, "
    "a lineup snub, beef between two managers, waiver-wire drama). Keep it "
    "vague enough to sound like real unconfirmed gossip, not a fact. Max 280 "
    "chars, one emoji max, attribute to 'sources' the way real insiders do."
)

_REFUSAL_MARKERS = (
    "i can't help", "i cant help", "i won't", "i wont", "i'm not able",
    "i am not able", "unable to help", "can't write", "cant write",
    "can't report", "cant report",
)

_DEFAULT_REPORT = (
    "Word around the league: something's brewing, but even Dianna's "
    "sources went quiet on this one. 👀"
)


def generate_insider_report(claude, tip_text: str, tone: str) -> str:
    """Rewrite one raw manager tip into a punchy anonymous report.

    Never publishes the tip verbatim, and never leaks a Claude refusal into
    the feed — a tip that isn't safe to run gets reshaped into fictional
    in-league drama instead, with a couple of safety-netted fallbacks so
    something usable always comes back.
    """
    prompt = f'Tip: "{tip_text}". Write the insider report.'
    report = _extract_report(claude.generate_json(REPORT_SYSTEM, prompt, tone, max_tokens=220))
    if report:
        return report

    report = _extract_report(
        claude.generate_json(FALLBACK_SYSTEM, "Write the report.", tone, max_tokens=220)
    )
    return report or _DEFAULT_REPORT


def generate_fabricated_rumor(claude, tone: str) -> str:
    """Invent a rumor from nothing, for the scheduled 'nothing to report' slot."""
    return claude.generate(
        FABRICATE_SYSTEM, "No tips today. Invent one and write the report.",
        tone, max_tokens=180,
    )


def _extract_report(data) -> str | None:
    if not isinstance(data, dict):
        return None
    report = str(data.get("report") or "").strip()
    if not report:
        return None
    lowered = report.lower()
    if any(marker in lowered for marker in _REFUSAL_MARKERS):
        return None
    return report
