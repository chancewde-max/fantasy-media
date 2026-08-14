"""Always-on polling scheduler.

Uses APScheduler's blocking scheduler to poll on a configurable interval.
One bad cycle is caught inside Pipeline.run_once so the loop never dies.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from .config import Config
from .pipeline import Pipeline

log = logging.getLogger(__name__)


def run(cfg: Config) -> None:
    pipeline = Pipeline(cfg)

    # Run immediately on start, then on the interval.
    log.info("Initial poll...")
    _safe_cycle(pipeline)

    if cfg.run_once:
        log.info("RUN_ONCE set — exiting after one cycle.")
        return

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        _safe_cycle,
        "interval",
        minutes=cfg.poll_interval_minutes,
        args=[pipeline],
        id="poll",
        max_instances=1,
        coalesce=True,
    )
    log.info("Scheduler started — polling every %d min. Ctrl-C to stop.",
             cfg.poll_interval_minutes)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Shutting down scheduler.")


def _safe_cycle(pipeline: Pipeline) -> None:
    try:
        pipeline.run_once()
    except Exception as exc:  # noqa: BLE001 - never let the scheduler die
        log.exception("Poll cycle raised, continuing: %s", exc)
