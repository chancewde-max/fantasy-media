"""One-off entrypoint: publish the historical season backfill, then exit.

Run this instead of main.py to seed past-season content (real AI-generated
copy + real Storage-hosted graphics, via the same SupabaseWriter the live
pipeline uses). Safe to re-run — each post has a stable event_key, so already
-published posts are skipped.
"""
from __future__ import annotations

import logging
import sys

from src.config import Config, ConfigError
from src.generators.claude_client import ClaudeClient
from src.historical import run_backfill
from src.supabase_writer import SupabaseWriter


def main() -> int:
    try:
        cfg = Config.load()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    logging.basicConfig(
        level=getattr(logging, cfg.log_level, logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    log = logging.getLogger("backfill")

    if not cfg.supabase_url or not cfg.supabase_service_key or not cfg.supabase_league_id:
        print("SUPABASE_URL / SUPABASE_SERVICE_KEY / SUPABASE_LEAGUE_ID are required.", file=sys.stderr)
        return 2

    claude = ClaudeClient(cfg.anthropic_api_key, cfg.anthropic_model)
    supabase = SupabaseWriter(
        cfg.supabase_url, cfg.supabase_service_key, cfg.supabase_league_id, cfg.supabase_bucket,
    )

    log.info("Starting historical backfill...")
    run_backfill(claude, supabase, tone=cfg.tone_default)
    log.info("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
