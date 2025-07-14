"""
Celery application for Project Chimera Enterprise
Handles background tasks and scheduled jobs
"""
from celery import Celery
from celery.schedules import crontab
from config.settings import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "chimera_enterprise",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "workers.tasks.agent_tasks",
        "workers.tasks.email_tasks", 
        "workers.tasks.monitoring_tasks",
        "workers.tasks.tenant_tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    result_expires=3600,  # 1 hour
    task_routes={
        "workers.tasks.agent_tasks.*": {"queue": "agents"},
        "workers.tasks.email_tasks.*": {"queue": "emails"},
        "workers.tasks.monitoring_tasks.*": {"queue": "monitoring"},
        "workers.tasks.tenant_tasks.*": {"queue": "tenants"},
    },
    beat_schedule={
        # Email polling every 5 minutes
        "poll-emails": {
            "task": "workers.tasks.email_tasks.poll_emails",
            "schedule": crontab(minute="*/5"),
        },
        # System health check every minute
        "health-check": {
            "task": "workers.tasks.monitoring_tasks.system_health_check",
            "schedule": crontab(minute="*"),
        },
        # Tenant cleanup daily at 2 AM
        "tenant-cleanup": {
            "task": "workers.tasks.tenant_tasks.cleanup_expired_tenants",
            "schedule": crontab(hour=2, minute=0),
        },
        # Usage statistics update every hour
        "update-usage-stats": {
            "task": "workers.tasks.tenant_tasks.update_usage_statistics",
            "schedule": crontab(minute=0),
        },
        # Agent health check every 10 minutes
        "agent-health-check": {
            "task": "workers.tasks.agent_tasks.check_agent_health",
            "schedule": crontab(minute="*/10"),
        },
    },
)

if __name__ == "__main__":
    celery_app.start()
