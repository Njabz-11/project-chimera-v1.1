"""
Project Chimera - Base Agent Class
Foundation class for all autonomous agents in the ABOP system
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from database.db_manager import DatabaseManager
from utils.logger import ChimeraLogger

@dataclass
class AgentJob:
    """Represents a job/task for an agent to execute"""
    job_id: str
    job_type: str
    input_data: Dict[str, Any]
    priority: int = 1
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class AgentResult:
    """Represents the result of an agent's job execution"""
    job_id: str
    agent_name: str
    status: str  # success, error, partial
    output_data: Dict[str, Any]
    execution_time_ms: int
    error_message: Optional[str] = None
    next_jobs: List[AgentJob] = None
    
    def __post_init__(self):
        if self.next_jobs is None:
            self.next_jobs = []

class BaseAgent(ABC):
    """Base class for all Project Chimera agents"""
    
    def __init__(self, agent_name: str, db_manager: DatabaseManager):
        self.agent_name = agent_name
        self.db_manager = db_manager
        self.logger = ChimeraLogger.get_logger(f"Agent.{agent_name}")
        self.is_running = False
        self.job_queue = asyncio.Queue()
        self.status = "initialized"
        self.last_activity = datetime.now()
        
    async def initialize(self):
        """Initialize the agent - called once at startup"""
        self.logger.info(f"🤖 Initializing {self.agent_name} agent...")
        self.status = "ready"
        self.last_activity = datetime.now()
        
        # Log initialization
        await self.db_manager.log_agent_activity(
            agent_name=self.agent_name,
            activity_type="initialization",
            description=f"{self.agent_name} agent initialized",
            status="success"
        )
        
        self.logger.info(f"✅ {self.agent_name} agent ready for operations")
    
    async def start(self):
        """Start the agent's main processing loop"""
        if self.is_running:
            self.logger.warning(f"{self.agent_name} agent is already running")
            return
        
        self.is_running = True
        self.status = "active"
        self.logger.info(f"🚀 Starting {self.agent_name} agent processing loop")
        
        try:
            while self.is_running:
                try:
                    # Wait for a job with timeout
                    job = await asyncio.wait_for(self.job_queue.get(), timeout=5.0)
                    await self._process_job(job)
                except asyncio.TimeoutError:
                    # No job received, continue loop (allows for graceful shutdown)
                    continue
                except Exception as e:
                    self.logger.error(f"Error in {self.agent_name} processing loop: {e}")
                    await asyncio.sleep(1)  # Brief pause before retrying
        
        except Exception as e:
            self.logger.error(f"Fatal error in {self.agent_name} agent: {e}")
            self.status = "error"
        finally:
            self.status = "stopped"
            self.logger.info(f"🛑 {self.agent_name} agent stopped")
    
    async def stop(self):
        """Stop the agent gracefully"""
        self.logger.info(f"🛑 Stopping {self.agent_name} agent...")
        self.is_running = False
        self.status = "stopping"
    
    async def add_job(self, job: AgentJob):
        """Add a job to the agent's queue"""
        await self.job_queue.put(job)
        self.logger.debug(f"📥 Job {job.job_id} added to {self.agent_name} queue")
    
    async def _process_job(self, job: AgentJob):
        """Process a single job"""
        start_time = time.time()
        self.last_activity = datetime.now()
        
        self.logger.info(f"🔄 Processing job {job.job_id} of type {job.job_type}")
        
        try:
            # Execute the job
            result = await self.execute(job)
            
            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            result.execution_time_ms = execution_time_ms
            
            # Log successful execution
            await self.db_manager.log_agent_activity(
                agent_name=self.agent_name,
                activity_type=job.job_type,
                description=f"Executed {job.job_type} job",
                status=result.status,
                input_data=job.input_data,
                output_data=result.output_data,
                execution_time_ms=execution_time_ms,
                error_message=result.error_message
            )
            
            self.logger.info(f"✅ Job {job.job_id} completed with status: {result.status}")
        
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)

            self.logger.error(f"❌ Job {job.job_id} failed: {error_msg}")

            # Create diagnostic report for error analysis
            try:
                from utils.error_handler import error_handler
                from utils.error_router import error_router

                # Create diagnostic report
                report = error_handler.create_diagnostic_report(
                    exception=e,
                    agent_name=self.agent_name,
                    job_id=job.job_id,
                    context_data=job.input_data,
                    original_goal=job.input_data.get("original_goal", f"Execute {job.job_type} job")
                )

                # Route error for appropriate handling
                routing_result = await error_router.route_error(report)

                self.logger.info(f"🔍 Error routed with strategy: {routing_result.get('route_strategy', 'unknown')}")

            except Exception as routing_error:
                self.logger.error(f"Failed to route error: {routing_error}")

            # Log failed execution
            await self.db_manager.log_agent_activity(
                agent_name=self.agent_name,
                activity_type=job.job_type,
                description=f"Failed to execute {job.job_type} job",
                status="error",
                input_data=job.input_data,
                execution_time_ms=execution_time_ms,
                error_message=error_msg
            )
    
    @abstractmethod
    async def execute(self, job: AgentJob) -> AgentResult:
        """Execute a specific job - must be implemented by each agent"""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            "agent_name": self.agent_name,
            "status": self.status,
            "is_running": self.is_running,
            "queue_size": self.job_queue.qsize(),
            "last_activity": self.last_activity.isoformat()
        }
