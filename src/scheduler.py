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
    # Report each manager tip as its own Insider drop shortly after it's submitted.
    scheduler.add_job(
        _safe_tip_check,
        "interval",
        minutes=cfg.tip_check_interval_minutes,
        args=[pipeline],
        id="tip_check",
        max_instances=1,
        coalesce=True,
    )
    # If nothing real has come in by these checkpoints, invent a rumor instead.
    scheduler.add_job(
        _safe_fabrication,
        "cron",
        hour=",".join(str(h) for h in cfg.insider_fabricate_hours),
        minute=0,
        args=[pipeline],
        id="insider_fabrication",
        max_instances=1,
        coalesce=True,
    )
    log.info(
        "Scheduler started — polling every %d min, checking tips every %d min, "
        "Insider fabrication checkpoints at %s UTC. Ctrl-C to stop.",
        cfg.poll_interval_minutes, cfg.tip_check_interval_minutes,
        ", ".join(f"{h:02d}:00" for h in cfg.insider_fabricate_hours),
    )
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Shutting down scheduler.")


def _safe_cycle(pipeline: Pipeline) -> None:
    try:
        pipeline.run_once()
    except Exception as exc:  # noqa: BLE001 - never let the scheduler die
        log.exception("Poll cycle raised, continuing: %s", exc)


def _safe_tip_check(pipeline: Pipeline) -> None:
    try:
        pipeline.check_pending_tips()
    except Exception as exc:  # noqa: BLE001 - never let the scheduler die
        log.exception("Tip check raised, continuing: %s", exc)


def _safe_fabrication(pipeline: Pipeline) -> None:
    try:
        pipeline.run_scheduled_fabrication()
    except Exception as exc:  # noqa: BLE001 - never let the scheduler die
        log.exception("Insider fabrication raised, continuing: %s", exc)
