from __future__ import annotations
"""Celery application configuration."""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "digital_secretary",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.reminder_worker",
        "app.workers.birthday_worker",
        "app.workers.task_worker",
        "app.workers.briefing_worker",
        "app.workers.brain_worker"
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Almaty",
    enable_utc=True,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        # Meeting reminders - every minute
        "check-meeting-reminders": {
            "task": "check_meeting_reminders",
            "schedule": 60.0,
        },
        # Birthday reminders - every hour
        "check-birthday-reminders": {
            "task": "check_birthday_reminders",
            "schedule": 3600.0,
        },
        # Task deadlines - every 30 minutes
        "check-task-deadlines": {
            "task": "check_task_deadlines",
            "schedule": 1800.0,
        },
        # Morning briefing - daily at 09:00
        "send-morning-briefing": {
            "task": "send_morning_briefing",
            "schedule": crontab(hour=9, minute=0),
        },
        # Evening Report - daily at 23:00
        "send-daily-report": {
            "task": "send_daily_report",
            "schedule": crontab(hour=23, minute=0),
        },
        # Debt collection check - every 4 hours
        "check-overdue-invoices": {
            "task": "check_overdue_invoices",
            "schedule": crontab(hour="*/4", minute=30),
        },
        # Weekly summary - Monday 09:00
        "generate-weekly-summary": {
            "task": "generate_weekly_summary",
            "schedule": crontab(hour=9, minute=0, day_of_week=1),
        },
        # ⭐ BRAIN TICK - every 5 minutes (proactive autonomous actions)
        "brain-tick": {
            "task": "brain_tick",
            "schedule": 300.0,  # Every 5 minutes
        },
    },
)



