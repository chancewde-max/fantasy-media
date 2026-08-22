"""Reaction GIFs via Giphy.

Optional layer: if GIPHY_API_KEY is set, we pull a real animated reaction GIF
for a post so the feed feels like a live group chat. Without the key (or
without network), every function is a safe no-op returning None, and the rest
of the bot carries on with its native meme graphics.

(Tenor was the original plan but no longer issues new API keys, so we use
Giphy, which still does — get a free key at developers.giphy.com.)

We return a direct .gif media URL, which the web feed renders like any other
image (an animated GIF is just an image URL).
"""
from __future__ import annotations

import logging
import os
import random

import requests

log = logging.getLogger(__name__)

_ENDPOINT = "https://api.giphy.com/v1/gifs/search"


def gifs_enabled() -> bool:
    return bool(os.environ.get("GIPHY_API_KEY"))


def search_gif(query: str, *, limit: int = 25, timeout: int = 8) -> str | None:
    """Return a random reaction GIF URL for the query, or None if GIFs aren't
    configured / nothing came back / the request failed.

    Randomizing over the result set keeps the same query from returning the
    same GIF every time, so reactions don't feel canned.
    """
    key = os.environ.get("GIPHY_API_KEY")
    if not key or not query:
        return None
    try:
        resp = requests.get(
            _ENDPOINT,
            params={
                "q": query,
                "api_key": key,
                "limit": limit,
                "rating": "pg-13",   # keep it safe-for-feed
                "bundle": "messaging_non_clips",
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        results = resp.json().get("data") or []
    except (requests.RequestException, ValueError) as exc:
        log.warning("Giphy GIF search failed for %r: %s", query[:60], exc)
        return None

    urls = []
    for r in results:
        url = (((r.get("images") or {}).get("downsized") or {}).get("url")
               or ((r.get("images") or {}).get("original") or {}).get("url"))
        if url:
            urls.append(url)
    if not urls:
        return None
    return random.choice(urls)
