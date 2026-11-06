from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from bot.config import TZ

def build_scheduler(app):
    """
    Wires all scheduled jobs to bot handlers.
    app: telegram.ext.Application instance
    """
    from bot.handlers.voting import send_weekly_poll, close_weekly_poll
    from bot.handlers.attendance import send_day_of_reminder
    from bot.handlers.ratings import request_post_session_ratings

    tz = pytz.timezone(TZ)
    scheduler = AsyncIOScheduler(timezone=tz)

    # Monday 10:00 — open poll
    scheduler.add_job(
        send_weekly_poll,
        CronTrigger(day_of_week="mon", hour=10, minute=0, timezone=tz),
        args=[app],
        id="open_poll",
    )

    # Friday 10:00 — close poll
    scheduler.add_job(
        close_weekly_poll,
        CronTrigger(day_of_week="fri", hour=10, minute=0, timezone=tz),
        args=[app],
        id="close_poll",
    )

    # Every possible meeting day (Tue–Sun) 9:00 — day-of reminder.
    # The handler itself no-ops unless today is the chosen day
    # of the latest closed poll, so extra firings are harmless.
    scheduler.add_job(
        send_day_of_reminder,
        CronTrigger(day_of_week="tue-sun", hour=9, minute=0, timezone=tz),
        args=[app],
        id="day_of_reminder",
    )

    # Every possible meeting day (Tue–Sun) 23:00 — request post-session ratings.
    # Previously this ran only on Sat/Sun, which silently skipped
    # any session held on a weekday (Tue–Fri).
    scheduler.add_job(
        request_post_session_ratings,
        CronTrigger(day_of_week="tue-sun", hour=23, minute=0, timezone=tz),
        args=[app],
        id="request_ratings",
    )

    return scheduler
