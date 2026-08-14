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
from .generators.insider import cluster_tips, generate_insider_report
from .generators.instagram import generate_instagram
from .generators.notifications import generate_notification
from .generators.rankings import generate_rankings
from .generators.reactions import generate_fan_comments, generate_reaction_tweets
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
        """One ESPN poll cycle: detect events -> publish posts (+ fan reactions).

        The Insider tip batch runs on its OWN daily schedule, not here — see
        run_daily_insider().
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
        if self.delivery is not None:
            text = f"{emoji} {body}" if emoji else body
            imgs = [image_path] if image_path else []
            self.delivery.send(text, imgs)
        return post_id

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

    # ----------------------------------------------------------- daily insider
    def run_daily_insider(self) -> None:
        """Once-a-day batch: publish only rumors corroborated by 2+ managers.

        Clusters pending tips; any cluster of size >= threshold becomes ONE
        anonymous Insider report, followed by a few fan reaction tweets. Tips in
        a published cluster are marked published; un-corroborated tips stay
        pending so they can be matched by a future tip.
        """
        if self.supabase is None:
            return
        try:
            tips = self.supabase.fetch_pending_tips()
        except SupabaseError as exc:
            log.error("Could not fetch tips: %s", exc)
            return

        if not tips:
            log.info("Daily insider: no pending tips.")
            return

        clusters = cluster_tips(
            self.claude, tips, self.cfg.insider_min_corroboration
        )
        log.info(
            "Daily insider: %d pending tips -> %d corroborated cluster(s).",
            len(tips), len(clusters),
        )

        for cluster in clusters:
            try:
                self._publish_insider_cluster(cluster)
            except SupabaseError as exc:
                log.error("Failed to publish insider cluster: %s", exc)
            except Exception as exc:  # noqa: BLE001
                log.exception("Unexpected error on insider cluster: %s", exc)

    def _publish_insider_cluster(self, cluster: dict) -> None:
        summary = cluster.get("summary") or "the latest league buzz"
        report = generate_insider_report(self.claude, summary, self.cfg.tone_default)

        # De-dup the report itself off the sorted tip ids in the cluster.
        cluster_key = "insider:" + "+".join(sorted(cluster["tip_ids"]))
        post_id = self._publish(
            "insider_report", report, "@LeagueInsider", "🕵️",
            event_key=cluster_key,
            metadata={"source": "corroborated_tips", "corroboration": len(cluster["tip_ids"])},
        )

        # Mark all tips in the cluster as published, linked to the report.
        for tip_id in cluster["tip_ids"]:
            try:
                self.supabase.mark_tip(tip_id, "published", post_id)
            except SupabaseError as exc:
                log.warning("Could not mark tip %s published: %s", tip_id, exc)

        if post_id is None:
            return  # duplicate report, don't spam reaction tweets again

        # Fan/reporter reaction tweets talking about the report.
        try:
            tweets = generate_reaction_tweets(
                self.claude, report, self.cfg.tone_default,
                n=self.cfg.reaction_tweets_per_report,
            )
            for i, tw in enumerate(tweets):
                self._publish(
                    "tweet", tw["text"], tw["handle"], "🐦",
                    event_key=f"{cluster_key}:reax{i}",
                    metadata={"reacting_to": post_id},
                    with_fan_comments=False,
                )
        except Exception as exc:  # noqa: BLE001
            log.warning("Reaction tweet generation failed: %s", exc)

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
