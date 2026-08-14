"""Entrypoint. Loads config, configures logging, starts the scheduler."""
from __future__ import annotations

import logging
import sys

from src.config import Config, ConfigError
from src.scheduler import run


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    # espn-api / urllib3 are noisy; keep them at WARNING.
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def main() -> int:
    try:
        cfg = Config.load()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        print("Copy .env.example to .env and fill in the values.", file=sys.stderr)
        return 2

    _configure_logging(cfg.log_level)
    log = logging.getLogger("main")
    log.info(
        "Starting fantasy media bot — league=%s season=%s provider=%s",
        cfg.league_id, cfg.season, cfg.webhook_provider,
    )
    run(cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
