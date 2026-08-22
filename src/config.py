"""Loads configuration from environment / .env file.

All secrets and tunables live here so the rest of the app never reads
os.environ directly. Nothing in here is ever logged.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

VALID_TONES = {"hype", "roast"}
VALID_PROVIDERS = {"discord", "slack", "groupme"}


def _get(name: str, default: str | None = None, required: bool = False) -> str:
    val = os.environ.get(name, default)
    if required and (val is None or val == ""):
        raise ConfigError(f"Missing required config value: {name}")
    return val if val is not None else ""


def _get_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        raise ConfigError(f"Config value {name} must be an integer, got {raw!r}")


def _get_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_int_list(name: str, default: list[int]) -> list[int]:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return [int(p.strip()) for p in raw.split(",") if p.strip()]
    except ValueError:
        raise ConfigError(f"Config value {name} must be comma-separated integers, got {raw!r}")


def _tone(name: str, fallback: str) -> str:
    val = os.environ.get(name, fallback).strip().lower()
    if val not in VALID_TONES:
        raise ConfigError(f"{name} must be one of {VALID_TONES}, got {val!r}")
    return val


def _current_nfl_season(today: datetime | None = None) -> int:
    """The NFL/fantasy season a given date falls in. A season (e.g. 2026)
    runs from around September through the following February, so January
    and February still belong to the PREVIOUS calendar year's season.
    Lets SEASON default to "auto" and roll over on its own every year
    instead of needing a manual bump."""
    d = today or datetime.now(timezone.utc)
    return d.year if d.month >= 3 else d.year - 1


class ConfigError(RuntimeError):
    pass


@dataclass
class Config:
    # ESPN
    league_id: int
    season: int
    espn_s2: str
    swid: str

    # Claude
    anthropic_api_key: str
    anthropic_model: str

    # Delivery
    post_target: str          # supabase | webhook | both
    webhook_provider: str
    webhook_url: str
    groupme_bot_id: str

    # Supabase (feed database for the app)
    supabase_url: str
    supabase_service_key: str
    supabase_league_id: str
    supabase_bucket: str

    # Tone (per content type)
    tone_default: str
    tone_notifications: str
    tone_tweets: str
    tone_instagram: str
    tone_rankings: str

    # Scheduling
    poll_interval_minutes: int
    run_once: bool

    # Insider + fan-reaction behavior
    tip_check_interval_minutes: int  # how often to check for new tips to report immediately
    insider_fabricate_hours: list[int]  # UTC hours to invent a rumor if nothing real came in
    fan_comments_per_post: int
    reaction_tweets_per_report: int

    # Web Push (optional — silently disabled if no key is set)
    vapid_private_key: str
    vapid_subject: str

    # Display
    league_timezone: str  # IANA tz name, e.g. "America/Chicago" — for date/time text

    # Misc
    state_db: str
    log_level: str

    @classmethod
    def load(cls) -> "Config":
        provider = _get("WEBHOOK_PROVIDER", "discord").strip().lower()
        if provider not in VALID_PROVIDERS:
            raise ConfigError(
                f"WEBHOOK_PROVIDER must be one of {VALID_PROVIDERS}, got {provider!r}"
            )

        default_tone = _tone("TONE", "roast")

        post_target = _get("POST_TARGET", "supabase").strip().lower()
        if post_target not in {"supabase", "webhook", "both"}:
            raise ConfigError(
                f"POST_TARGET must be supabase|webhook|both, got {post_target!r}"
            )

        season_raw = os.environ.get("SEASON", "auto").strip()
        if season_raw == "" or season_raw.lower() == "auto":
            season = _current_nfl_season()
        else:
            try:
                season = int(season_raw)
            except ValueError:
                raise ConfigError(f"SEASON must be an integer or 'auto', got {season_raw!r}")

        cfg = cls(
            league_id=_get_int("LEAGUE_ID", 0),
            season=season,
            espn_s2=_get("ESPN_S2", required=True),
            swid=_get("SWID", required=True),
            anthropic_api_key=_get("ANTHROPIC_API_KEY", required=True),
            anthropic_model=_get("ANTHROPIC_MODEL", "claude-sonnet-5"),
            post_target=post_target,
            webhook_provider=provider,
            webhook_url=_get("WEBHOOK_URL", ""),
            groupme_bot_id=_get("GROUPME_BOT_ID", ""),
            supabase_url=_get("SUPABASE_URL", ""),
            supabase_service_key=_get("SUPABASE_SERVICE_KEY", ""),
            supabase_league_id=_get("SUPABASE_LEAGUE_ID", ""),
            supabase_bucket=_get("SUPABASE_BUCKET", "media"),
            tone_default=default_tone,
            tone_notifications=_tone("TONE_NOTIFICATIONS", default_tone),
            tone_tweets=_tone("TONE_TWEETS", default_tone),
            tone_instagram=_tone("TONE_INSTAGRAM", default_tone),
            tone_rankings=_tone("TONE_RANKINGS", "hype"),
            poll_interval_minutes=_get_int("POLL_INTERVAL", 60),
            run_once=_get_bool("RUN_ONCE", False),
            tip_check_interval_minutes=_get_int("TIP_CHECK_INTERVAL_MINUTES", 5),
            insider_fabricate_hours=_get_int_list("INSIDER_FABRICATE_HOURS", [7, 12, 18]),
            fan_comments_per_post=_get_int("FAN_COMMENTS_PER_POST", 2),
            reaction_tweets_per_report=_get_int("REACTION_TWEETS_PER_REPORT", 6),
            vapid_private_key=_get("VAPID_PRIVATE_KEY", ""),
            vapid_subject=_get("VAPID_SUBJECT", "mailto:admin@example.com"),
            league_timezone=_get("LEAGUE_TIMEZONE", "America/Chicago"),
            state_db=_get("STATE_DB", "data/state.db"),
            log_level=_get("LOG_LEVEL", "INFO").upper(),
        )

        if cfg.league_id == 0:
            raise ConfigError("LEAGUE_ID must be set")
        if post_target in {"supabase", "both"}:
            if not cfg.supabase_url:
                raise ConfigError("SUPABASE_URL is required when POST_TARGET includes supabase")
            if not cfg.supabase_service_key:
                raise ConfigError("SUPABASE_SERVICE_KEY is required when POST_TARGET includes supabase")
            if not cfg.supabase_league_id:
                raise ConfigError("SUPABASE_LEAGUE_ID is required when POST_TARGET includes supabase")

        if post_target in {"webhook", "both"}:
            if provider == "groupme":
                if not cfg.groupme_bot_id:
                    raise ConfigError("GROUPME_BOT_ID is required when WEBHOOK_PROVIDER=groupme")
            elif not cfg.webhook_url:
                raise ConfigError("WEBHOOK_URL is required for discord/slack")

        return cfg
