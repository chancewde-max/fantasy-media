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
from datetime import datetime, timedelta, timezone

from .config import Config
from .delivery import Delivery, DeliveryError
from .espn_client import ESPNAuthError, ESPNClient, ESPNFetchError
from .events import build_ranking_movement, detect_events
from .generators.articles import generate_article
from .generators.claude_client import ClaudeClient
from .generators.insider import generate_fabricated_rumor, generate_insider_report
from .generators.instagram import generate_instagram
from .generators.notifications import generate_notification
from .generators.rankings import generate_rankings
from .generators.reactions import generate_fan_comments, generate_reaction_tweets
from .generators.tweets import generate_tweet
from .push import notification_for, send_to_subscriptions
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

        self.push_enabled = bool(cfg.vapid_private_key) and self.supabase is not None

        os.makedirs(OUT_DIR, exist_ok=True)

    # ------------------------------------------------------------------ cycle
    def run_once(self) -> None:
        """One ESPN poll cycle: detect events -> publish posts (+ fan reactions).

        Insider tip reporting runs on its OWN schedule, not here — see
        check_pending_tips() and run_scheduled_fabrication().
        """
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
        with_fan_comments: bool = True,
    ) -> str | None:
        """Fan out one post to Supabase (feed) and/or the chat webhook.

        Returns the created Supabase post id (or None). When a post lands in the
        feed, seed a couple of AI fan comments so it feels alive.
        """
        post_id = None
        if self.supabase is not None:
            post_id = self.supabase.insert_post(
                post_type=post_type,
                body=body,
                author_handle=author_handle,
                image_path=image_path,
                event_key=event_key,
                metadata=metadata,
            )
            if post_id and with_fan_comments and self.cfg.fan_comments_per_post > 0:
                self._add_fan_comments(post_id, body)
            if post_id and self.push_enabled:
                self._send_push(post_type, author_handle, body)
        if self.delivery is not None:
            text = f"{emoji} {body}" if emoji else body
            imgs = [image_path] if image_path else []
            self.delivery.send(text, imgs)
        return post_id

    def _send_push(self, post_type: str, author_handle: str, body: str) -> None:
        try:
            subs = self.supabase.fetch_push_subscriptions()
            if not subs:
                return
            title, snippet = notification_for(post_type, author_handle, body)
            dead = send_to_subscriptions(
                subs, title, snippet, self.cfg.vapid_private_key, self.cfg.vapid_subject,
            )
            for endpoint in dead:
                try:
                    self.supabase.delete_push_subscription(endpoint)
                except SupabaseError:
                    pass
        except Exception as exc:  # noqa: BLE001
            log.warning("Push notification failed: %s", exc)

    def _add_fan_comments(self, post_id: str, post_body: str) -> None:
        try:
            comments = generate_fan_comments(
                self.claude, post_body, self.cfg.tone_default,
                n=self.cfg.fan_comments_per_post,
            )
            for c in comments:
                self.supabase.insert_fan_comment(post_id, c["handle"], c["text"])
        except SupabaseError as exc:
            log.warning("Could not add fan comments to %s: %s", post_id, exc)
        except Exception as exc:  # noqa: BLE001
            log.warning("Fan comment generation failed: %s", exc)

    def _handle_event(self, event) -> None:
        cfg = self.cfg

        note = generate_notification(self.claude, event, cfg.tone_notifications)
        metadata = {**event.data, **self._article_metadata(f"{event.title}: {note}")}
        self._publish(
            "espn_notification", note, "ESPN", "🚨",
            event_key=f"{event.key}:note", metadata=metadata,
        )

        if event.kind in {"blowout", "nailbiter", "high", "low", "matchup_final"}:
            tweet = generate_tweet(self.claude, event, cfg.tone_tweets)
            self._publish(
                "tweet", tweet, "@DiannaRussinni", "🐦",
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

    # -------------------------------------------------------------- insider
    def check_pending_tips(self) -> None:
        """Report every pending tip as its own Insider drop, right away.

        Called on a short interval (TIP_CHECK_INTERVAL_MINUTES) so a manager's
        tip shows up in the feed shortly after they submit it — no waiting for
        a second matching tip.
        """
        if self.supabase is None:
            return
        try:
            tips = self.supabase.fetch_pending_tips()
        except SupabaseError as exc:
            log.error("Could not fetch tips: %s", exc)
            return

        if not tips:
            return

        log.info("%d pending tip(s) to report.", len(tips))
        for tip in tips:
            try:
                self._publish_tip_report(tip)
            except SupabaseError as exc:
                log.error("Failed to publish tip report: %s", exc)
            except Exception as exc:  # noqa: BLE001
                log.exception("Unexpected error reporting tip %s: %s", tip.get("id"), exc)

    def _publish_tip_report(self, tip: dict) -> None:
        report = generate_insider_report(self.claude, tip["raw_text"], self.cfg.tone_default)

        tip_key = f"insider:tip:{tip['id']}"
        metadata = {"source": "tip", **self._article_metadata(report)}
        post_id = self._publish(
            "insider_report", report, "@DiannaRussinni", "🕵️",
            event_key=tip_key, metadata=metadata,
        )

        try:
            self.supabase.mark_tip(tip["id"], "published", post_id)
        except SupabaseError as exc:
            log.warning("Could not mark tip %s published: %s", tip["id"], exc)

        if post_id is None:
            return  # duplicate report, don't spam reaction tweets again

        self.state.set_meta("insider:last_real_report_at", _utcnow_iso())
        self._publish_reaction_tweets(report, post_id, tip_key)

    def _article_metadata(self, context: str) -> dict:
        """A short (headline + one paragraph) companion piece giving color on
        an ESPN alert or Insider report, tucked into the post's metadata so
        the card can reveal it as a "read the full story" popup instead of
        cluttering the feed as its own post."""
        try:
            article = generate_article(self.claude, context, self.cfg.tone_default)
            return {"article": article} if article.get("body") else {}
        except Exception as exc:  # noqa: BLE001
            log.warning("Article generation failed: %s", exc)
            return {}

    def _publish_reaction_tweets(self, report: str, post_id: str, key: str) -> None:
        """Fan reaction tweets to a just-published Insider report. Claude reads
        how inflammatory the report is and calibrates tone — mild reports get
        an honor-system defense ('yall reaching'), juicy ones get roasted."""
        try:
            tweets = generate_reaction_tweets(
                self.claude, report, self.cfg.tone_default,
                n=self.cfg.reaction_tweets_per_report,
            )
            for i, tw in enumerate(tweets):
                self._publish(
                    "tweet", tw["text"], tw["handle"], "🐦",
                    event_key=f"{key}:reax{i}",
                    metadata={"reacting_to": post_id},
                )
        except Exception as exc:  # noqa: BLE001
            log.warning("Reaction tweet generation failed: %s", exc)

    def run_scheduled_fabrication(self) -> None:
        """Scheduled checkpoint (INSIDER_FABRICATE_HOURS, default 7/12/18 UTC):
        if no real tip has been reported since the previous checkpoint, invent
        a rumor so the Insider still drops something.
        """
        if self.supabase is None:
            return

        now = datetime.now(timezone.utc)
        slot_key = f"insider:fab:{now:%Y-%m-%d}:{now:%H}"
        if not self.state.is_new(slot_key):
            return
        self.state.mark_fired(slot_key)

        checkpoint = _previous_checkpoint(self.cfg.insider_fabricate_hours, now)
        last_real = self.state.get_meta("insider:last_real_report_at")
        if last_real and datetime.fromisoformat(last_real) >= checkpoint:
            log.info("A real tip already dropped since %s — skipping fabrication.", checkpoint)
            return

        report = generate_fabricated_rumor(self.claude, self.cfg.tone_default)
        metadata = {"source": "fabricated", **self._article_metadata(report)}
        post_id = self._publish(
            "insider_report", report, "@DiannaRussinni", "🕵️",
            event_key=slot_key, metadata=metadata,
        )
        if post_id is not None:
            self._publish_reaction_tweets(report, post_id, slot_key)

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


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _previous_checkpoint(hours: list[int], now: datetime) -> datetime:
    """The most recent scheduled checkpoint at or before `now` (today or,
    if none has happened yet today, the last one from yesterday)."""
    hours = sorted(hours)
    todays = [
        h for h in hours
        if now.replace(hour=h, minute=0, second=0, microsecond=0) <= now
    ]
    if todays:
        return now.replace(hour=todays[-1], minute=0, second=0, microsecond=0)
    yesterday = now - timedelta(days=1)
    return yesterday.replace(hour=hours[-1], minute=0, second=0, microsecond=0)
