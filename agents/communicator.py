"""
Project Chimera - Communicator Agent (HERALD)
Initiates personalized first-contact with new leads
"""

import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from .base_agent import BaseAgent, AgentJob, AgentResult
from tools.email_service import EmailService
from tools.memory_bank import MemoryBank
from utils.llm_service import LLMService

class CommunicatorAgent(BaseAgent):
    """HERALD - First-contact and outreach specialist"""

    def __init__(self, db_manager):
        super().__init__("HERALD", db_manager)
        self.email_service = EmailService()
        self.memory_bank = MemoryBank()
        self.llm_service = LLMService()
        self.initialized = False

    async def initialize_services(self):
        """Initialize email and memory services"""
        if not self.initialized:
            await self.email_service.initialize()
            await self.memory_bank.initialize()
            self.initialized = True

    async def execute(self, job: AgentJob) -> AgentResult:
        """Execute communicator-specific jobs"""
        start_time = time.time()

        try:
            await self.initialize_services()

            job_type = job.job_type

            if job_type == "draft_outreach":
                return await self._handle_draft_outreach(job)
            elif job_type == "send_follow_up":
                return await self._handle_follow_up(job)
            else:
                return AgentResult(
                    job_id=job.job_id,
                    agent_name=self.agent_name,
                    status="error",
                    output_data={},
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    error_message=f"Unknown job type: {job_type}"
                )

        except Exception as e:
            self.logger.error(f"Error in CommunicatorAgent: {e}")
            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="error",
                output_data={},
                execution_time_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            )

    async def _handle_draft_outreach(self, job: AgentJob) -> AgentResult:
        """Handle drafting first-touch outreach email"""
        start_time = time.time()

        try:
            lead_id = job.input_data.get('lead_id')
            if not lead_id:
                raise ValueError("lead_id is required for draft_outreach job")

            # Get lead information
            lead = await self.db_manager.get_lead_by_id(lead_id)
            if not lead:
                raise ValueError(f"Lead {lead_id} not found")

            # Get mission briefing
            mission = await self.db_manager.get_mission_by_id(lead['mission_id'])
            if not mission:
                raise ValueError(f"Mission {lead['mission_id']} not found")

            # Generate personalized outreach email
            email_content = await self._generate_outreach_email(lead, mission)

            # Create email draft
            draft_id = await self.email_service.create_draft(
                to=lead['contact_email'],
                subject=email_content['subject'],
                body=email_content['body']
            )

            if draft_id:
                # Store conversation record
                conversation_data = {
                    'lead_id': lead_id,
                    'subject': email_content['subject'],
                    'recipient_email': lead['contact_email'],
                    'message_type': 'outgoing',
                    'body_preview': email_content['body'][:200] + "..." if len(email_content['body']) > 200 else email_content['body'],
                    'full_body': email_content['body'],
                    'status': 'draft',
                    'draft_id': draft_id,
                    'sent_at': None,
                    'received_at': None
                }

                conversation_id = await self.db_manager.create_conversation(conversation_data)

                # Create memory bank collection for this lead
                await self.memory_bank.create_lead_collection(lead_id)

                # Store in memory bank
                memory_data = {
                    'type': 'outgoing',
                    'subject': email_content['subject'],
                    'body': email_content['body'],
                    'sender': 'system',
                    'timestamp': datetime.now().isoformat(),
                    'context': f"First outreach email for {lead['company_name']}"
                }

                await self.memory_bank.store_message(lead_id, memory_data)

                # Update lead status
                await self.db_manager.update_lead_status(lead_id, 'contacted')

                self.logger.info(f"✅ Created outreach draft {draft_id} for lead {lead_id}")

                return AgentResult(
                    job_id=job.job_id,
                    agent_name=self.agent_name,
                    status="success",
                    output_data={
                        "draft_id": draft_id,
                        "conversation_id": conversation_id,
                        "lead_id": lead_id,
                        "subject": email_content['subject'],
                        "preview": email_content['body'][:100] + "..."
                    },
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
            else:
                raise Exception("Failed to create email draft")

        except Exception as e:
            self.logger.error(f"Failed to draft outreach for job {job.job_id}: {e}")
            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="error",
                output_data={},
                execution_time_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            )

    async def _generate_outreach_email(self, lead: Dict[str, Any], mission: Dict[str, Any]) -> Dict[str, str]:
        """Generate personalized outreach email using LLM"""

        # Prepare context for LLM
        context = f"""
        Lead Information:
        - Company: {lead.get('company_name', 'Unknown')}
        - Industry: {lead.get('industry', 'Unknown')}
        - Website: {lead.get('website_url', 'N/A')}
        - Pain Points: {lead.get('pain_points', 'Unknown')}
        - Contact: {lead.get('contact_name', 'Unknown')}

        Mission Context:
        - Business Goal: {mission.get('business_goal', '')}
        - Target Audience: {mission.get('target_audience', '')}
        - Brand Voice: {mission.get('brand_voice', '')}
        - Service Offerings: {mission.get('service_offerings', '')}
        """

        prompt = f"""
        You are a professional business development specialist writing a personalized first-touch outreach email.

        {context}

        Write a compelling, personalized outreach email that:
        1. Addresses the lead by name (if available) or company
        2. Shows you've researched their business
        3. Identifies a specific pain point or opportunity
        4. Briefly explains how your services can help
        5. Includes a clear, low-pressure call to action
        6. Maintains the specified brand voice
        7. Is concise (under 150 words)
        8. Feels personal, not templated

        Return the response in this exact JSON format:
        {{
            "subject": "Subject line here",
            "body": "Email body here"
        }}
        """

        try:
            response = await self.llm_service.generate_response(prompt)

            # Parse JSON response
            import json
            # Handle LLMResponse object
            response_text = response.content if hasattr(response, 'content') else str(response)
            email_content = json.loads(response_text)

            # Validate required fields
            if 'subject' not in email_content or 'body' not in email_content:
                raise ValueError("LLM response missing required fields")

            return email_content

        except Exception as e:
            self.logger.error(f"Failed to generate outreach email: {e}")
            # Fallback to template
            return {
                "subject": f"Partnership opportunity with {lead.get('company_name', 'your company')}",
                "body": f"""Hi {lead.get('contact_name', 'there')},

I noticed {lead.get('company_name', 'your company')} and thought there might be a great opportunity for collaboration.

{mission.get('service_offerings', 'Our services')} could help address some of the challenges in {lead.get('industry', 'your industry')}.

Would you be open to a brief conversation to explore this further?

Best regards,
{mission.get('contact_info', 'The Team')}"""
            }

    async def _handle_follow_up(self, job: AgentJob) -> AgentResult:
        """Handle follow-up email generation"""
        start_time = time.time()

        try:
            lead_id = job.input_data.get('lead_id')
            follow_up_type = job.input_data.get('follow_up_type', 'general')

            if not lead_id:
                raise ValueError("lead_id is required for follow_up job")

            # Get lead and conversation history
            lead = await self.db_manager.get_lead_by_id(lead_id)
            conversations = await self.db_manager.get_conversations_by_lead(lead_id)

            # Get relevant context from memory bank
            context_messages = await self.memory_bank.retrieve_conversation_history(
                lead_id, limit=5
            )

            # Generate follow-up email
            email_content = await self._generate_follow_up_email(
                lead, conversations, context_messages, follow_up_type
            )

            # Create draft
            draft_id = await self.email_service.create_draft(
                to=lead['contact_email'],
                subject=email_content['subject'],
                body=email_content['body']
            )

            if draft_id:
                self.logger.info(f"✅ Created follow-up draft {draft_id} for lead {lead_id}")

                return AgentResult(
                    job_id=job.job_id,
                    agent_name=self.agent_name,
                    status="success",
                    output_data={
                        "draft_id": draft_id,
                        "lead_id": lead_id,
                        "follow_up_type": follow_up_type
                    },
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
            else:
                raise Exception("Failed to create follow-up draft")

        except Exception as e:
            self.logger.error(f"Failed to create follow-up for job {job.job_id}: {e}")
            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="error",
                output_data={},
                execution_time_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            )

    async def _generate_follow_up_email(self, lead: Dict[str, Any],
                                       conversations: List[Dict[str, Any]],
                                       context_messages: List[Dict[str, Any]],
                                       follow_up_type: str) -> Dict[str, str]:
        """Generate follow-up email based on conversation history"""

        # Build conversation context
        conversation_summary = "\n".join([
            f"- {conv['message_type']}: {conv['body_preview']}"
            for conv in conversations[-3:]  # Last 3 conversations
        ])

        prompt = f"""
        Generate a follow-up email for this lead:

        Lead: {lead.get('company_name')} ({lead.get('contact_name')})
        Follow-up Type: {follow_up_type}

        Recent Conversation History:
        {conversation_summary}

        Create a {follow_up_type} follow-up email that:
        1. References previous interactions appropriately
        2. Provides additional value
        3. Maintains professional tone
        4. Includes clear next steps

        Return JSON format:
        {{
            "subject": "Subject line",
            "body": "Email body"
        }}
        """

        try:
            response = await self.llm_service.generate_response(prompt)
            import json
            response_text = response.content if hasattr(response, 'content') else str(response)
            return json.loads(response_text)
        except Exception as e:
            self.logger.error(f"Failed to generate follow-up email: {e}")
            return {
                "subject": f"Following up on our conversation",
                "body": f"Hi {lead.get('contact_name', 'there')},\n\nI wanted to follow up on our previous conversation.\n\nBest regards"
            }
