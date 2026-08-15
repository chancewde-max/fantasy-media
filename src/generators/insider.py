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

Each report comes back as two parts:
  * headline — a short, punchy scoop (this is what flashes as the push
    notification and shows as the card's bold line), and
  * body — the full story, a few sentences of color that the card reveals
    behind "Read the full story". The headline grabs; the body delivers.
"""
from __future__ import annotations

_FORMAT_RULES = (
    "Report it in TWO parts:\n"
    "- headline: a short, punchy, attention-grabbing scoop — max 10 words, "
    "one emoji max. This is what flashes as a phone push notification and "
    "as the card's bold top line, so make it land.\n"
    "- body: the full story, 3-5 sentences that expand on the headline with "
    "the scoop, the color, what the league is saying, and what's next. Add "
    "real detail — do NOT just restate the headline.\n"
    'Respond as JSON: {"headline": "...", "body": "..."}'
)

REPORT_SYSTEM = (
    "You are Dianna Russinni, a fantasy football league's insider reporter who "
    "breaks news from anonymous sources. Turn the tip below into an anonymous "
    "insider report. Attribute it to 'a source' or 'word around the league' — "
    "NEVER reveal who tipped it, and don't repeat the tip verbatim, rephrase "
    "it like a scoop. \n\n"
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
    "mention that anything was changed.\n\n" + _FORMAT_RULES
)

FALLBACK_SYSTEM = (
    "You are Dianna Russinni, a fantasy football league's insider reporter who "
    "breaks news from anonymous sources. Invent a short, purely fictional bit "
    "of in-league fantasy football gossip (a trade being shopped, a lineup "
    "snub, waiver-wire drama, manager beef). Attribute it to 'sources' the "
    "way real insiders do.\n\n" + _FORMAT_RULES
)

FABRICATE_SYSTEM = (
    "You are Dianna Russinni, a fantasy football league's insider reporter who "
    "breaks news from anonymous sources. No real tip has come in — invent a "
    "plausible-sounding rumor or bit of league gossip (a trade being shopped, "
    "a lineup snub, beef between two managers, waiver-wire drama). Keep it "
    "vague enough to sound like real unconfirmed gossip, not a fact. "
    "Attribute it to 'sources' the way real insiders do.\n\n" + _FORMAT_RULES
)

_REFUSAL_MARKERS = (
    "i can't help", "i cant help", "i won't", "i wont", "i'm not able",
    "i am not able", "unable to help", "can't write", "cant write",
    "can't report", "cant report",
)

_DEFAULT_REPORT = {
    "headline": "Something's brewing in the league 👀",
    "body": (
        "Word around the league: something's brewing, but even Dianna's "
        "sources went quiet on this one. Stay tuned — when it breaks, you'll "
        "hear it here first."
    ),
}


def generate_insider_report(claude, tip_text: str, tone: str) -> dict:
    """Rewrite one raw manager tip into a punchy anonymous report.

    Returns a ``{"headline": str, "body": str}`` pair — a short scoop for the
    notification/headline and a fuller story for the card's "read more". Never
    publishes the tip verbatim, and never leaks a Claude refusal into the feed
    — a tip that isn't safe to run gets reshaped into fictional in-league
    drama instead, with a couple of safety-netted fallbacks so something
    usable always comes back.
    """
    prompt = f'Tip: "{tip_text}". Write the insider report.'
    report = _extract_report(claude.generate_json(REPORT_SYSTEM, prompt, tone, max_tokens=500))
    if report:
        return report

    report = _extract_report(
        claude.generate_json(FALLBACK_SYSTEM, "Write the report.", tone, max_tokens=500)
    )
    return report or dict(_DEFAULT_REPORT)


def generate_fabricated_rumor(claude, tone: str) -> dict:
    """Invent a rumor from nothing, for the scheduled 'nothing to report' slot.

    Same ``{"headline", "body"}`` shape as ``generate_insider_report``.
    """
    report = _extract_report(
        claude.generate_json(
            FABRICATE_SYSTEM, "No tips today. Invent one and write the report.",
            tone, max_tokens=500,
        )
    )
    return report or dict(_DEFAULT_REPORT)


def _extract_report(data) -> dict | None:
    """Pull a clean ``{"headline", "body"}`` out of Claude's JSON, or None.

    Requires a usable body; if the model returns a body but no headline, we
    synthesize a short one from the body so the card/notification still has a
    punchy top line. Refusals (in either field) are rejected so nothing like
    "I can't help with that" ever lands in the feed.
    """
    if not isinstance(data, dict):
        return None
    body = str(data.get("body") or "").strip()
    if not body:
        return None
    headline = str(data.get("headline") or "").strip() or _headline_from_body(body)

    combined = f"{headline}\n{body}".lower()
    if any(marker in combined for marker in _REFUSAL_MARKERS):
        return None
    return {"headline": headline, "body": body}


def _headline_from_body(body: str, max_words: int = 10) -> str:
    """Fallback headline: the body's first sentence, trimmed to a few words."""
    first = body.split(". ")[0].strip().rstrip(".")
    words = first.split()
    if len(words) <= max_words:
        return first
    return " ".join(words[:max_words]) + "…"
