"""
Project Chimera - Strategist Agent (ARCHITECT)
Processes client input into actionable Mission Briefings
"""

import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_agent import BaseAgent, AgentJob, AgentResult
from utils.llm_service import LLMService

class StrategistAgent(BaseAgent):
    """ARCHITECT - Strategic mission planning and briefing analysis"""

    def __init__(self, db_manager):
        super().__init__("ARCHITECT", db_manager)
        self.llm_service = LLMService()

    async def execute(self, job: AgentJob) -> AgentResult:
        """Execute strategist-specific jobs"""
        start_time = time.time()
        job_type = job.job_type

        try:
            if job_type == "create_mission_brief":
                return await self._create_mission_brief(job)
            elif job_type == "analyze_market":
                return await self._analyze_market(job)
            elif job_type == "develop_strategy":
                return await self._develop_strategy(job)
            elif job_type == "refine_brief":
                return await self._refine_brief(job)
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
            self.logger.error(f"Strategist execution failed: {e}")
            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="error",
                output_data={"error": str(e)},
                execution_time_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            )

    async def _create_mission_brief(self, job: AgentJob) -> AgentResult:
        """Create a structured Mission Briefing from client input"""
        client_input = job.input_data.get("client_input", {})

        # Extract key information from client input
        business_goal = client_input.get("business_goal", "")
        target_audience = client_input.get("target_audience", "")
        brand_voice = client_input.get("brand_voice", "")
        service_offerings = client_input.get("service_offerings", [])
        budget_range = client_input.get("budget_range", "")
        timeline = client_input.get("timeline", "")

        if not business_goal:
            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="error",
                output_data={},
                execution_time_ms=0,
                error_message="Business goal is required for mission brief creation"
            )

        # Use LLM to analyze and structure the input
        structured_brief = await self._analyze_and_structure_input(client_input)

        # Create the mission briefing object
        mission_briefing = {
            "mission_id": job.input_data.get("mission_id"),
            "created_at": datetime.now().isoformat(),
            "business_goal": structured_brief.get("business_goal", business_goal),
            "target_audience": structured_brief.get("target_audience", target_audience),
            "brand_voice": structured_brief.get("brand_voice", brand_voice),
            "service_offerings": structured_brief.get("service_offerings", service_offerings),
            "value_proposition": structured_brief.get("value_proposition", ""),
            "key_messaging": structured_brief.get("key_messaging", []),
            "success_metrics": structured_brief.get("success_metrics", []),
            "budget_range": budget_range,
            "timeline": timeline,
            "strategic_approach": structured_brief.get("strategic_approach", ""),
            "content_themes": structured_brief.get("content_themes", []),
            "lead_qualification_criteria": structured_brief.get("lead_qualification_criteria", {}),
            "competitive_advantages": structured_brief.get("competitive_advantages", [])
        }

        # Save mission briefing to database
        try:
            mission_id = await self._save_mission_briefing(mission_briefing)
            mission_briefing["mission_id"] = mission_id
        except Exception as e:
            self.logger.error(f"Failed to save mission briefing: {e}")

        return AgentResult(
            job_id=job.job_id,
            agent_name=self.agent_name,
            status="success",
            output_data={
                "mission_briefing": mission_briefing,
                "analysis_summary": structured_brief.get("analysis_summary", ""),
                "recommendations": structured_brief.get("recommendations", [])
            },
            execution_time_ms=int((time.time() - time.time()) * 1000)
        )

    async def _analyze_market(self, job: AgentJob) -> AgentResult:
        """Analyze market conditions and competitive landscape"""
        industry = job.input_data.get("industry", "")
        target_market = job.input_data.get("target_market", "")

        market_analysis = await self._conduct_market_analysis(industry, target_market)

        return AgentResult(
            job_id=job.job_id,
            agent_name=self.agent_name,
            status="success",
            output_data={
                "market_analysis": market_analysis,
                "competitive_insights": market_analysis.get("competitive_insights", []),
                "market_opportunities": market_analysis.get("opportunities", []),
                "market_threats": market_analysis.get("threats", [])
            },
            execution_time_ms=0
        )

    async def _develop_strategy(self, job: AgentJob) -> AgentResult:
        """Develop strategic approach based on mission brief"""
        mission_brief = job.input_data.get("mission_brief", {})

        strategy = await self._create_strategic_plan(mission_brief)

        return AgentResult(
            job_id=job.job_id,
            agent_name=self.agent_name,
            status="success",
            output_data={
                "strategic_plan": strategy,
                "action_items": strategy.get("action_items", []),
                "timeline": strategy.get("timeline", {}),
                "resource_requirements": strategy.get("resource_requirements", {})
            },
            execution_time_ms=0
        )

    async def _refine_brief(self, job: AgentJob) -> AgentResult:
        """Refine existing mission brief based on feedback or new information"""
        mission_id = job.input_data.get("mission_id")
        refinements = job.input_data.get("refinements", {})

        # Get existing mission brief
        existing_brief = await self.db_manager.get_mission_by_id(mission_id)
        if not existing_brief:
            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="error",
                output_data={},
                execution_time_ms=0,
                error_message=f"Mission {mission_id} not found"
            )

        # Apply refinements
        refined_brief = await self._apply_refinements(existing_brief, refinements)

        # Update in database
        await self._update_mission_briefing(mission_id, refined_brief)

        return AgentResult(
            job_id=job.job_id,
            agent_name=self.agent_name,
            status="success",
            output_data={
                "refined_brief": refined_brief,
                "changes_made": refinements,
                "mission_id": mission_id
            },
            execution_time_ms=0
        )

    async def _analyze_and_structure_input(self, client_input: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM to analyze and structure client input into a comprehensive brief"""
        prompt = f"""
        Analyze the following client input and create a structured business strategy brief:

        CLIENT INPUT:
        {json.dumps(client_input, indent=2)}

        Please provide a comprehensive analysis and create structured output with:

        1. REFINED BUSINESS GOAL: Clear, specific, measurable objective
        2. TARGET AUDIENCE: Detailed persona and demographics
        3. VALUE PROPOSITION: Unique selling points and benefits
        4. KEY MESSAGING: Core messages that resonate with target audience
        5. SUCCESS METRICS: Measurable KPIs and goals
        6. STRATEGIC APPROACH: High-level strategy and methodology
        7. CONTENT THEMES: Topics and themes for content creation
        8. LEAD QUALIFICATION CRITERIA: Ideal customer profile
        9. COMPETITIVE ADVANTAGES: Unique strengths and differentiators
        10. ANALYSIS SUMMARY: Key insights and observations
        11. RECOMMENDATIONS: Strategic recommendations for success

        Respond with a JSON object containing all these elements.
        """

        try:
            response = await self.llm_service.generate_response(
                prompt=prompt,
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                temperature=0.3
            )

            # Parse JSON response
            structured_data = json.loads(response)
            return structured_data

        except Exception as e:
            self.logger.error(f"LLM analysis failed: {e}")
            # Return basic structure if LLM fails
            return {
                "business_goal": client_input.get("business_goal", ""),
                "target_audience": client_input.get("target_audience", ""),
                "value_proposition": "To be defined",
                "key_messaging": [],
                "success_metrics": ["Lead generation", "Conversion rate"],
                "strategic_approach": "Multi-channel outreach and content marketing",
                "content_themes": ["Industry insights", "Problem solving"],
                "lead_qualification_criteria": {"budget": "TBD", "authority": "Decision maker"},
                "competitive_advantages": [],
                "analysis_summary": "Basic analysis completed",
                "recommendations": ["Define clear value proposition", "Identify target market"]
            }

    async def _conduct_market_analysis(self, industry: str, target_market: str) -> Dict[str, Any]:
        """Conduct market analysis using LLM"""
        prompt = f"""
        Conduct a market analysis for the following:
        Industry: {industry}
        Target Market: {target_market}

        Provide analysis on:
        1. Market size and growth trends
        2. Key competitors and their positioning
        3. Market opportunities and gaps
        4. Potential threats and challenges
        5. Customer behavior and preferences
        6. Pricing strategies in the market
        7. Distribution channels
        8. Regulatory considerations

        Respond with a JSON object containing competitive_insights, opportunities, threats, and market_overview.
        """

        try:
            response = await self.llm_service.generate_response(
                prompt=prompt,
                model="claude-3-sonnet-20240229",
                max_tokens=1500,
                temperature=0.2
            )

            return json.loads(response)

        except Exception as e:
            self.logger.error(f"Market analysis failed: {e}")
            return {
                "competitive_insights": ["Analysis unavailable"],
                "opportunities": ["Market research needed"],
                "threats": ["Competition analysis required"],
                "market_overview": "Detailed analysis unavailable"
            }

    async def _create_strategic_plan(self, mission_brief: Dict[str, Any]) -> Dict[str, Any]:
        """Create strategic plan based on mission brief"""
        prompt = f"""
        Create a strategic plan based on this mission brief:
        {json.dumps(mission_brief, indent=2)}

        Develop a comprehensive strategic plan including:
        1. Strategic objectives and goals
        2. Action items with priorities
        3. Timeline and milestones
        4. Resource requirements
        5. Risk assessment and mitigation
        6. Success metrics and KPIs
        7. Implementation phases

        Respond with a JSON object containing these elements.
        """

        try:
            response = await self.llm_service.generate_response(
                prompt=prompt,
                model="claude-3-sonnet-20240229",
                max_tokens=1500,
                temperature=0.3
            )

            return json.loads(response)

        except Exception as e:
            self.logger.error(f"Strategic planning failed: {e}")
            return {
                "action_items": ["Define strategy", "Execute plan"],
                "timeline": {"phase1": "30 days", "phase2": "60 days"},
                "resource_requirements": {"team": "TBD", "budget": "TBD"}
            }

    async def _apply_refinements(self, existing_brief: Dict[str, Any], refinements: Dict[str, Any]) -> Dict[str, Any]:
        """Apply refinements to existing mission brief"""
        refined_brief = existing_brief.copy()

        # Apply direct updates
        for key, value in refinements.items():
            if key in refined_brief:
                refined_brief[key] = value

        # Update timestamp
        refined_brief["updated_at"] = datetime.now().isoformat()

        return refined_brief

    async def _save_mission_briefing(self, mission_briefing: Dict[str, Any]) -> int:
        """Save mission briefing to database"""
        try:
            cursor = await self.db_manager.connection.execute("""
                INSERT INTO missions (
                    business_goal, target_audience, brand_voice, service_offerings,
                    value_proposition, key_messaging, success_metrics, budget_range,
                    timeline, strategic_approach, content_themes, lead_qualification_criteria,
                    competitive_advantages, created_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                mission_briefing.get("business_goal", ""),
                mission_briefing.get("target_audience", ""),
                mission_briefing.get("brand_voice", ""),
                json.dumps(mission_briefing.get("service_offerings", [])),
                mission_briefing.get("value_proposition", ""),
                json.dumps(mission_briefing.get("key_messaging", [])),
                json.dumps(mission_briefing.get("success_metrics", [])),
                mission_briefing.get("budget_range", ""),
                mission_briefing.get("timeline", ""),
                mission_briefing.get("strategic_approach", ""),
                json.dumps(mission_briefing.get("content_themes", [])),
                json.dumps(mission_briefing.get("lead_qualification_criteria", {})),
                json.dumps(mission_briefing.get("competitive_advantages", [])),
                mission_briefing.get("created_at", datetime.now().isoformat()),
                "active"
            ))

            await self.db_manager.connection.commit()
            return cursor.lastrowid

        except Exception as e:
            self.logger.error(f"Failed to save mission briefing: {e}")
            raise

    async def _update_mission_briefing(self, mission_id: int, refined_brief: Dict[str, Any]):
        """Update existing mission briefing"""
        try:
            await self.db_manager.connection.execute("""
                UPDATE missions SET
                    business_goal = ?, target_audience = ?, brand_voice = ?,
                    service_offerings = ?, value_proposition = ?, key_messaging = ?,
                    success_metrics = ?, strategic_approach = ?, content_themes = ?,
                    lead_qualification_criteria = ?, competitive_advantages = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                refined_brief.get("business_goal", ""),
                refined_brief.get("target_audience", ""),
                refined_brief.get("brand_voice", ""),
                json.dumps(refined_brief.get("service_offerings", [])),
                refined_brief.get("value_proposition", ""),
                json.dumps(refined_brief.get("key_messaging", [])),
                json.dumps(refined_brief.get("success_metrics", [])),
                refined_brief.get("strategic_approach", ""),
                json.dumps(refined_brief.get("content_themes", [])),
                json.dumps(refined_brief.get("lead_qualification_criteria", {})),
                json.dumps(refined_brief.get("competitive_advantages", [])),
                refined_brief.get("updated_at", datetime.now().isoformat()),
                mission_id
            ))

            await self.db_manager.connection.commit()

        except Exception as e:
            self.logger.error(f"Failed to update mission briefing: {e}")
            raise
