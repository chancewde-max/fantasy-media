"""Wires everything together for one poll cycle.

fetch -> detect -> de-dup -> generate -> publish -> mark fired,
plus: pull manager tips -> Insider report -> publish.

Publishing fans out to Supabase (the app feed) and/or a chat webhook,
controlled by POST_TARGET. One failure (a bad ESPN poll, a Claude hiccup,
a Supabase blip) is logged and the scheduler keeps running.
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
from .generators.insider import generate_insider_report
from .generators.instagram import generate_instagram
from .generators.notifications import generate_notification
from .generators.rankings import generate_rankings
from .generators.tweets import generate_tweet
from .state import State
from .supabase_writer import SupabaseError, SupabaseWriter

log = logging.getLogger(__name__)

OUT_DIR = "out"
PREV_STANDINGS_FILE = "data/prev_standings.json"


class Pipeline:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.espn = ESPNClient(cfg.league_id, cfg.season, cfg.espn_s2, cfg.swid)
        self.state = State(cfg.state_db)
        self.claude = ClaudeClient(cfg.anthropic_api_key, cfg.anthropic_model)

        self.supabase = None
        if cfg.post_target in {"supabase", "both"}:
            self.supabase = SupabaseWriter(
                cfg.supabase_url,
                cfg.supabase_service_key,
                cfg.supabase_league_id,
                cfg.supabase_bucket,
            )

        self.delivery = None
        if cfg.post_target in {"webhook", "both"}:
            self.delivery = Delivery(
                cfg.webhook_provider, cfg.webhook_url, cfg.groupme_bot_id
            )

        os.makedirs(OUT_DIR, exist_ok=True)

    # ------------------------------------------------------------------ cycle
    def run_once(self) -> None:
        # Manager tips first — they don't depend on ESPN being reachable.
        self._process_tips()

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
            except (DeliveryError, SupabaseError) as exc:
                log.error("Publish failed for %s: %s", event.key, exc)
                # Not marked fired -> retried next cycle.
            except Exception as exc:  # noqa: BLE001
                log.exception("Unexpected error handling %s: %s", event.key, exc)

        self._maybe_send_rankings(snap)

    # -------------------------------------------------------------- publishing
    def _publish(
        self,
        post_type: str,
        body: str,
        author_handle: str,
        emoji: str,
        image_path: str | None = None,
        event_key: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Fan out one post to Supabase (feed) and/or the chat webhook."""
        if self.supabase is not None:
            self.supabase.insert_post(
                post_type=post_type,
                body=body,
                author_handle=author_handle,
                image_path=image_path,
                event_key=event_key,
                metadata=metadata,
            )
        if self.delivery is not None:
            text = f"{emoji} {body}" if emoji else body
            imgs = [image_path] if image_path else []
            self.delivery.send(text, imgs)

    def _handle_event(self, event) -> None:
        cfg = self.cfg

        note = generate_notification(self.claude, event, cfg.tone_notifications)
        self._publish(
            "espn_notification", note, "ESPN", "🚨",
            event_key=f"{event.key}:note", metadata=event.data,
        )

        if event.kind in {"blowout", "nailbiter", "high", "low", "matchup_final"}:
            tweet = generate_tweet(self.claude, event, cfg.tone_tweets)
            self._publish(
                "tweet", tweet, "@LeagueInsider", "🐦",
                event_key=f"{event.key}:tweet", metadata=event.data,
            )

            ig = generate_instagram(self.claude, event, cfg.tone_instagram, OUT_DIR)
            self._publish(
                "instagram", ig["caption"], "@LeagueGram", "📸",
                image_path=ig.get("image_path"),
                event_key=f"{event.key}:ig", metadata=event.data,
            )

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
            self._publish(
                "instagram", result["blurb"], "@LeagueGram", "📊",
                image_path=result.get("image_path"),
                event_key=week_key, metadata={"week": snap.week, "rankings": rows},
            )
            self.state.mark_fired(week_key)
            _save_prev_standings(snap.standings)
        except (DeliveryError, SupabaseError) as exc:
            log.error("Failed to publish rankings: %s", exc)

    # -------------------------------------------------------------------- tips
    def _process_tips(self) -> None:
        """Pull pending manager tips, turn each into an anonymous Insider post."""
        if self.supabase is None:
            return
        try:
            tips = self.supabase.fetch_pending_tips()
        except SupabaseError as exc:
            log.error("Could not fetch tips: %s", exc)
            return

        for tip in tips:
            try:
                report = generate_insider_report(
                    self.claude, tip["raw_text"], self.cfg.tone_default
                )
                self.supabase.insert_post(
                    post_type="insider_report",
                    body=report,
                    author_handle="@LeagueInsider",
                    event_key=f"tip:{tip['id']}",
                    metadata={"source": "manager_tip"},
                )
                self.supabase.mark_tip(tip["id"], "published")
                log.info("Published insider report from tip %s", tip["id"])
            except SupabaseError as exc:
                log.error("Failed to publish tip %s: %s", tip["id"], exc)
            except Exception as exc:  # noqa: BLE001
                log.exception("Unexpected error on tip %s: %s", tip["id"], exc)

    def _notify_auth_problem(self, detail: str) -> None:
        msg = (
            "⚠️ Fantasy media bot: your ESPN cookies need refreshing "
            "(espn_s2 / SWID). Re-grab them from your browser and update config."
        )
        try:
            self._publish("espn_notification", msg, "System", "⚠️",
                          event_key=None, metadata={"kind": "auth_error"})
        except (DeliveryError, SupabaseError) as exc:
            log.error("Could not send auth-problem heads-up: %s", exc)


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
