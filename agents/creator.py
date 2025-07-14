"""
Project Chimera - Creator Agent (ARTIFICER)
Creates digital products/services when no human is required
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path

from .base_agent import BaseAgent, AgentJob, AgentResult
from utils.llm_service import llm_service

class CreatorAgent(BaseAgent):
    """ARTIFICER - Digital product and service creation specialist"""

    def __init__(self, db_manager):
        super().__init__("ARTIFICER", db_manager)
        self.deliverables_dir = Path("data/deliverables")
        self.deliverables_dir.mkdir(parents=True, exist_ok=True)

    async def execute(self, job: AgentJob) -> AgentResult:
        """Execute creator-specific jobs"""
        start_time = time.time()

        try:
            if job.job_type == "fulfill_internal":
                result = await self._handle_internal_fulfillment(job.input_data)
            elif job.job_type == "create_digital_product":
                result = await self._create_digital_product(job.input_data)
            elif job.job_type == "generate_report":
                result = await self._generate_report(job.input_data)
            elif job.job_type == "create_script":
                result = await self._create_script(job.input_data)
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

    async def _handle_internal_fulfillment(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle internal fulfillment by creating digital products"""
        try:
            lead_id = input_data.get("lead_id")
            if not lead_id:
                return {"error": "Lead ID is required for internal fulfillment"}

            # Get lead and mission data
            lead = await self.db_manager.get_lead_by_id(lead_id)
            if not lead:
                return {"error": f"Lead {lead_id} not found"}

            mission = await self.db_manager.get_mission_by_id(lead["mission_id"])
            if not mission:
                return {"error": f"Mission {lead['mission_id']} not found"}

            # Determine deliverable type based on requirements
            requirements = input_data.get("project_requirements", {})
            deliverable_type = requirements.get("deliverable_type", "pdf_report")

            # Create the digital product
            if deliverable_type == "pdf_report":
                result = await self._generate_report({
                    "lead": lead,
                    "mission": mission,
                    "requirements": requirements
                })
            elif deliverable_type == "python_script":
                result = await self._create_script({
                    "lead": lead,
                    "mission": mission,
                    "requirements": requirements
                })
            else:
                result = await self._create_digital_product({
                    "lead": lead,
                    "mission": mission,
                    "requirements": requirements,
                    "deliverable_type": deliverable_type
                })

            if "error" in result:
                return result

            # Create fulfillment project record
            project_data = {
                "lead_id": lead_id,
                "mission_id": lead["mission_id"],
                "project_type": "internal",
                "project_title": f"Internal fulfillment for {lead['company_name']}",
                "project_description": result["description"],
                "requirements": requirements,
                "deliverable_type": deliverable_type,
                "deliverable_path": result["file_path"],
                "status": "completed",
                "actual_completion": datetime.now().isoformat()
            }

            project_id = await self.db_manager.create_fulfillment_project(project_data)

            self.logger.info(f"🎯 Created internal fulfillment project {project_id} for lead {lead_id}")

            return {
                "project_id": project_id,
                "deliverable_path": result["file_path"],
                "deliverable_type": deliverable_type,
                "description": result["description"],
                "status": "completed"
            }

        except Exception as e:
            self.logger.error(f"Error in internal fulfillment: {e}")
            return {"error": str(e)}

    async def _generate_report(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a comprehensive PDF report"""
        try:
            lead = input_data["lead"]
            mission = input_data["mission"]
            requirements = input_data.get("requirements", {})

            # Create comprehensive prompt for report generation
            system_prompt = """You are a professional business consultant creating detailed reports.
Generate comprehensive, well-structured content that provides real value to the client.
Include executive summary, analysis, recommendations, and actionable insights.
Format the content with clear headings and professional structure."""

            user_prompt = f"""Create a comprehensive business report for the following client:

CLIENT INFORMATION:
- Company: {lead['company_name']}
- Industry: {lead.get('industry', 'Not specified')}
- Contact: {lead.get('contact_name', 'Not specified')}
- Company Size: {lead.get('company_size', 'Not specified')}
- Pain Points: {json.dumps(lead.get('pain_points', []))}

BUSINESS CONTEXT:
- Business Goal: {mission['business_goal']}
- Target Audience: {mission['target_audience']}
- Brand Voice: {mission['brand_voice']}
- Service Offerings: {json.dumps(mission['service_offerings'])}

REPORT REQUIREMENTS:
{json.dumps(requirements, indent=2)}

Generate a detailed report with the following structure:
1. Executive Summary
2. Current Situation Analysis
3. Market Opportunities
4. Strategic Recommendations
5. Implementation Plan
6. Success Metrics
7. Conclusion

Make it professional, actionable, and valuable for the client."""

            response = await llm_service.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=4000,
                temperature=0.7
            )

            if response.error:
                return {"error": f"LLM generation failed: {response.error}"}

            # Save report to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{lead['company_name'].replace(' ', '_')}_{timestamp}.txt"
            file_path = self.deliverables_dir / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"BUSINESS REPORT FOR {lead['company_name'].upper()}\n")
                f.write("=" * 50 + "\n\n")
                f.write(response.content)

            self.logger.info(f"📄 Generated report for {lead['company_name']}: {filename}")

            return {
                "file_path": str(file_path),
                "description": f"Comprehensive business report for {lead['company_name']}",
                "word_count": len(response.content.split()),
                "generated_at": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error generating report: {e}")
            return {"error": str(e)}

    async def _create_script(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a Python script based on requirements"""
        try:
            lead = input_data["lead"]
            mission = input_data["mission"]
            requirements = input_data.get("requirements", {})

            system_prompt = """You are a professional Python developer creating production-ready scripts.
Generate clean, well-documented, and functional Python code that solves the client's specific needs.
Include proper error handling, comments, and usage instructions."""

            user_prompt = f"""Create a Python script for the following client:

CLIENT INFORMATION:
- Company: {lead['company_name']}
- Industry: {lead.get('industry', 'Not specified')}
- Pain Points: {json.dumps(lead.get('pain_points', []))}

BUSINESS CONTEXT:
- Business Goal: {mission['business_goal']}
- Service Offerings: {json.dumps(mission['service_offerings'])}

SCRIPT REQUIREMENTS:
{json.dumps(requirements, indent=2)}

Generate a complete Python script that addresses the client's needs. Include:
1. Proper imports and dependencies
2. Clear function definitions
3. Error handling
4. Documentation and comments
5. Usage examples
6. Main execution block

Make it production-ready and well-documented."""

            response = await llm_service.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=3000,
                temperature=0.3  # Lower temperature for more consistent code
            )

            if response.error:
                return {"error": f"LLM generation failed: {response.error}"}

            # Save script to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"script_{lead['company_name'].replace(' ', '_')}_{timestamp}.py"
            file_path = self.deliverables_dir / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f'"""\nPython Script for {lead["company_name"]}\n')
                f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f'"""\n\n')
                f.write(response.content)

            self.logger.info(f"🐍 Generated Python script for {lead['company_name']}: {filename}")

            return {
                "file_path": str(file_path),
                "description": f"Custom Python script for {lead['company_name']}",
                "lines_of_code": len(response.content.split('\n')),
                "generated_at": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error creating script: {e}")
            return {"error": str(e)}

    async def _create_digital_product(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a generic digital product based on type"""
        try:
            lead = input_data["lead"]
            mission = input_data["mission"]
            requirements = input_data.get("requirements", {})
            deliverable_type = input_data.get("deliverable_type", "document")

            # Map deliverable types to file extensions and content types
            type_mapping = {
                "marketing_plan": {"ext": "txt", "content": "marketing strategy and plan"},
                "business_plan": {"ext": "txt", "content": "comprehensive business plan"},
                "seo_audit": {"ext": "txt", "content": "SEO audit and recommendations"},
                "content_strategy": {"ext": "txt", "content": "content marketing strategy"},
                "social_media_plan": {"ext": "txt", "content": "social media strategy and calendar"},
                "email_campaign": {"ext": "txt", "content": "email marketing campaign"},
                "document": {"ext": "txt", "content": "business document"}
            }

            mapping = type_mapping.get(deliverable_type, type_mapping["document"])

            system_prompt = f"""You are a professional business consultant creating a detailed {mapping['content']}.
Generate comprehensive, actionable content that provides real value to the client.
Structure the content professionally with clear sections and practical recommendations."""

            user_prompt = f"""Create a detailed {mapping['content']} for the following client:

CLIENT INFORMATION:
- Company: {lead['company_name']}
- Industry: {lead.get('industry', 'Not specified')}
- Contact: {lead.get('contact_name', 'Not specified')}
- Company Size: {lead.get('company_size', 'Not specified')}
- Pain Points: {json.dumps(lead.get('pain_points', []))}

BUSINESS CONTEXT:
- Business Goal: {mission['business_goal']}
- Target Audience: {mission['target_audience']}
- Brand Voice: {mission['brand_voice']}
- Service Offerings: {json.dumps(mission['service_offerings'])}

SPECIFIC REQUIREMENTS:
{json.dumps(requirements, indent=2)}

Generate comprehensive content that addresses the client's specific needs and provides actionable value."""

            response = await llm_service.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=3500,
                temperature=0.7
            )

            if response.error:
                return {"error": f"LLM generation failed: {response.error}"}

            # Save product to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{deliverable_type}_{lead['company_name'].replace(' ', '_')}_{timestamp}.{mapping['ext']}"
            file_path = self.deliverables_dir / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"{mapping['content'].upper()} FOR {lead['company_name'].upper()}\n")
                f.write("=" * 60 + "\n\n")
                f.write(response.content)

            self.logger.info(f"📦 Generated {deliverable_type} for {lead['company_name']}: {filename}")

            return {
                "file_path": str(file_path),
                "description": f"{mapping['content'].title()} for {lead['company_name']}",
                "deliverable_type": deliverable_type,
                "word_count": len(response.content.split()),
                "generated_at": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error creating digital product: {e}")
            return {"error": str(e)}
