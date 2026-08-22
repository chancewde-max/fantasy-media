"""Player / team hero images for graphics.

Two sources, in priority order:
  1. A manual cutout you drop in data/cutouts/<TEAM_ABBREV>.png (or .jpg) — use
     this for hand-made transparent action cutouts. Highest quality, fully in
     your control, shows up immediately.
  2. The real ESPN player headshot for a team's marquee rostered player
     (transparent PNG from ESPN's CDN — the same image the ESPN app uses).

Everything is best-effort and cached; any miss returns None and the template
falls back to the team logo / monogram crest, so graphics never break.
"""
from __future__ import annotations

import base64
import logging
import os
from functools import lru_cache

import requests

from .. import league_history

log = logging.getLogger(__name__)

_CUTOUT_DIR = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "data", "cutouts")
_HEADSHOT = "https://a.espncdn.com/i/headshots/nfl/players/full/{id}.png"
_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


def _data_uri(raw: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"


def _abbrev(team_name: str) -> str:
    meta = league_history.team_meta().get((team_name or "").strip().lower()) or {}
    return meta.get("abbrev") or "".join(c for c in team_name if c.isalnum())[:4]


def team_cutout(team_name: str) -> str | None:
    """A manually-uploaded cutout for this team, if present."""
    abbrev = "".join(c if c.isalnum() else "_" for c in _abbrev(team_name))
    if not os.path.isdir(_CUTOUT_DIR):
        return None
    for fn in os.listdir(_CUTOUT_DIR):
        base, ext = os.path.splitext(fn)
        if base.lower() == abbrev.lower() and ext.lower() in _MIME:
            try:
                return _data_uri(open(os.path.join(_CUTOUT_DIR, fn), "rb").read(), _MIME[ext.lower()])
            except OSError:
                return None
    return None


@lru_cache(maxsize=128)
def headshot(espn_id: int | str) -> str | None:
    """Real ESPN player headshot as a data URI, or None."""
    if not espn_id:
        return None
    try:
        resp = requests.get(
            _HEADSHOT.format(id=espn_id),
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
            timeout=10,
        )
        resp.raise_for_status()
        if not resp.content or "image" not in resp.headers.get("Content-Type", "image/png"):
            return None
        return _data_uri(resp.content, "image/png")
    except requests.RequestException as exc:
        log.warning("Headshot fetch failed for %s: %s", espn_id, exc)
        return None


def hero_for_team(team_name: str, year: int | None = None) -> tuple[str | None, str]:
    """(hero_data_uri, player_name) for a team — manual cutout first, then the
    marquee player's headshot. player_name is '' for a manual cutout."""
    cut = team_cutout(team_name)
    if cut:
        return cut, ""
    mp = league_history.marquee_player(team_name, year)
    if mp:
        img = headshot(mp["espn_id"])
        if img:
            return img, mp["name"]
    return None, ""
