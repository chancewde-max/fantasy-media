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
    "Report it in these parts:\n"
    "- headline: a short, punchy, attention-grabbing scoop — max 10 words, "
    "one emoji max. This is what flashes as a phone push notification and "
    "as the card's bold top line, so make it land.\n"
    "- body: the full story, 3-5 sentences that expand on the headline with "
    "the scoop, the color, what the league is saying, and what's next. Add "
    "real detail — do NOT just restate the headline.\n"
    "- storyline_action: one of \"continue\" (this report escalates or pays "
    "off one of the ONGOING LEAGUE STORYLINES listed in the context, if any "
    "were given and one genuinely fits), \"new\" (this report is juicy or "
    "recurring enough to be worth tracking as its own arc going forward — a "
    "real beef, a pattern, a running bit), or \"none\" (a one-off, nothing "
    "worth tracking). Default to \"none\" — most reports are just one drop, "
    "don't force a storyline where there isn't one.\n"
    "- storyline_key: REQUIRED and must exactly match one of the [key: ...] "
    "values from the context when storyline_action is \"continue\". Omit "
    "otherwise.\n"
    "- storyline_title: REQUIRED (a short 3-6 word name for the arc, e.g. "
    "'The Josh Benching Scandal') when storyline_action is \"new\". Omit "
    "otherwise.\n"
    "- canon_note: REQUIRED when storyline_action is \"new\" or \"continue\" "
    "— ONE factual sentence capturing what just happened in-story, written "
    "so a future report can reference it as established history. Omit when "
    "storyline_action is \"none\".\n"
    'Respond as JSON: {"headline": "...", "body": "...", "storyline_action": '
    '"...", "storyline_key": "...", "storyline_title": "...", "canon_note": "..."}'
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
    "storyline": {"action": "none"},
}


def _with_context(prompt: str, context: str) -> str:
    """Prepend real league context so the report fits the actual league —
    the managers, their records, their tendencies, and any ongoing manufactured
    storylines — instead of generic filler. The context is background to draw
    on, not something to recite."""
    if not context:
        return prompt
    return (
        "Real league context (managers, records, tendencies, ongoing "
        "storylines — use it to keep the report grounded and believable; "
        "weave in only what's relevant, never dump it verbatim, and never "
        "contradict it):\n"
        f"{context}\n\n{prompt}"
    )


def generate_insider_report(claude, tip_text: str, tone: str, context: str = "") -> dict:
    """Rewrite one raw manager tip into a punchy anonymous report.

    ``context`` is optional real league background (see league_history) that
    keeps the report believable — tied to the actual managers and their
    history rather than generic drama.

    Returns a ``{"headline": str, "body": str}`` pair — a short scoop for the
    notification/headline and a fuller story for the card's "read more". Never
    publishes the tip verbatim, and never leaks a Claude refusal into the feed
    — a tip that isn't safe to run gets reshaped into fictional in-league
    drama instead, with a couple of safety-netted fallbacks so something
    usable always comes back.
    """
    prompt = _with_context(f'Tip: "{tip_text}". Write the insider report.', context)
    report = _extract_report(claude.generate_json(REPORT_SYSTEM, prompt, tone, max_tokens=500))
    if report:
        return report

    report = _extract_report(
        claude.generate_json(
            FALLBACK_SYSTEM, _with_context("Write the report.", context), tone, max_tokens=500
        )
    )
    return report or dict(_DEFAULT_REPORT)


def generate_fabricated_rumor(claude, tone: str, context: str = "") -> dict:
    """Invent a rumor from nothing, for the scheduled 'nothing to report' slot.

    ``context`` is optional real league background so the invented rumor fits
    actual managers and their tendencies. Same ``{"headline", "body"}`` shape
    as ``generate_insider_report``.
    """
    report = _extract_report(
        claude.generate_json(
            FABRICATE_SYSTEM,
            _with_context("No tips today. Invent one and write the report.", context),
            tone, max_tokens=500,
        )
    )
    return report or dict(_DEFAULT_REPORT)


def _extract_report(data) -> dict | None:
    """Pull a clean ``{"headline", "body", "storyline"}`` out of Claude's
    JSON, or None.

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
    return {"headline": headline, "body": body, "storyline": _extract_storyline(data)}


def _extract_storyline(data: dict) -> dict:
    """Pull the optional storyline_action/key/title/canon_note fields into
    the {"action", "key", "title", "canon_note"} shape storylines.apply_update
    expects. Malformed or missing fields fall back to "none" — a storyline is
    never persisted on shaky data."""
    action = str(data.get("storyline_action") or "none").strip().lower()
    if action not in {"new", "continue"}:
        return {"action": "none"}
    canon_note = str(data.get("canon_note") or "").strip()
    if not canon_note:
        return {"action": "none"}
    if action == "new":
        title = str(data.get("storyline_title") or "").strip()
        if not title:
            return {"action": "none"}
        return {"action": "new", "title": title, "canon_note": canon_note}
    key = str(data.get("storyline_key") or "").strip()
    if not key:
        return {"action": "none"}
    return {"action": "continue", "key": key, "canon_note": canon_note}


def _headline_from_body(body: str, max_words: int = 10) -> str:
    """Fallback headline: the body's first sentence, trimmed to a few words."""
    first = body.split(". ")[0].strip().rstrip(".")
    words = first.split()
    if len(words) <= max_words:
        return first
    return " ".join(words[:max_words]) + "…"
