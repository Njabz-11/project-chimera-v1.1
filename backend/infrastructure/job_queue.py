"""
Job Queue Infrastructure for Project Chimera
Provides Celery-based job queue system for agent communication
"""

import os
import logging
from typing import Dict, Any, Optional, List, Callable
import json
from datetime import datetime, timedelta

# Celery imports
try:
    from celery import Celery, Task
    from celery.result import AsyncResult
    from kombu import Queue
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    logging.warning("Celery not available")

# Redis imports
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available")


class JobQueueConfig:
    """Job queue configuration management"""
    
    def __init__(self):
        # Broker configuration (Redis or RabbitMQ)
        self.broker_type = os.getenv("BROKER_TYPE", "redis")
        
        # Redis configuration
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_db = int(os.getenv("REDIS_DB", "0"))
        self.redis_password = os.getenv("REDIS_PASSWORD", None)
        
        # RabbitMQ configuration
        self.rabbitmq_host = os.getenv("RABBITMQ_HOST", "localhost")
        self.rabbitmq_port = int(os.getenv("RABBITMQ_PORT", "5672"))
        self.rabbitmq_user = os.getenv("RABBITMQ_USER", "guest")
        self.rabbitmq_password = os.getenv("RABBITMQ_PASSWORD", "guest")
        self.rabbitmq_vhost = os.getenv("RABBITMQ_VHOST", "/")
        
        # Celery configuration
        self.celery_app_name = "chimera_agents"
        self.result_backend = self.get_result_backend()
        self.broker_url = self.get_broker_url()
    
    def get_broker_url(self) -> str:
        """Get broker URL based on configuration"""
        if self.broker_type.lower() == "redis":
            if self.redis_password:
                return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
            else:
                return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
        elif self.broker_type.lower() == "rabbitmq":
            return f"pyamqp://{self.rabbitmq_user}:{self.rabbitmq_password}@{self.rabbitmq_host}:{self.rabbitmq_port}/{self.rabbitmq_vhost}"
        else:
            raise ValueError(f"Unsupported broker type: {self.broker_type}")
    
    def get_result_backend(self) -> str:
        """Get result backend URL"""
        # Use Redis for result backend regardless of broker type
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        else:
            return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


class ChimeraTask(Task):
    """Custom Celery task class for Project Chimera"""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds"""
        logging.info(f"Task {task_id} succeeded with result: {retval}")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails"""
        logging.error(f"Task {task_id} failed: {exc}")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried"""
        logging.warning(f"Task {task_id} retrying due to: {exc}")


class JobQueueManager:
    """Manages the Celery job queue system"""
    
    def __init__(self, config: Optional[JobQueueConfig] = None):
        self.config = config or JobQueueConfig()
        self.celery_app = None
        self.redis_client = None
        self.initialized = False
    
    def initialize(self) -> bool:
        """Initialize the job queue system"""
        if not CELERY_AVAILABLE:
            logging.error("Celery is not available")
            return False
        
        try:
            # Create Celery app
            self.celery_app = Celery(
                self.config.celery_app_name,
                broker=self.config.broker_url,
                backend=self.config.result_backend
            )
            
            # Configure Celery
            self.celery_app.conf.update(
                task_serializer='json',
                accept_content=['json'],
                result_serializer='json',
                timezone='UTC',
                enable_utc=True,
                task_track_started=True,
                task_time_limit=30 * 60,  # 30 minutes
                task_soft_time_limit=25 * 60,  # 25 minutes
                worker_prefetch_multiplier=1,
                task_acks_late=True,
                worker_disable_rate_limits=False,
                task_compression='gzip',
                result_compression='gzip',
                task_routes={
                    'chimera.agents.*': {'queue': 'agents'},
                    'chimera.orchestrator.*': {'queue': 'orchestrator'},
                    'chimera.system.*': {'queue': 'system'}
                },
                task_default_queue='default',
                task_queues=(
                    Queue('default'),
                    Queue('agents'),
                    Queue('orchestrator'),
                    Queue('system'),
                    Queue('high_priority'),
                    Queue('low_priority')
                )
            )
            
            # Set custom task class
            self.celery_app.Task = ChimeraTask
            
            # Initialize Redis client if using Redis
            if self.config.broker_type.lower() == "redis" and REDIS_AVAILABLE:
                self.redis_client = redis.Redis(
                    host=self.config.redis_host,
                    port=self.config.redis_port,
                    db=self.config.redis_db,
                    password=self.config.redis_password,
                    decode_responses=True
                )
            
            self.initialized = True
            logging.info("Job queue system initialized successfully")
            return True
            
        except Exception as e:
            logging.error(f"Failed to initialize job queue system: {e}")
            return False
    
    def get_celery_app(self) -> Optional[Celery]:
        """Get the Celery app instance"""
        if not self.initialized:
            self.initialize()
        return self.celery_app
    
    def submit_job(self, task_name: str, args: tuple = (), kwargs: dict = None, 
                   queue: str = 'default', priority: int = 5, 
                   countdown: int = 0, eta: datetime = None) -> Optional[str]:
        """Submit a job to the queue"""
        if not self.initialized:
            return None
        
        try:
            kwargs = kwargs or {}
            
            # Submit task
            result = self.celery_app.send_task(
                task_name,
                args=args,
                kwargs=kwargs,
                queue=queue,
                priority=priority,
                countdown=countdown,
                eta=eta
            )
            
            logging.info(f"Submitted job {result.id} to queue {queue}")
            return result.id
            
        except Exception as e:
            logging.error(f"Failed to submit job: {e}")
            return None
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status and result"""
        if not self.initialized:
            return {"status": "error", "message": "Queue not initialized"}
        
        try:
            result = AsyncResult(job_id, app=self.celery_app)
            
            return {
                "id": job_id,
                "status": result.status,
                "result": result.result,
                "traceback": result.traceback,
                "successful": result.successful(),
                "failed": result.failed(),
                "ready": result.ready()
            }
            
        except Exception as e:
            logging.error(f"Failed to get job status: {e}")
            return {"status": "error", "message": str(e)}
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        if not self.initialized:
            return False
        
        try:
            result = AsyncResult(job_id, app=self.celery_app)
            result.revoke(terminate=True)
            logging.info(f"Cancelled job {job_id}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to cancel job: {e}")
            return False
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        if not self.initialized or not self.redis_client:
            return {}
        
        try:
            stats = {}
            
            # Get queue lengths
            queues = ['default', 'agents', 'orchestrator', 'system', 'high_priority', 'low_priority']
            for queue in queues:
                length = self.redis_client.llen(queue)
                stats[f"{queue}_queue_length"] = length
            
            # Get active workers (if available)
            inspect = self.celery_app.control.inspect()
            active_workers = inspect.active()
            stats["active_workers"] = len(active_workers) if active_workers else 0
            
            return stats
            
        except Exception as e:
            logging.error(f"Failed to get queue stats: {e}")
            return {}
    
    def purge_queue(self, queue_name: str) -> bool:
        """Purge all messages from a queue"""
        if not self.initialized:
            return False
        
        try:
            self.celery_app.control.purge()
            logging.info(f"Purged queue {queue_name}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to purge queue: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test connection to broker and result backend"""
        if not self.initialized:
            return False
        
        try:
            # Test broker connection
            with self.celery_app.connection() as conn:
                conn.ensure_connection(max_retries=3)
            
            # Test Redis connection if available
            if self.redis_client:
                self.redis_client.ping()
            
            logging.info("Job queue connection test successful")
            return True
            
        except Exception as e:
            logging.error(f"Job queue connection test failed: {e}")
            return False


class AgentJobDispatcher:
    """High-level interface for dispatching jobs to Project Chimera agents"""
    
    def __init__(self, job_queue_manager: Optional[JobQueueManager] = None):
        self.job_queue = job_queue_manager or JobQueueManager()
        if not self.job_queue.initialized:
            self.job_queue.initialize()
    
    def dispatch_to_orchestrator(self, action: str, data: Dict[str, Any], 
                                priority: int = 5) -> Optional[str]:
        """Dispatch a job to the Orchestrator agent"""
        return self.job_queue.submit_job(
            'chimera.orchestrator.execute',
            kwargs={'action': action, 'data': data},
            queue='orchestrator',
            priority=priority
        )
    
    def dispatch_to_prospector(self, mission_brief: Dict[str, Any], 
                              priority: int = 5) -> Optional[str]:
        """Dispatch a lead finding job to the Prospector agent"""
        return self.job_queue.submit_job(
            'chimera.agents.prospector.find_leads',
            kwargs={'mission_brief': mission_brief},
            queue='agents',
            priority=priority
        )
    
    def dispatch_to_communicator(self, lead_data: Dict[str, Any], 
                                priority: int = 7) -> Optional[str]:
        """Dispatch an outreach job to the Communicator agent"""
        return self.job_queue.submit_job(
            'chimera.agents.communicator.draft_outreach',
            kwargs={'lead_data': lead_data},
            queue='agents',
            priority=priority
        )
    
    def dispatch_to_closer(self, conversation_data: Dict[str, Any], 
                          priority: int = 8) -> Optional[str]:
        """Dispatch a reply handling job to the Closer agent"""
        return self.job_queue.submit_job(
            'chimera.agents.closer.process_reply',
            kwargs={'conversation_data': conversation_data},
            queue='agents',
            priority=priority
        )
    
    def dispatch_to_bard(self, content_request: Dict[str, Any], 
                        priority: int = 4) -> Optional[str]:
        """Dispatch a content generation job to the Bard agent"""
        return self.job_queue.submit_job(
            'chimera.agents.bard.generate_content',
            kwargs={'content_request': content_request},
            queue='agents',
            priority=priority
        )
    
    def dispatch_to_dispatcher(self, project_data: Dict[str, Any], 
                              priority: int = 6) -> Optional[str]:
        """Dispatch a fulfillment job to the Dispatcher agent"""
        return self.job_queue.submit_job(
            'chimera.agents.dispatcher.fulfill_external',
            kwargs={'project_data': project_data},
            queue='agents',
            priority=priority
        )
    
    def dispatch_to_creator(self, project_data: Dict[str, Any], 
                           priority: int = 6) -> Optional[str]:
        """Dispatch an internal fulfillment job to the Creator agent"""
        return self.job_queue.submit_job(
            'chimera.agents.creator.fulfill_internal',
            kwargs={'project_data': project_data},
            queue='agents',
            priority=priority
        )
    
    def dispatch_to_technician(self, error_data: Dict[str, Any], 
                              priority: int = 9) -> Optional[str]:
        """Dispatch an error fixing job to the Technician agent"""
        return self.job_queue.submit_job(
            'chimera.agents.technician.fix_error',
            kwargs={'error_data': error_data},
            queue='system',
            priority=priority
        )
    
    def dispatch_to_guardian(self, message_data: Dict[str, Any], 
                            priority: int = 10) -> Optional[str]:
        """Dispatch a safety check job to the Guardian agent"""
        return self.job_queue.submit_job(
            'chimera.agents.guardian.safety_check',
            kwargs={'message_data': message_data},
            queue='system',
            priority=priority
        )


# Convenience functions for Project Chimera
def get_job_queue_manager() -> JobQueueManager:
    """Get configured job queue manager"""
    return JobQueueManager()


def get_agent_dispatcher() -> AgentJobDispatcher:
    """Get configured agent job dispatcher"""
    return AgentJobDispatcher()


def initialize_job_queue() -> bool:
    """Initialize job queue system"""
    manager = get_job_queue_manager()
    return manager.initialize()
