"""APScheduler init — started in FastAPI lifespan, shutdown on exit."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.jobs.keepalive import keepalive
from app.jobs.sweeper import sweep_stale
from app.jobs.weekly_recap import send_weekly_recap

scheduler = AsyncIOScheduler()


def init_scheduler() -> None:
    """Register all jobs and start the scheduler."""
    scheduler.add_job(
        keepalive,
        trigger=IntervalTrigger(minutes=10),
        id="keepalive",
        replace_existing=True,
    )
    scheduler.add_job(
        sweep_stale,
        trigger=IntervalTrigger(minutes=2),
        id="sweeper",
        replace_existing=True,
    )
    scheduler.add_job(
        send_weekly_recap,
        trigger=CronTrigger(day_of_week="mon", hour=8, minute=0, timezone="Europe/Paris"),
        id="weekly_recap",
        replace_existing=True,
    )
    scheduler.start()


def shutdown_scheduler() -> None:
    """Graceful shutdown."""
    scheduler.shutdown(wait=False)
