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

    # Friday 23:59 — close poll
    scheduler.add_job(
        close_weekly_poll,
        CronTrigger(day_of_week="fri", hour=23, minute=59, timezone=tz),
        args=[app],
        id="close_poll",
    )

    # Saturday & Sunday 10:00 — day-of reminder
    scheduler.add_job(
        send_day_of_reminder,
        CronTrigger(day_of_week="sat,sun", hour=10, minute=0, timezone=tz),
        args=[app],
        id="day_of_reminder",
    )

    # Saturday & Sunday 23:00 — request ratings
    scheduler.add_job(
        request_post_session_ratings,
        CronTrigger(day_of_week="sat,sun", hour=23, minute=0, timezone=tz),
        args=[app],
        id="request_ratings",
    )

    return scheduler
