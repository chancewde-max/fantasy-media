"""Fan-reaction layer: reaction tweets to reports, and fan comments on posts.

These make the feed feel alive — invented fan personas reacting to what the
league's media is putting out, rather than a one-way broadcast.
"""
from __future__ import annotations

import logging

from .claude_client import ClaudeClient

log = logging.getLogger(__name__)

REACTION_TWEETS_SYSTEM = (
    "You are inventing reactions from fictional fantasy-league 'fans' on a "
    "Twitter-like feed reacting to a just-published insider report. First "
    "judge how inflammatory the report actually is. If it's mild, vague, or "
    "barely a scoop, most fans should run an honor-system defense — downplay "
    "it, have the subject's back, tell people they're reaching ('yall not "
    "about to make this a thing', 'this is nothing lol'). If it's genuinely "
    "juicy or damning, fans pile on and roast instead. Match the energy to "
    "the report — don't roast over nothing, and don't defend the indefensible. "
    'Return a JSON array of objects {"handle": "@fanhandle", "text": "the '
    'tweet"}. Make handles feel like real fan accounts (nicknames, team '
    "stans, degen bettors). Tweets are short (max 200 chars). No real NFL "
    "names."
)

FAN_COMMENTS_SYSTEM = (
    "You are inventing short comments from fictional fantasy-league 'fans' "
    "reacting to a post in a league media feed. Return a JSON array of objects "
    '{"handle": "@fanhandle", "text": "the comment"}. Keep each under 120 '
    "chars, casual, reactive, a mix of hype/roast/jokes. No real NFL names."
)


def generate_reaction_tweets(claude: ClaudeClient, report_body: str, tone: str, n: int = 3):
    data = claude.generate_json(
        REACTION_TWEETS_SYSTEM,
        f"The report: \"{report_body}\". Write {n} fan reaction tweets.",
        tone, max_tokens=500,
    )
    return _clean(data, n)


def generate_fan_comments(claude: ClaudeClient, post_body: str, tone: str, n: int = 2):
    data = claude.generate_json(
        FAN_COMMENTS_SYSTEM,
        f"The post: \"{post_body}\". Write {n} fan comments.",
        tone, max_tokens=400,
    )
    return _clean(data, n)


def _clean(data, n: int):
    out = []
    if isinstance(data, list):
        for item in data[:n]:
            if isinstance(item, dict) and item.get("text"):
                handle = str(item.get("handle") or "@fan").strip()
                if not handle.startswith("@"):
                    handle = "@" + handle
                out.append({"handle": handle, "text": str(item["text"]).strip()})
    return out
