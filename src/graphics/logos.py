"""Resolve a team's real logo to a data URI for embedding in graphics.

Teams carry a real logo URL in the ESPN export (custom uploads on ESPN's
mystique host, or ESPN vector/CDN SVGs). We fetch it once, cache it on disk
(data/logos) and in memory, and hand back a data: URI the HTML templates drop
straight into a crest. Custom-upload logos live behind ESPN auth, so we send
the league's ESPN cookies when present.

Everything is best-effort: any failure returns None and the template falls
back to a monogram badge, so graphics never break on a missing logo.
"""
from __future__ import annotations

import base64
import logging
import os
from functools import lru_cache

import requests

from .. import league_history

log = logging.getLogger(__name__)

_CACHE_DIR = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "data", "logos")

_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
         ".svg": "image/svg+xml", ".gif": "image/gif", ".webp": "image/webp"}


def _ext_for(url: str, content_type: str = "") -> str:
    low = url.lower()
    for ext in _MIME:
        if low.endswith(ext):
            return ext
    if "svg" in content_type:
        return ".svg"
    if "png" in content_type:
        return ".png"
    if "jpeg" in content_type or "jpg" in content_type:
        return ".jpg"
    return ".png"


def _cache_path(team_abbrev: str, ext: str) -> str:
    safe = "".join(c if c.isalnum() else "_" for c in (team_abbrev or "t"))
    return os.path.join(_CACHE_DIR, f"{safe}{ext}")


def _to_data_uri(raw: bytes, ext: str) -> str:
    mime = _MIME.get(ext, "image/png")
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"


def _espn_cookies() -> dict:
    s2 = os.environ.get("ESPN_S2")
    swid = os.environ.get("SWID")
    ck = {}
    if s2:
        ck["espn_s2"] = s2
    if swid:
        ck["SWID"] = swid
    return ck


@lru_cache(maxsize=64)
def logo_data_uri(team_name: str) -> str | None:
    """Data URI for a team's logo, or None to fall back to a monogram."""
    meta = league_history.team_meta().get((team_name or "").strip().lower())
    if not meta:
        return None
    url = meta.get("logo_url")
    if not url:
        return None
    abbrev = meta.get("abbrev") or team_name

    # disk cache first
    if os.path.isdir(_CACHE_DIR):
        for fn in os.listdir(_CACHE_DIR):
            base, ext = os.path.splitext(fn)
            if base == "".join(c if c.isalnum() else "_" for c in abbrev):
                try:
                    return _to_data_uri(open(os.path.join(_CACHE_DIR, fn), "rb").read(), ext)
                except OSError:
                    break

    try:
        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
        cookies = _espn_cookies() if "mystique" in url or "espn" in url else {}
        resp = requests.get(url, headers=headers, cookies=cookies, timeout=12)
        resp.raise_for_status()
        raw = resp.content
        ext = _ext_for(url, resp.headers.get("Content-Type", ""))
    except requests.RequestException as exc:
        log.warning("Logo fetch failed for %s (%s) — monogram fallback.", team_name, exc)
        return None

    # best-effort disk cache for next time
    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        with open(_cache_path(abbrev, ext), "wb") as fh:
            fh.write(raw)
    except OSError:
        pass
    return _to_data_uri(raw, ext)
