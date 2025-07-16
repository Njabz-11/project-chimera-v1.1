"""
Project Chimera - Dispatcher Agent (QUARTERMASTER)
Manages fulfillment process by hiring and briefing external freelancers
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from .base_agent import BaseAgent, AgentJob, AgentResult
from utils.llm_service import llm_service

class DispatcherAgent(BaseAgent):
    """QUARTERMASTER - External fulfillment and resource management specialist"""

    def __init__(self, db_manager):
        super().__init__("QUARTERMASTER", db_manager)

    async def execute(self, job: AgentJob) -> AgentResult:
        """Execute dispatcher-specific jobs"""
        start_time = time.time()

        try:
            if job.job_type == "fulfill_external":
                result = await self._handle_external_fulfillment(job.input_data)
            elif job.job_type == "generate_freelancer_brief":
                result = await self._generate_freelancer_brief(job.input_data)
            else:
                self.logger.warning(f"Unknown job type: {job.job_type}")
                result = {"error": f"Unknown job type: {job.job_type}"}

            execution_time = int((time.time() - start_time) * 1000)

            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="success" if "error" not in result else "error",
                output_data=result,
                execution_time_ms=execution_time,
                error_message=result.get("error")
            )

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.logger.error(f"Error in {self.agent_name} execution: {e}")

            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="error",
                output_data={"error": str(e)},
                execution_time_ms=execution_time,
                error_message=str(e)
            )

    async def _handle_external_fulfillment(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle external fulfillment by creating freelancer brief"""
        try:
            lead_id = input_data.get("lead_id")
            if not lead_id:
                return {"error": "Lead ID is required for external fulfillment"}

            # Get lead and mission data
            lead = await self.db_manager.get_lead_by_id(lead_id)
            if not lead:
                return {"error": f"Lead {lead_id} not found"}

            mission = await self.db_manager.get_mission_by_id(lead["mission_id"])
            if not mission:
                return {"error": f"Mission {lead['mission_id']} not found"}

            # Get conversation history for context
            conversations = await self.db_manager.get_conversations_by_lead(lead_id)

            # Generate freelancer brief
            brief_result = await self._generate_freelancer_brief({
                "lead": lead,
                "mission": mission,
                "conversations": conversations,
                "project_requirements": input_data.get("project_requirements", {})
            })

            if "error" in brief_result:
                return brief_result

            # Create fulfillment project record
            project_data = {
                "lead_id": lead_id,
                "mission_id": lead["mission_id"],
                "project_type": "external",
                "project_title": f"External fulfillment for {lead['company_name']}",
                "project_description": brief_result["project_description"],
                "requirements": input_data.get("project_requirements", {}),
                "deliverable_type": "freelancer_brief",
                "freelancer_brief": brief_result["freelancer_brief"],
                "status": "pending",
                "estimated_completion": (datetime.now() + timedelta(days=14)).isoformat()
            }

            project_id = await self.db_manager.create_fulfillment_project(project_data)

            self.logger.info(f"📋 Created external fulfillment project {project_id} for lead {lead_id}")

            return {
                "project_id": project_id,
                "freelancer_brief": brief_result["freelancer_brief"],
                "project_description": brief_result["project_description"],
                "estimated_timeline": "14 days",
                "status": "ready_for_posting"
            }

        except Exception as e:
            self.logger.error(f"Error in external fulfillment: {e}")
            return {"error": str(e)}

    async def _generate_freelancer_brief(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a detailed freelancer job posting using LLM"""
        try:
            lead = input_data["lead"]
            mission = input_data["mission"]
            conversations = input_data.get("conversations", [])
            requirements = input_data.get("project_requirements", {})

            # Build context from conversations
            conversation_context = ""
            if conversations:
                conversation_context = "\n\nConversation History:\n"
                for conv in conversations[-5:]:  # Last 5 conversations
                    conversation_context += f"- {conv['message_type']}: {conv['body_preview']}\n"

            # Create comprehensive prompt for freelancer brief
            system_prompt = """You are a professional project manager creating detailed freelancer job postings.
Your job is to synthesize business requirements, client conversations, and project needs into a comprehensive,
professional freelancer brief that will attract qualified candidates.

Create a job posting that includes:
1. Clear project title and overview
2. Detailed scope of work
3. Required skills and qualifications
4. Deliverables and timeline
5. Budget guidance (if applicable)
6. Communication expectations

Make it professional, specific, and actionable."""

            user_prompt = f"""Create a detailed freelancer job posting based on this information:

BUSINESS CONTEXT:
- Company: {lead['company_name']}
- Industry: {lead.get('industry', 'Not specified')}
- Business Goal: {mission['business_goal']}
- Target Audience: {mission['target_audience']}
- Service Offerings: {json.dumps(mission['service_offerings'])}

CLIENT DETAILS:
- Contact: {lead.get('contact_name', 'Not specified')}
- Company Size: {lead.get('company_size', 'Not specified')}
- Pain Points: {json.dumps(lead.get('pain_points', []))}

PROJECT REQUIREMENTS:
{json.dumps(requirements, indent=2)}

{conversation_context}

Generate a comprehensive freelancer job posting that addresses the client's needs and provides clear direction for potential freelancers."""

            response = await llm_service.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=2000,
                temperature=0.7
            )

            if response.error:
                return {"error": f"LLM generation failed: {response.error}"}

            # Extract project description from the brief
            brief_lines = response.content.split('\n')
            project_description = f"External fulfillment project for {lead['company_name']}"

            # Look for project overview or description in the brief
            for i, line in enumerate(brief_lines):
                if any(keyword in line.lower() for keyword in ['overview', 'description', 'project']):
                    if i + 1 < len(brief_lines):
                        project_description = brief_lines[i + 1].strip()
                        break

            self.logger.info(f"📝 Generated freelancer brief for {lead['company_name']}")

            return {
                "freelancer_brief": response.content,
                "project_description": project_description,
                "generated_at": datetime.now().isoformat(),
                "word_count": len(response.content.split())
            }

        except Exception as e:
            self.logger.error(f"Error generating freelancer brief: {e}")
            return {"error": str(e)}
