"""
Project Chimera - Agent Task Handlers
Celery tasks for executing agent jobs in a decoupled manner
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any
from celery import current_task
from celery.exceptions import Retry

from workers.celery_app import celery_app
from agents.base_agent import AgentJob, AgentResult
from database.db_manager import DatabaseManager
from utils.logger import ChimeraLogger

logger = ChimeraLogger.get_logger("workers.agent_tasks")

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def execute_agent_job(self, agent_name: str, job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a job for a specific agent through the Celery queue system
    This replaces direct agent instantiation in the orchestrator
    """
    try:
        # Create job object
        job = AgentJob(
            job_id=job_data.get("job_id", str(current_task.request.id)),
            job_type=job_data.get("type", "unknown"),
            input_data=job_data,
            priority=job_data.get("priority", 5)
        )
        
        logger.info(f"🔄 Executing {job.job_type} job {job.job_id} for agent {agent_name}")
        
        # Execute the job asynchronously
        result = asyncio.run(_execute_agent_job_async(agent_name, job))
        
        logger.info(f"✅ Job {job.job_id} completed with status: {result['status']}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Job execution failed for {agent_name}: {e}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"🔄 Retrying job for {agent_name} (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60 * (self.request.retries + 1))
        
        # Max retries reached
        return {
            "job_id": job_data.get("job_id", str(current_task.request.id)),
            "agent_name": agent_name,
            "status": "error",
            "output_data": {"error": str(e)},
            "execution_time_ms": 0,
            "error_message": str(e)
        }

async def _execute_agent_job_async(agent_name: str, job: AgentJob) -> Dict[str, Any]:
    """Execute agent job asynchronously"""
    db_manager = None
    try:
        # Initialize database connection
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Import and instantiate the appropriate agent
        agent = await _get_agent_instance(agent_name, db_manager)
        if not agent:
            raise ValueError(f"Unknown agent: {agent_name}")
        
        # Execute the job
        result = await agent.execute(job)
        
        # Log the result
        await db_manager.log_agent_activity(
            agent_name=agent_name,
            activity_type="job_execution",
            description=f"Executed job {job.job_id}",
            status=result.status,
            input_data=job.input_data,
            output_data=result.output_data,
            execution_time_ms=result.execution_time_ms,
            error_message=result.error_message
        )
        
        # Process any next jobs that need to be queued
        if result.next_jobs:
            for next_job in result.next_jobs:
                # Submit next job to appropriate queue
                execute_agent_job.delay(
                    agent_name=_get_agent_name_for_job_type(next_job.job_type),
                    job_data={
                        "job_id": next_job.job_id,
                        "type": next_job.job_type,
                        "priority": next_job.priority,
                        **next_job.input_data
                    }
                )
        
        return {
            "job_id": result.job_id,
            "agent_name": result.agent_name,
            "status": result.status,
            "output_data": result.output_data,
            "execution_time_ms": result.execution_time_ms,
            "error_message": result.error_message
        }
        
    finally:
        if db_manager:
            await db_manager.close()

async def _get_agent_instance(agent_name: str, db_manager: DatabaseManager):
    """Get agent instance by name"""
    if agent_name == "SCOUT":
        from agents.prospector import ProspectorAgent
        return ProspectorAgent(db_manager)
    elif agent_name == "HERALD":
        from agents.communicator import CommunicatorAgent
        return CommunicatorAgent(db_manager)
    elif agent_name == "DIPLOMAT":
        from agents.closer import CloserAgent
        return CloserAgent(db_manager)
    elif agent_name == "WRENCH":
        from agents.technician import TechnicianAgent
        return TechnicianAgent(db_manager)
    elif agent_name == "QUARTERMASTER":
        from agents.dispatcher import DispatcherAgent
        return DispatcherAgent(db_manager)
    elif agent_name == "ARTIFICER":
        from agents.creator import CreatorAgent
        return CreatorAgent(db_manager)
    elif agent_name == "LOREWEAVER":
        from agents.bard import BardAgent
        return BardAgent(db_manager)
    elif agent_name == "AEGIS":
        from agents.guardian import GuardianAgent
        return GuardianAgent(db_manager)
    elif agent_name == "ARCHITECT":
        from agents.strategist import StrategistAgent
        return StrategistAgent(db_manager)
    else:
        return None

def _get_agent_name_for_job_type(job_type: str) -> str:
    """Map job types to agent names"""
    job_type_mapping = {
        "find_leads": "SCOUT",
        "draft_outreach": "HERALD",
        "process_reply": "DIPLOMAT",
        "auto_repair": "WRENCH",
        "fulfill_external": "QUARTERMASTER",
        "fulfill_internal": "ARTIFICER",
        "generate_content_calendar": "LOREWEAVER",
        "create_content": "LOREWEAVER",
        "validate_message": "AEGIS",
        "create_mission_brief": "ARCHITECT"
    }
    return job_type_mapping.get(job_type, "MAESTRO")
