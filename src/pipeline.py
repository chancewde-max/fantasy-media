"""Wires everything together for one poll cycle.

fetch -> detect -> de-dup -> generate -> deliver -> mark fired.
Designed so one failure (a bad ESPN poll, a Claude hiccup) is logged and the
scheduler keeps running.
"""
from __future__ import annotations

import json
import logging
import os

from .config import Config
from .delivery import Delivery, DeliveryError
from .espn_client import ESPNAuthError, ESPNClient, ESPNFetchError
from .events import build_ranking_movement, detect_events
from .generators.claude_client import ClaudeClient
from .generators.instagram import generate_instagram
from .generators.notifications import generate_notification
from .generators.rankings import generate_rankings
from .generators.tweets import generate_tweet
from .state import State

log = logging.getLogger(__name__)

OUT_DIR = "out"
PREV_STANDINGS_FILE = "data/prev_standings.json"


class Pipeline:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.espn = ESPNClient(cfg.league_id, cfg.season, cfg.espn_s2, cfg.swid)
        self.state = State(cfg.state_db)
        self.claude = ClaudeClient(cfg.anthropic_api_key, cfg.anthropic_model)
        self.delivery = Delivery(cfg.webhook_provider, cfg.webhook_url, cfg.groupme_bot_id)
        os.makedirs(OUT_DIR, exist_ok=True)

    def run_once(self) -> None:
        try:
            snap = self.espn.fetch_snapshot()
        except ESPNAuthError as exc:
            log.error("ESPN auth failed: %s", exc)
            self._notify_auth_problem(str(exc))
            return
        except ESPNFetchError as exc:
            log.error("ESPN fetch failed (skipping this cycle): %s", exc)
            return

        log.info("Fetched week %s: %d matchups", snap.week, len(snap.matchups))

        events = detect_events(snap)
        new_events = [e for e in events if self.state.is_new(e.key)]
        log.info("%d events detected, %d new", len(events), len(new_events))

        for event in new_events:
            try:
                self._handle_event(event)
                self.state.mark_fired(event.key)
            except DeliveryError as exc:
                log.error("Delivery failed for %s: %s", event.key, exc)
                # Not marked fired -> retried next cycle.
            except Exception as exc:  # noqa: BLE001
                log.exception("Unexpected error handling %s: %s", event.key, exc)

        # Power rankings once per week when standings are present.
        self._maybe_send_rankings(snap)

    def _handle_event(self, event) -> None:
        cfg = self.cfg
        note = generate_notification(self.claude, event, cfg.tone_notifications)

        # Notifications for every event.
        self.delivery.send(note)

        # Superlative events also get a tweet + IG post for extra flavor.
        if event.kind in {"blowout", "nailbiter", "high", "low", "matchup_final"}:
            tweet = generate_tweet(self.claude, event, cfg.tone_tweets)
            self.delivery.send(f"🐦 @LeagueInsider\n{tweet}")

            ig = generate_instagram(self.claude, event, cfg.tone_instagram, OUT_DIR)
            imgs = [ig["image_path"]] if ig.get("image_path") else []
            self.delivery.send(f"📸 {ig['caption']}", imgs)

    def _maybe_send_rankings(self, snap) -> None:
        if not snap.standings:
            return
        week_key = f"rankings:w{snap.week}"
        if not self.state.is_new(week_key):
            return

        prev = _load_prev_standings()
        rows = build_ranking_movement(snap.standings, prev)
        try:
            result = generate_rankings(
                self.claude, rows, snap.week, self.cfg.tone_rankings, OUT_DIR
            )
            imgs = [result["image_path"]] if result.get("image_path") else []
            self.delivery.send(f"📊 {result['blurb']}", imgs)
            self.state.mark_fired(week_key)
            _save_prev_standings(snap.standings)
        except DeliveryError as exc:
            log.error("Failed to deliver rankings: %s", exc)

    def _notify_auth_problem(self, detail: str) -> None:
        try:
            self.delivery.send(
                "⚠️ Fantasy media bot: your ESPN cookies need refreshing "
                "(espn_s2 / SWID). Re-grab them from your browser and update .env."
            )
        except DeliveryError as exc:
            log.error("Could not even send auth-problem heads-up: %s", exc)


def _load_prev_standings():
    try:
        with open(PREV_STANDINGS_FILE) as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _save_prev_standings(standings) -> None:
    os.makedirs(os.path.dirname(PREV_STANDINGS_FILE), exist_ok=True)
    with open(PREV_STANDINGS_FILE, "w") as fh:
        json.dump(standings, fh)
