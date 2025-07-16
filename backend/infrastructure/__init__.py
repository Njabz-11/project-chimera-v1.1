"""
Infrastructure package for Project Chimera
Contains vector databases, job queues, browser automation, and database management
"""

from .vector_db import MemoryBank, VectorDBFactory, ChromaDBManager, LanceDBManager
from .browser_automation import WebScraper, BrowserManager, scrape_website, search_for_leads, extract_lead_contact_info
from .database import DatabaseManager, DatabaseConfig, MigrationManager, initialize_database, get_database_manager
from .job_queue import JobQueueManager, JobQueueConfig, AgentJobDispatcher, initialize_job_queue, get_job_queue_manager, get_agent_dispatcher

__all__ = [
    # Vector Database
    'MemoryBank',
    'VectorDBFactory',
    'ChromaDBManager',
    'LanceDBManager',

    # Browser Automation
    'WebScraper',
    'BrowserManager',
    'scrape_website',
    'search_for_leads',
    'extract_lead_contact_info',

    # Database Management
    'DatabaseManager',
    'DatabaseConfig',
    'MigrationManager',
    'initialize_database',
    'get_database_manager',

    # Job Queue System
    'JobQueueManager',
    'JobQueueConfig',
    'AgentJobDispatcher',
    'initialize_job_queue',
    'get_job_queue_manager',
    'get_agent_dispatcher'
]
