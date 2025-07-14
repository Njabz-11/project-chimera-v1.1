"""
Project Chimera - Orchestrator Agent (MAESTRO)
The central nervous system and state machine for the entire platform
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum

from .base_agent import BaseAgent, AgentJob, AgentResult
from database.db_manager import DatabaseManager
from tools.email_service import EmailService

class MissionState(Enum):
    """Possible states for a mission"""
    CREATED = "created"
    ANALYZING = "analyzing"
    PROSPECTING = "prospecting"
    CONTENT_CREATING = "content_creating"
    OUTREACH_ACTIVE = "outreach_active"
    LEADS_NURTURING = "leads_nurturing"
    DEALS_CLOSING = "deals_closing"
    FULFILLMENT = "fulfillment"
    COMPLETED = "completed"
    PAUSED = "paused"
    ERROR = "error"

class OrchestratorAgent(BaseAgent):
    """MAESTRO - The central orchestrator managing all system operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__("MAESTRO", db_manager)
        self.mission_states: Dict[int, MissionState] = {}
        self.active_agents: Dict[str, BaseAgent] = {}
        self.email_service = EmailService()
        self.email_polling_active = False
        self.last_email_check = None
        
    async def initialize(self):
        """Initialize the orchestrator"""
        await super().initialize()
        self.logger.info("🎭 MAESTRO orchestrator initialized and ready")
    
    async def start_mission(self, mission_id: int, briefing_data: Dict[str, Any]):
        """Start a new mission and initiate the workflow"""
        self.logger.info(f"🎯 Starting mission {mission_id}: {briefing_data.get('business_goal', 'Unknown goal')}")
        
        # Set initial mission state
        self.mission_states[mission_id] = MissionState.CREATED
        
        # Log mission start
        await self.db_manager.log_agent_activity(
            agent_name=self.agent_name,
            activity_type="mission_start",
            description=f"Mission {mission_id} started",
            status="success",
            input_data={"mission_id": mission_id, "briefing_data": briefing_data}
        )
        
        # Update mission state
        await self._update_mission_state(mission_id, MissionState.ANALYZING)
    
    async def _update_mission_state(self, mission_id: int, new_state: MissionState):
        """Update mission state and log the transition"""
        old_state = self.mission_states.get(mission_id, MissionState.CREATED)
        self.mission_states[mission_id] = new_state
        
        self.logger.info(f"🔄 Mission {mission_id} state: {old_state.value} → {new_state.value}")
        
        # Log state transition
        await self.db_manager.log_agent_activity(
            agent_name=self.agent_name,
            activity_type="state_transition",
            description=f"Mission {mission_id} state changed from {old_state.value} to {new_state.value}",
            status="success",
            input_data={"mission_id": mission_id, "old_state": old_state.value, "new_state": new_state.value}
        )
    
    async def execute(self, job: AgentJob) -> AgentResult:
        """Execute orchestrator-specific jobs"""
        job_type = job.job_type
        
        if job_type == "mission_completed":
            return await self._handle_mission_completion(job)
        elif job_type == "agent_error":
            return await self._handle_agent_error(job)
        else:
            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="error",
                output_data={},
                execution_time_ms=0,
                error_message=f"Unknown job type: {job_type}"
            )
    
    async def _handle_mission_completion(self, job: AgentJob) -> AgentResult:
        """Handle mission completion workflow"""
        mission_id = job.input_data.get("mission_id")
        
        if mission_id:
            await self._update_mission_state(mission_id, MissionState.COMPLETED)
            
            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="success",
                output_data={"mission_id": mission_id, "status": "completed"},
                execution_time_ms=0
            )
        else:
            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="error",
                output_data={},
                execution_time_ms=0,
                error_message="Missing mission_id in job data"
            )
    
    async def _handle_agent_error(self, job: AgentJob) -> AgentResult:
        """Handle agent error notifications"""
        agent_name = job.input_data.get("agent_name")
        error_message = job.input_data.get("error_message")
        
        self.logger.error(f"🚨 Agent error reported by {agent_name}: {error_message}")
        
        return AgentResult(
            job_id=job.job_id,
            agent_name=self.agent_name,
            status="success",
            output_data={"error_handled": True},
            execution_time_ms=0
        )
    
    def get_active_agent_count(self) -> int:
        """Get count of active agents"""
        return len([agent for agent in self.active_agents.values() if agent.status == "active"])

    async def submit_job(self, agent_name: str, job_data: Dict[str, Any]) -> str:
        """Submit a job to a specific agent"""
        import uuid

        job_id = str(uuid.uuid4())

        # Create agent job
        job = AgentJob(
            job_id=job_id,
            job_type=job_data.get("type", "unknown"),
            input_data=job_data,
            priority=job_data.get("priority", 5)
        )

        # Log job submission
        await self.db_manager.log_agent_activity(
            agent_name=self.agent_name,
            activity_type="job_submission",
            description=f"Submitted job {job_id} to {agent_name}",
            status="success",
            input_data=job_data
        )

        # For now, execute the job immediately (in Phase 1 we don't have a queue system)
        # In later phases, this would be submitted to a job queue
        asyncio.create_task(self._execute_agent_job(agent_name, job))

        return job_id

    async def _execute_agent_job(self, agent_name: str, job: AgentJob):
        """Execute a job for a specific agent"""
        try:
            # Import and instantiate the appropriate agent
            if agent_name == "SCOUT":
                from .prospector import ProspectorAgent
                agent = ProspectorAgent(self.db_manager)
            elif agent_name == "HERALD":
                from .communicator import CommunicatorAgent
                agent = CommunicatorAgent(self.db_manager)
            elif agent_name == "DIPLOMAT":
                from .closer import CloserAgent
                agent = CloserAgent(self.db_manager)
            elif agent_name == "WRENCH":
                from .technician import TechnicianAgent
                agent = TechnicianAgent(self.db_manager)
            elif agent_name == "QUARTERMASTER":
                from .dispatcher import DispatcherAgent
                agent = DispatcherAgent(self.db_manager)
            elif agent_name == "ARTIFICER":
                from .creator import CreatorAgent
                agent = CreatorAgent(self.db_manager)
            elif agent_name == "LOREWEAVER":
                from .bard import BardAgent
                agent = BardAgent(self.db_manager)
            else:
                self.logger.error(f"Unknown agent: {agent_name}")
                return

            # Execute the job
            result = await agent.execute(job)

            # Log the result
            await self.db_manager.log_agent_activity(
                agent_name=agent_name,
                activity_type="job_execution",
                description=f"Executed job {job.job_id}",
                status=result.status,
                input_data=job.input_data,
                output_data=result.output_data,
                execution_time_ms=result.execution_time_ms,
                error_message=result.output_data.get("error") if result.status == "error" else None
            )

        except Exception as e:
            self.logger.error(f"Failed to execute job {job.job_id} for {agent_name}: {e}")

            # Log the error
            await self.db_manager.log_agent_activity(
                agent_name=agent_name,
                activity_type="job_execution",
                description=f"Failed to execute job {job.job_id}",
                status="error",
                input_data=job.input_data,
                error_message=str(e)
            )

    # Email Polling and Workflow Management
    async def start_email_polling(self, interval_minutes: int = 5):
        """Start periodic email polling for new messages"""
        if self.email_polling_active:
            self.logger.warning("Email polling is already active")
            return

        # Initialize email service
        email_initialized = await self.email_service.initialize()
        if not email_initialized:
            self.logger.error("❌ Cannot start email polling - email service not initialized")
            return

        self.email_polling_active = True
        self.logger.info(f"📧 Starting email polling every {interval_minutes} minutes")

        # Start polling loop
        asyncio.create_task(self._email_polling_loop(interval_minutes))

    async def stop_email_polling(self):
        """Stop email polling"""
        self.email_polling_active = False
        self.logger.info("📧 Email polling stopped")

    async def _email_polling_loop(self, interval_minutes: int):
        """Main email polling loop"""
        while self.email_polling_active:
            try:
                await self._check_for_new_emails()
                await asyncio.sleep(interval_minutes * 60)  # Convert to seconds
            except Exception as e:
                self.logger.error(f"Error in email polling loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _check_for_new_emails(self):
        """Check for new emails and process them"""
        try:
            # Get new messages
            new_messages = await self.email_service.list_new_messages(
                query="is:unread", max_results=20
            )

            if not new_messages:
                self.logger.debug("📧 No new emails found")
                return

            self.logger.info(f"📧 Found {len(new_messages)} new emails to process")

            for message in new_messages:
                await self._process_incoming_email(message)

            self.last_email_check = datetime.now()

        except Exception as e:
            self.logger.error(f"Failed to check for new emails: {e}")

    async def _process_incoming_email(self, email_data: Dict[str, Any]):
        """Process a single incoming email"""
        try:
            sender_email = self._extract_email_from_sender(email_data.get('sender', ''))

            # Check if this email is from a known lead
            lead = await self.db_manager.find_lead_by_email(sender_email)

            if lead:
                # Submit job to Closer Agent for processing
                job_data = {
                    "type": "process_reply",
                    "email_data": email_data,
                    "priority": 3
                }

                job_id = await self.submit_job("DIPLOMAT", job_data)
                self.logger.info(f"📧 Submitted email processing job {job_id} for lead {lead['id']}")
            else:
                self.logger.info(f"📧 Received email from unknown sender: {sender_email}")
                # Could potentially create a new lead here in the future

        except Exception as e:
            self.logger.error(f"Failed to process incoming email: {e}")

    def _extract_email_from_sender(self, sender_string: str) -> str:
        """Extract email address from sender string"""
        import re
        email_pattern = r'<([^>]+)>|([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        match = re.search(email_pattern, sender_string)

        if match:
            return match.group(1) or match.group(2)

        return sender_string.strip()

    # Workflow Management Methods
    async def trigger_outreach_for_new_leads(self):
        """Check for new leads and trigger outreach"""
        try:
            # Get all leads with status 'new'
            cursor = await self.db_manager.connection.execute("""
                SELECT * FROM leads WHERE status = 'new'
            """)

            new_leads = await cursor.fetchall()

            for lead_row in new_leads:
                lead = dict(lead_row)

                # Submit job to Communicator Agent
                job_data = {
                    "type": "draft_outreach",
                    "lead_id": lead['id'],
                    "priority": 4
                }

                job_id = await self.submit_job("HERALD", job_data)
                self.logger.info(f"📤 Triggered outreach for lead {lead['id']} (job {job_id})")

        except Exception as e:
            self.logger.error(f"Failed to trigger outreach for new leads: {e}")

    async def trigger_fulfillment_for_closed_deals(self):
        """Check for closed deals and trigger fulfillment"""
        try:
            # Get all leads with status 'deal_closed'
            cursor = await self.db_manager.connection.execute("""
                SELECT * FROM leads WHERE status = 'deal_closed'
            """)

            closed_deals = await cursor.fetchall()

            for lead_row in closed_deals:
                lead = dict(lead_row)

                # Check if fulfillment project already exists
                existing_projects = await self.db_manager.get_fulfillment_projects(lead_id=lead['id'])
                if existing_projects:
                    continue  # Skip if already has fulfillment project

                # Determine fulfillment type based on service offerings or lead notes
                mission = await self.db_manager.get_mission_by_id(lead['mission_id'])
                if not mission:
                    continue

                # Default to internal fulfillment, but could be configured per mission
                fulfillment_type = "internal"  # or "external" based on business logic

                if fulfillment_type == "internal":
                    # Submit job to Creator Agent
                    job_data = {
                        "type": "fulfill_internal",
                        "lead_id": lead['id'],
                        "project_requirements": {
                            "deliverable_type": "pdf_report",  # Default, could be customized
                            "urgency": "standard"
                        },
                        "priority": 3
                    }
                    job_id = await self.submit_job("ARTIFICER", job_data)
                    self.logger.info(f"🎯 Triggered internal fulfillment for lead {lead['id']} (job {job_id})")
                else:
                    # Submit job to Dispatcher Agent
                    job_data = {
                        "type": "fulfill_external",
                        "lead_id": lead['id'],
                        "project_requirements": {
                            "project_type": "consulting",
                            "timeline": "2 weeks"
                        },
                        "priority": 3
                    }
                    job_id = await self.submit_job("QUARTERMASTER", job_data)
                    self.logger.info(f"📋 Triggered external fulfillment for lead {lead['id']} (job {job_id})")

                # Update lead status to indicate fulfillment is in progress
                await self.db_manager.update_lead_status(lead['id'], "fulfillment_in_progress")

        except Exception as e:
            self.logger.error(f"Failed to trigger fulfillment for closed deals: {e}")

    async def trigger_content_generation(self, mission_id: int):
        """Trigger content calendar generation for a mission"""
        try:
            # Submit job to Bard Agent for content calendar
            job_data = {
                "type": "generate_content_calendar",
                "mission_id": mission_id,
                "priority": 2
            }

            job_id = await self.submit_job("LOREWEAVER", job_data)
            self.logger.info(f"📅 Triggered content calendar generation for mission {mission_id} (job {job_id})")

            return job_id

        except Exception as e:
            self.logger.error(f"Failed to trigger content generation: {e}")
            return None

    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            # Get lead counts by status
            cursor = await self.db_manager.connection.execute("""
                SELECT status, COUNT(*) as count
                FROM leads
                GROUP BY status
            """)

            lead_stats = {row[0]: row[1] for row in await cursor.fetchall()}

            # Get recent activity
            cursor = await self.db_manager.connection.execute("""
                SELECT COUNT(*) as count
                FROM agent_activities
                WHERE created_at > datetime('now', '-24 hours')
            """)

            recent_activity = (await cursor.fetchone())[0]

            # Get conversation stats
            cursor = await self.db_manager.connection.execute("""
                SELECT message_type, COUNT(*) as count
                FROM conversations
                GROUP BY message_type
            """)

            conversation_stats = {row[0]: row[1] for row in await cursor.fetchall()}

            return {
                "email_polling_active": self.email_polling_active,
                "last_email_check": self.last_email_check.isoformat() if self.last_email_check else None,
                "active_missions": len(self.mission_states),
                "lead_stats": lead_stats,
                "conversation_stats": conversation_stats,
                "recent_activity_24h": recent_activity,
                "system_uptime": str(datetime.now() - self.last_activity)
            }

        except Exception as e:
            self.logger.error(f"Failed to get system status: {e}")
            return {"error": str(e)}
    
    def get_mission_state(self, mission_id: int) -> Optional[MissionState]:
        """Get current state of a mission"""
        return self.mission_states.get(mission_id)
    
    async def shutdown(self):
        """Shutdown orchestrator and all agents"""
        self.logger.info("🛑 Shutting down MAESTRO...")
        
        # Stop all agents
        for agent in self.active_agents.values():
            await agent.stop()
        
        # Stop self
        await self.stop()
        
        self.logger.info("✅ MAESTRO shutdown complete")
