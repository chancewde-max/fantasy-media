"""The Insider: clusters corroborated manager tips into anonymous reports.

Rules (per product design):
  * A rumor is only published once at least MIN_CORROBORATION managers have
    independently reported the same thing (clusters of size >= threshold).
  * Tips stay secret — managers never see each other's; Claude does the
    matching from the raw text.
  * Reports go out in a once-a-day batch (scheduled by the caller).
"""
from __future__ import annotations

import logging

from .claude_client import ClaudeClient

log = logging.getLogger(__name__)

CLUSTER_SYSTEM = (
    "You are a fantasy football league's rumor desk. You receive a list of "
    "anonymous tips submitted by league managers. Group tips that describe the "
    "SAME underlying rumor (same players/teams/claim), even if worded "
    "differently. Return a JSON array of clusters; each cluster is an object "
    '{"tip_ids": [list of ids], "summary": "one-line neutral summary"}. '
    "Only include a cluster if it groups 2 or more DISTINCT tips. Ignore "
    "one-off tips with no match. Return [] if nothing corroborates."
)

REPORT_SYSTEM = (
    "You are @LeagueInsider, a fantasy football insider who breaks news from "
    "anonymous sources. Write a short, punchy insider report (max 280 chars) "
    "based on the corroborated rumor below. Attribute to 'multiple sources' or "
    "'sources around the league' — NEVER reveal who tipped it. One emoji max."
)


def cluster_tips(claude: ClaudeClient, tips: list[dict], min_corroboration: int = 2):
    """Return clusters of tip ids that corroborate each other (size >= threshold).

    tips: [{"id": ..., "raw_text": ...}, ...]
    Falls back to exact-text matching if the model call fails.
    """
    if len(tips) < min_corroboration:
        return []

    listing = "\n".join(f'- id={t["id"]}: "{t["raw_text"]}"' for t in tips)
    data = claude.generate_json(
        CLUSTER_SYSTEM,
        f"Tips:\n{listing}\n\nCluster them.",
        tone="hype",
        max_tokens=800,
    )

    clusters = []
    if isinstance(data, list):
        valid_ids = {str(t["id"]) for t in tips}
        for c in data:
            ids = [str(i) for i in c.get("tip_ids", []) if str(i) in valid_ids]
            ids = list(dict.fromkeys(ids))  # de-dup, preserve order
            if len(ids) >= min_corroboration:
                clusters.append({"tip_ids": ids, "summary": c.get("summary", "")})
        return clusters

    # Fallback: group by normalized exact text.
    log.warning("Tip clustering fell back to exact-text matching.")
    buckets: dict[str, list[str]] = {}
    summaries: dict[str, str] = {}
    for t in tips:
        key = " ".join(t["raw_text"].lower().split())
        buckets.setdefault(key, []).append(str(t["id"]))
        summaries[key] = t["raw_text"]
    return [
        {"tip_ids": ids, "summary": summaries[key]}
        for key, ids in buckets.items()
        if len(ids) >= min_corroboration
    ]


def generate_insider_report(claude: ClaudeClient, summary: str, tone: str) -> str:
    prompt = f"Corroborated rumor: \"{summary}\". Write the insider report."
    return claude.generate(REPORT_SYSTEM, prompt, tone, max_tokens=180)
