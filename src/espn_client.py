"""Thin wrapper around espn-api.

Every ESPN call is defensive: the wrapper is unofficial and endpoints can
change or auth can expire at any time. We surface two clear failure modes
(auth vs. everything else) so the scheduler can react instead of crashing.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)


class ESPNAuthError(RuntimeError):
    """Cookies expired / rejected — user needs to refresh espn_s2 + SWID."""


class ESPNFetchError(RuntimeError):
    """Any other failure talking to ESPN (endpoint change, network, etc.)."""


@dataclass
class LeagueSnapshot:
    """Plain-data view of the league at one point in time.

    Kept deliberately dumb (no espn-api objects leak past this module) so the
    rest of the app is easy to test and unaffected by wrapper changes.
    """
    week: int
    matchups: list[dict[str, Any]]
    standings: list[dict[str, Any]]
    transactions: list[dict[str, Any]]
    draft_date_ms: int | None = None
    season: int = 0


class ESPNClient:
    def __init__(self, league_id: int, season: int, espn_s2: str, swid: str):
        self._league_id = league_id
        self._season = season
        self._espn_s2 = espn_s2
        self._swid = swid
        self._league = None

    def _connect(self):
        # Imported lazily so config errors surface before the heavy import.
        from espn_api.football import League

        try:
            self._league = League(
                league_id=self._league_id,
                year=self._season,
                espn_s2=self._espn_s2,
                swid=self._swid,
            )
        except Exception as exc:  # noqa: BLE001 - wrapper raises broad types
            msg = str(exc).lower()
            if any(t in msg for t in ("401", "403", "unauthorized", "cookie", "private")):
                raise ESPNAuthError(
                    "ESPN rejected the request — your espn_s2 / SWID cookies "
                    "likely expired. Re-grab them from your browser."
                ) from exc
            raise ESPNFetchError(f"Failed to connect to ESPN league: {exc}") from exc

    def fetch_snapshot(self) -> LeagueSnapshot:
        """Fetch current league state as a plain LeagueSnapshot."""
        if self._league is None:
            self._connect()
        league = self._league

        try:
            week = getattr(league, "current_week", 0) or 0
            matchups = self._read_matchups(league, week)
            standings = self._read_standings(league)
            transactions = self._read_transactions(league)
            draft_date_ms = self._read_draft_date(league)
        except (ESPNAuthError, ESPNFetchError):
            raise
        except Exception as exc:  # noqa: BLE001
            raise ESPNFetchError(f"Failed reading league state: {exc}") from exc

        return LeagueSnapshot(
            week=week,
            matchups=matchups,
            standings=standings,
            transactions=transactions,
            draft_date_ms=draft_date_ms,
            season=self._season,
        )

    # --- internal readers, each guarded ---

    @staticmethod
    def _team_name(team: Any) -> str:
        return getattr(team, "team_name", None) or getattr(team, "team_abbrev", "Unknown")

    def _read_matchups(self, league: Any, week: int) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        if not week:
            return out
        try:
            box = league.box_scores(week)
        except Exception as exc:  # noqa: BLE001
            log.warning("box_scores(%s) failed: %s", week, exc)
            return out
        for m in box:
            home, away = m.home_team, m.away_team
            if home is None or away is None:
                continue
            home_score = float(getattr(m, "home_score", 0) or 0)
            away_score = float(getattr(m, "away_score", 0) or 0)
            # A matchup is "final" once scores are in and no minutes remain.
            final = home_score > 0 or away_score > 0
            out.append(
                {
                    "week": week,
                    "home": self._team_name(home),
                    "away": self._team_name(away),
                    "home_score": round(home_score, 2),
                    "away_score": round(away_score, 2),
                    "final": final,
                }
            )
        return out

    def _read_standings(self, league: Any) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        try:
            teams = league.standings()
        except Exception as exc:  # noqa: BLE001
            log.warning("standings() failed, falling back to league.teams: %s", exc)
            teams = getattr(league, "teams", []) or []
        for rank, team in enumerate(teams, start=1):
            out.append(
                {
                    "rank": rank,
                    "team": self._team_name(team),
                    "wins": int(getattr(team, "wins", 0) or 0),
                    "losses": int(getattr(team, "losses", 0) or 0),
                    "points_for": round(float(getattr(team, "points_for", 0) or 0), 2),
                }
            )
        return out

    def _read_draft_date(self, league: Any) -> int | None:
        """Scheduled draft date (epoch ms), straight from the raw settings
        payload — espn-api's parsed Settings object doesn't surface it."""
        try:
            data = league.espn_request.get_league()
            date_ms = data.get("settings", {}).get("draftSettings", {}).get("date")
            return int(date_ms) if date_ms else None
        except Exception as exc:  # noqa: BLE001
            log.warning("Could not read draft date: %s", exc)
            return None

    def _read_transactions(self, league: Any) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        try:
            activity = league.recent_activity(size=25)
        except Exception as exc:  # noqa: BLE001
            log.warning("recent_activity() failed: %s", exc)
            return out
        for act in activity:
            actions = getattr(act, "actions", []) or []
            parts = []
            for team, action, player, *_ in (a + (None,) * 3 for a in actions):
                team_name = self._team_name(team) if team else "?"
                pname = getattr(player, "name", None) or str(player)
                parts.append(f"{team_name} {action} {pname}")
            if not parts:
                continue
            out.append(
                {
                    "id": str(getattr(act, "date", "")) + "|" + " ; ".join(parts),
                    "date": getattr(act, "date", 0),
                    "summary": " ; ".join(parts),
                }
            )
        return out
