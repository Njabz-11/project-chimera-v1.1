"""
Project Chimera - Celery Application Configuration
Central job queue system for decoupled agent communication
"""

import os
from celery import Celery
from kombu import Queue
from config.settings import Settings

# Load settings
settings = Settings()

# Create Celery application
celery_app = Celery(
    'chimera',
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        'workers.agent_tasks',
        'workers.system_tasks'
    ]
)

# Celery Configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        'workers.agent_tasks.execute_agent_job': {'queue': 'agent_jobs'},
        'workers.system_tasks.system_maintenance': {'queue': 'system_tasks'},
        'workers.system_tasks.email_polling': {'queue': 'system_tasks'},
    },
    
    # Queue definitions
    task_queues=(
        Queue('agent_jobs', routing_key='agent_jobs'),
        Queue('system_tasks', routing_key='system_tasks'),
        Queue('high_priority', routing_key='high_priority'),
    ),
    
    # Task execution settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    
    # Task retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Beat scheduler settings (for periodic tasks)
    beat_schedule={
        'email-polling': {
            'task': 'workers.system_tasks.email_polling',
            'schedule': 300.0,  # Every 5 minutes
        },
        'trigger-outreach': {
            'task': 'workers.system_tasks.trigger_outreach_for_new_leads',
            'schedule': 600.0,  # Every 10 minutes
        },
        'trigger-fulfillment': {
            'task': 'workers.system_tasks.trigger_fulfillment_for_closed_deals',
            'schedule': 900.0,  # Every 15 minutes
        },
    },
)

# Task discovery
celery_app.autodiscover_tasks()

if __name__ == '__main__':
    celery_app.start()
