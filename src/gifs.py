"""Reaction GIFs via Tenor.

Optional layer: if TENOR_API_KEY is set, we can pull a real animated reaction
GIF for a post so the feed feels like a live group chat. Without the key (or
without network), every function is a safe no-op returning None, and the rest
of the bot carries on with its native graphics.

We return the direct .gif media URL, which the web feed renders like any other
image (an animated GIF is just an image URL).
"""
from __future__ import annotations

import logging
import os
import random

import requests

log = logging.getLogger(__name__)

_ENDPOINT = "https://tenor.googleapis.com/v2/search"


def gifs_enabled() -> bool:
    return bool(os.environ.get("TENOR_API_KEY"))


def search_gif(query: str, *, limit: int = 20, timeout: int = 8) -> str | None:
    """Return a random reaction GIF URL for the query, or None if GIFs aren't
    configured / nothing came back / the request failed.

    Randomizing over a small result set keeps the same query from returning
    the same GIF every time, so reactions don't feel canned.
    """
    key = os.environ.get("TENOR_API_KEY")
    if not key or not query:
        return None
    try:
        resp = requests.get(
            _ENDPOINT,
            params={
                "q": query,
                "key": key,
                "client_key": "fantasy_media",
                "limit": limit,
                "media_filter": "gif",
                "contentfilter": "high",  # keep it safe-for-feed
                "random": "true",
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        results = resp.json().get("results") or []
    except (requests.RequestException, ValueError) as exc:
        log.warning("Tenor GIF search failed for %r: %s", query[:60], exc)
        return None

    urls = []
    for r in results:
        fmt = (r.get("media_formats") or {}).get("gif") or {}
        url = fmt.get("url")
        if url:
            urls.append(url)
    if not urls:
        return None
    return random.choice(urls)
