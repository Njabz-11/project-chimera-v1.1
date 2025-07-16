"""
Project Chimera - Closer Agent (DIPLOMAT)
Manages replies, answers questions, handles objections, and moves leads toward sales
"""

import time
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_agent import BaseAgent, AgentJob, AgentResult
from tools.email_service import EmailService
from tools.memory_bank import MemoryBank
from utils.llm_service import LLMService

class CloserAgent(BaseAgent):
    """DIPLOMAT - Reply management and deal closing specialist"""

    def __init__(self, db_manager):
        super().__init__("DIPLOMAT", db_manager)
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
        """Execute closer-specific jobs using RAG pattern"""
        start_time = time.time()

        try:
            await self.initialize_services()

            job_type = job.job_type

            if job_type == "process_reply":
                return await self._handle_process_reply(job)
            elif job_type == "handle_objection":
                return await self._handle_objection(job)
            elif job_type == "close_deal":
                return await self._handle_close_deal(job)
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
            self.logger.error(f"Error in CloserAgent: {e}")
            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="error",
                output_data={},
                execution_time_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            )

    async def _handle_process_reply(self, job: AgentJob) -> AgentResult:
        """Process incoming email reply using RAG pattern"""
        start_time = time.time()

        try:
            email_data = job.input_data.get('email_data')
            if not email_data:
                raise ValueError("email_data is required for process_reply job")

            # Extract sender email and find corresponding lead
            sender_email = self._extract_email_address(email_data.get('sender', ''))
            lead = await self.db_manager.find_lead_by_email(sender_email)

            if not lead:
                self.logger.warning(f"No lead found for email: {sender_email}")
                return AgentResult(
                    job_id=job.job_id,
                    agent_name=self.agent_name,
                    status="warning",
                    output_data={"message": "No lead found for sender"},
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )

            lead_id = lead['id']

            # Store incoming message in database
            conversation_data = {
                'lead_id': lead_id,
                'email_id': email_data.get('id'),
                'thread_id': email_data.get('thread_id'),
                'subject': email_data.get('subject'),
                'sender_email': sender_email,
                'message_type': 'incoming',
                'body_preview': email_data.get('snippet', ''),
                'full_body': email_data.get('body', ''),
                'status': 'unread',
                'received_at': datetime.now().isoformat()
            }

            conversation_id = await self.db_manager.create_conversation(conversation_data)

            # Store in memory bank
            memory_data = {
                'type': 'incoming',
                'subject': email_data.get('subject', ''),
                'body': email_data.get('body', ''),
                'sender': sender_email,
                'timestamp': datetime.now().isoformat(),
                'email_id': email_data.get('id'),
                'thread_id': email_data.get('thread_id')
            }

            await self.memory_bank.store_message(lead_id, memory_data)

            # Analyze message intent and generate response
            response_data = await self._generate_rag_response(lead, email_data)

            # Create response draft
            draft_id = await self.email_service.create_draft(
                to=sender_email,
                subject=response_data['subject'],
                body=response_data['body'],
                reply_to_message_id=email_data.get('id')
            )

            if draft_id:
                # Store outgoing draft in database
                response_conversation_data = {
                    'lead_id': lead_id,
                    'thread_id': email_data.get('thread_id'),
                    'subject': response_data['subject'],
                    'recipient_email': sender_email,
                    'message_type': 'outgoing',
                    'body_preview': response_data['body'][:200] + "...",
                    'full_body': response_data['body'],
                    'status': 'draft',
                    'draft_id': draft_id
                }

                response_conversation_id = await self.db_manager.create_conversation(response_conversation_data)

                # Update lead status based on message analysis
                new_status = self._determine_lead_status(email_data.get('body', ''))
                await self.db_manager.update_lead_status(lead_id, new_status)

                # Mark original message as read
                await self.email_service.mark_as_read(email_data.get('id'))
                await self.db_manager.update_conversation_status(conversation_id, 'replied')

                self.logger.info(f"✅ Processed reply and created draft {draft_id} for lead {lead_id}")

                return AgentResult(
                    job_id=job.job_id,
                    agent_name=self.agent_name,
                    status="success",
                    output_data={
                        "lead_id": lead_id,
                        "conversation_id": conversation_id,
                        "response_conversation_id": response_conversation_id,
                        "draft_id": draft_id,
                        "new_lead_status": new_status,
                        "response_preview": response_data['body'][:100] + "..."
                    },
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
            else:
                raise Exception("Failed to create response draft")

        except Exception as e:
            self.logger.error(f"Failed to process reply for job {job.job_id}: {e}")
            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="error",
                output_data={},
                execution_time_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            )

    async def _generate_rag_response(self, lead: Dict[str, Any], email_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate response using Retrieval-Augmented Generation (RAG)"""

        lead_id = lead['id']

        # Retrieve conversation history from memory bank
        conversation_history = await self.memory_bank.retrieve_conversation_history(
            lead_id, limit=10
        )

        # Get mission context
        mission = await self.db_manager.get_mission_by_id(lead['mission_id'])

        # Search for relevant context based on the incoming message
        relevant_context = await self.memory_bank.search_conversations(
            lead_id, email_data.get('body', ''), limit=3
        )

        # Build comprehensive context for LLM
        context = self._build_rag_context(lead, mission, conversation_history, relevant_context, email_data)

        # Generate response using LLM
        prompt = f"""
        You are a professional sales representative responding to a lead's email.

        CONTEXT:
        {context}

        INCOMING MESSAGE:
        Subject: {email_data.get('subject', '')}
        Body: {email_data.get('body', '')}

        INSTRUCTIONS:
        1. Analyze the incoming message for intent (question, objection, interest, etc.)
        2. Reference relevant conversation history appropriately
        3. Address any questions or concerns directly
        4. Provide value and build trust
        5. Move the conversation toward a positive outcome
        6. Maintain professional, helpful tone
        7. Include appropriate next steps

        Generate a response that feels natural and contextual.

        Return JSON format:
        {{
            "subject": "Re: [original subject or new subject]",
            "body": "Professional email response"
        }}
        """

        try:
            response = await self.llm_service.generate_response(prompt)
            import json
            response_text = response.content if hasattr(response, 'content') else str(response)
            return json.loads(response_text)

        except Exception as e:
            self.logger.error(f"Failed to generate RAG response: {e}")
            # Fallback response
            return {
                "subject": f"Re: {email_data.get('subject', 'Your inquiry')}",
                "body": f"""Thank you for your message, {lead.get('contact_name', 'there')}.

I appreciate you taking the time to reach out. Let me address your inquiry and provide some additional information that might be helpful.

I'll follow up with more details shortly.

Best regards,
{mission.get('contact_info', 'The Team') if mission else 'The Team'}"""
            }

    def _build_rag_context(self, lead: Dict[str, Any], mission: Dict[str, Any],
                          conversation_history: List[Dict], relevant_context: List[Dict],
                          email_data: Dict[str, Any]) -> str:
        """Build comprehensive context for RAG response generation"""

        context_parts = []

        # Lead information
        context_parts.append(f"""
        LEAD PROFILE:
        - Company: {lead.get('company_name', 'Unknown')}
        - Contact: {lead.get('contact_name', 'Unknown')}
        - Industry: {lead.get('industry', 'Unknown')}
        - Status: {lead.get('status', 'Unknown')}
        - Pain Points: {lead.get('pain_points', 'Unknown')}
        - Website: {lead.get('website_url', 'N/A')}
        """)

        # Mission context
        if mission:
            context_parts.append(f"""
            BUSINESS CONTEXT:
            - Goal: {mission.get('business_goal', '')}
            - Services: {mission.get('service_offerings', '')}
            - Brand Voice: {mission.get('brand_voice', '')}
            - Target Audience: {mission.get('target_audience', '')}
            """)

        # Recent conversation history
        if conversation_history:
            context_parts.append("RECENT CONVERSATION HISTORY:")
            for msg in conversation_history[-5:]:  # Last 5 messages
                msg_type = msg['metadata'].get('message_type', 'unknown')
                timestamp = msg['metadata'].get('timestamp', '')
                content_preview = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                context_parts.append(f"- {msg_type.upper()} ({timestamp}): {content_preview}")

        # Relevant context from search
        if relevant_context:
            context_parts.append("RELEVANT PREVIOUS DISCUSSIONS:")
            for ctx in relevant_context:
                relevance = ctx.get('relevance_score', 0)
                if relevance > 0.7:  # Only include highly relevant context
                    content_preview = ctx['content'][:100] + "..." if len(ctx['content']) > 100 else ctx['content']
                    context_parts.append(f"- (Relevance: {relevance:.2f}) {content_preview}")

        return "\n".join(context_parts)

    def _extract_email_address(self, sender_string: str) -> str:
        """Extract email address from sender string"""
        # Handle formats like "Name <email@domain.com>" or just "email@domain.com"
        email_pattern = r'<([^>]+)>|([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        match = re.search(email_pattern, sender_string)

        if match:
            return match.group(1) or match.group(2)

        return sender_string.strip()

    def _determine_lead_status(self, message_body: str) -> str:
        """Analyze message content to determine appropriate lead status"""
        message_lower = message_body.lower()

        # Positive indicators
        if any(word in message_lower for word in ['interested', 'yes', 'sounds good', 'let\'s talk', 'schedule', 'meeting']):
            return 'interested'

        # Objection indicators
        elif any(word in message_lower for word in ['not interested', 'no thanks', 'remove', 'unsubscribe']):
            return 'not_interested'

        # Question indicators
        elif any(word in message_lower for word in ['?', 'how', 'what', 'when', 'where', 'why', 'tell me more']):
            return 'engaged'

        # Pricing/negotiation indicators
        elif any(word in message_lower for word in ['price', 'cost', 'budget', 'proposal', 'quote']):
            return 'negotiating'

        # Default to engaged if they replied
        else:
            return 'engaged'

    async def _handle_objection(self, job: AgentJob) -> AgentResult:
        """Handle specific objections with targeted responses"""
        start_time = time.time()

        try:
            lead_id = job.input_data.get('lead_id')
            objection_type = job.input_data.get('objection_type')
            objection_text = job.input_data.get('objection_text', '')

            if not lead_id or not objection_type:
                raise ValueError("lead_id and objection_type are required")

            # Get lead and mission context
            lead = await self.db_manager.get_lead_by_id(lead_id)
            mission = await self.db_manager.get_mission_by_id(lead['mission_id'])

            # Generate objection response
            response_data = await self._generate_objection_response(
                lead, mission, objection_type, objection_text
            )

            # Create draft
            draft_id = await self.email_service.create_draft(
                to=lead['contact_email'],
                subject=response_data['subject'],
                body=response_data['body']
            )

            if draft_id:
                self.logger.info(f"✅ Created objection response draft {draft_id} for lead {lead_id}")

                return AgentResult(
                    job_id=job.job_id,
                    agent_name=self.agent_name,
                    status="success",
                    output_data={
                        "draft_id": draft_id,
                        "lead_id": lead_id,
                        "objection_type": objection_type
                    },
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
            else:
                raise Exception("Failed to create objection response draft")

        except Exception as e:
            self.logger.error(f"Failed to handle objection for job {job.job_id}: {e}")
            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="error",
                output_data={},
                execution_time_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            )

    async def _generate_objection_response(self, lead: Dict[str, Any], mission: Dict[str, Any],
                                         objection_type: str, objection_text: str) -> Dict[str, str]:
        """Generate targeted response to specific objections"""

        prompt = f"""
        Generate a professional response to handle this objection:

        Lead: {lead.get('company_name')} ({lead.get('contact_name')})
        Objection Type: {objection_type}
        Objection Text: {objection_text}

        Our Services: {mission.get('service_offerings', '') if mission else ''}

        Create a response that:
        1. Acknowledges their concern respectfully
        2. Provides relevant information to address the objection
        3. Offers social proof or case studies if appropriate
        4. Suggests a low-risk next step
        5. Maintains professional, helpful tone

        Return JSON format:
        {{
            "subject": "Addressing your concerns about [topic]",
            "body": "Professional objection response"
        }}
        """

        try:
            response = await self.llm_service.generate_response(prompt)
            import json
            response_text = response.content if hasattr(response, 'content') else str(response)
            return json.loads(response_text)
        except Exception as e:
            self.logger.error(f"Failed to generate objection response: {e}")
            return {
                "subject": "Addressing your concerns",
                "body": f"Thank you for sharing your concerns, {lead.get('contact_name', 'there')}. I understand and would like to address them properly."
            }

    async def _handle_close_deal(self, job: AgentJob) -> AgentResult:
        """Handle deal closing process"""
        start_time = time.time()

        try:
            lead_id = job.input_data.get('lead_id')
            close_type = job.input_data.get('close_type', 'soft')

            if not lead_id:
                raise ValueError("lead_id is required for close_deal job")

            # Get lead information
            lead = await self.db_manager.get_lead_by_id(lead_id)
            mission = await self.db_manager.get_mission_by_id(lead['mission_id'])

            # Generate closing email
            close_data = await self._generate_closing_email(lead, mission, close_type)

            # Create draft
            draft_id = await self.email_service.create_draft(
                to=lead['contact_email'],
                subject=close_data['subject'],
                body=close_data['body']
            )

            if draft_id:
                # Update lead status to closing
                await self.db_manager.update_lead_status(lead_id, 'closing')

                self.logger.info(f"✅ Created closing email draft {draft_id} for lead {lead_id}")

                return AgentResult(
                    job_id=job.job_id,
                    agent_name=self.agent_name,
                    status="success",
                    output_data={
                        "draft_id": draft_id,
                        "lead_id": lead_id,
                        "close_type": close_type
                    },
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
            else:
                raise Exception("Failed to create closing email draft")

        except Exception as e:
            self.logger.error(f"Failed to handle deal closing for job {job.job_id}: {e}")
            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="error",
                output_data={},
                execution_time_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            )

    async def _generate_closing_email(self, lead: Dict[str, Any], mission: Dict[str, Any],
                                    close_type: str) -> Dict[str, str]:
        """Generate deal closing email"""

        prompt = f"""
        Generate a {close_type} closing email for this lead:

        Lead: {lead.get('company_name')} ({lead.get('contact_name')})
        Services: {mission.get('service_offerings', '') if mission else ''}

        Create a {close_type} close that:
        1. Summarizes the value proposition
        2. Creates appropriate urgency (if hard close)
        3. Provides clear next steps
        4. Makes it easy to say yes
        5. Maintains professional tone

        Return JSON format:
        {{
            "subject": "Next steps for [company]",
            "body": "Professional closing email"
        }}
        """

        try:
            response = await self.llm_service.generate_response(prompt)
            import json
            response_text = response.content if hasattr(response, 'content') else str(response)
            return json.loads(response_text)
        except Exception as e:
            self.logger.error(f"Failed to generate closing email: {e}")
            return {
                "subject": f"Next steps for {lead.get('company_name')}",
                "body": f"Hi {lead.get('contact_name', 'there')},\n\nI'd like to discuss the next steps for our potential partnership.\n\nBest regards"
            }
