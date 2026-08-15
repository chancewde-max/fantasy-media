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
    "judge how inflammatory the report actually is — and let that judgment "
    "decide HOW MANY tweets to write, not just their tone.\n\n"
    "You may write anywhere from 0 up to {max_n} tweets, and you should use "
    "that whole range across different reports — DON'T default to a middle "
    "number every time. Rough guide:\n"
    "- a total nothing-burger (no real news, pure vague filler): 0-1 tweets\n"
    "- mild / barely-a-scoop: 1-2 tweets, mostly an honor-system defense — "
    "downplay it, have the subject's back, tell people they're reaching "
    "('yall not about to make this a thing', 'this is nothing lol')\n"
    "- a solid, genuinely interesting scoop: 3-4 tweets\n"
    "- juicy or damning, the kind that blows up the group chat: 5 up to "
    "{max_n} tweets as the whole league piles in to roast\n"
    "Pick the count that honestly fits THIS report — a quiet one gets a "
    "short array, an explosive one gets a long one. Don't roast over "
    "nothing, and don't defend the indefensible.\n\n"
    'Return a JSON array of objects {{"handle": "@fanhandle", "text": "the '
    'tweet"}}. Make handles feel like real fan accounts (nicknames, team '
    "stans, degen bettors). Tweets are short (max 200 chars). No real NFL "
    "names."
)

FAN_COMMENTS_SYSTEM = (
    "You are inventing short comments from fictional fantasy-league 'fans' "
    "reacting to a post in a league media feed. Return a JSON array of objects "
    '{"handle": "@fanhandle", "text": "the comment"}. Keep each under 120 '
    "chars, casual, reactive, a mix of hype/roast/jokes. No real NFL names."
)


def generate_reaction_tweets(claude: ClaudeClient, report_body: str, tone: str, max_n: int = 6):
    """Fan reaction tweets, count and tone both driven by how inflammatory
    Claude judges the report to be. max_n is the hard ceiling AND is fed into
    the prompt so the model spreads its counts across the full 0..max_n range
    instead of clustering on one number."""
    data = claude.generate_json(
        REACTION_TWEETS_SYSTEM.format(max_n=max_n),
        f'The report: "{report_body}". Write the fan reaction tweets.',
        tone, max_tokens=700,
    )
    return _clean(data, max_n)


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
