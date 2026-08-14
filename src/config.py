"""Loads configuration from environment / .env file.

All secrets and tunables live here so the rest of the app never reads
os.environ directly. Nothing in here is ever logged.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

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


def _tone(name: str, fallback: str) -> str:
    val = os.environ.get(name, fallback).strip().lower()
    if val not in VALID_TONES:
        raise ConfigError(f"{name} must be one of {VALID_TONES}, got {val!r}")
    return val


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
    webhook_provider: str
    webhook_url: str
    groupme_bot_id: str

    # Tone (per content type)
    tone_default: str
    tone_notifications: str
    tone_tweets: str
    tone_instagram: str
    tone_rankings: str

    # Scheduling
    poll_interval_minutes: int
    run_once: bool

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

        cfg = cls(
            league_id=_get_int("LEAGUE_ID", 0),
            season=_get_int("SEASON", 0),
            espn_s2=_get("ESPN_S2", required=True),
            swid=_get("SWID", required=True),
            anthropic_api_key=_get("ANTHROPIC_API_KEY", required=True),
            anthropic_model=_get("ANTHROPIC_MODEL", "claude-sonnet-5"),
            webhook_provider=provider,
            webhook_url=_get("WEBHOOK_URL", ""),
            groupme_bot_id=_get("GROUPME_BOT_ID", ""),
            tone_default=default_tone,
            tone_notifications=_tone("TONE_NOTIFICATIONS", default_tone),
            tone_tweets=_tone("TONE_TWEETS", default_tone),
            tone_instagram=_tone("TONE_INSTAGRAM", default_tone),
            tone_rankings=_tone("TONE_RANKINGS", "hype"),
            poll_interval_minutes=_get_int("POLL_INTERVAL", 60),
            run_once=_get_bool("RUN_ONCE", False),
            state_db=_get("STATE_DB", "data/state.db"),
            log_level=_get("LOG_LEVEL", "INFO").upper(),
        )

        if cfg.league_id == 0:
            raise ConfigError("LEAGUE_ID must be set")
        if cfg.season == 0:
            raise ConfigError("SEASON must be set")
        if provider == "groupme":
            if not cfg.groupme_bot_id:
                raise ConfigError("GROUPME_BOT_ID is required when WEBHOOK_PROVIDER=groupme")
        elif not cfg.webhook_url:
            raise ConfigError("WEBHOOK_URL is required for discord/slack")

        return cfg
