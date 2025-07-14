"""
Project Chimera - Bard Agent (LOREWEAVER)
Builds brand authority via content generation and publication
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from .base_agent import BaseAgent, AgentJob, AgentResult
from utils.llm_service import llm_service

class BardAgent(BaseAgent):
    """LOREWEAVER - Content creation and brand authority specialist"""

    def __init__(self, db_manager):
        super().__init__("LOREWEAVER", db_manager)

    async def execute(self, job: AgentJob) -> AgentResult:
        """Execute bard-specific jobs"""
        start_time = time.time()

        try:
            if job.job_type == "generate_content_calendar":
                result = await self._generate_content_calendar(job.input_data)
            elif job.job_type == "create_content":
                result = await self._create_content(job.input_data)
            elif job.job_type == "generate_blog_post":
                result = await self._generate_blog_post(job.input_data)
            elif job.job_type == "create_social_media_post":
                result = await self._create_social_media_post(job.input_data)
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

    async def _generate_content_calendar(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a 30-day content calendar based on mission briefing"""
        try:
            mission_id = input_data.get("mission_id")
            if not mission_id:
                return {"error": "Mission ID is required for content calendar generation"}

            # Get mission data
            mission = await self.db_manager.get_mission_by_id(mission_id)
            if not mission:
                return {"error": f"Mission {mission_id} not found"}

            # Create comprehensive prompt for content calendar
            system_prompt = """You are a professional content marketing strategist creating a 30-day content calendar.
Generate diverse, engaging content ideas that align with the business goals and target audience.
Include a mix of content types: blog posts, social media posts, videos, infographics, etc.
Ensure content builds brand authority and provides value to the target audience."""

            user_prompt = f"""Create a comprehensive 30-day content calendar for the following business:

BUSINESS CONTEXT:
- Business Goal: {mission['business_goal']}
- Target Audience: {mission['target_audience']}
- Brand Voice: {mission['brand_voice']}
- Service Offerings: {json.dumps(mission['service_offerings'])}

Generate 30 content ideas (one per day) with the following structure for each:
- Day number (1-30)
- Content type (blog_post, social_media, video_script, infographic, email_newsletter)
- Title/Topic
- Brief description (1-2 sentences)
- Target platform (LinkedIn, Twitter, Blog, Facebook, etc.)
- Key message/value proposition

Format as JSON array with each content item as an object.
Ensure variety in content types and topics while maintaining brand consistency."""

            response = await llm_service.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=3000,
                temperature=0.8  # Higher creativity for content ideas
            )

            if response.error:
                return {"error": f"LLM generation failed: {response.error}"}

            try:
                # Parse the JSON response
                content_calendar = json.loads(response.content)
                if not isinstance(content_calendar, list):
                    return {"error": "Invalid content calendar format"}

                # Create content items in database
                created_items = []
                for i, content_item in enumerate(content_calendar[:30]):  # Limit to 30 items
                    # Calculate scheduled date (starting tomorrow)
                    scheduled_date = (datetime.now() + timedelta(days=i+1)).isoformat()

                    content_data = {
                        "mission_id": mission_id,
                        "title": content_item.get("title", f"Content Day {i+1}"),
                        "content_type": content_item.get("content_type", "blog_post"),
                        "topic": content_item.get("description", ""),
                        "target_audience": mission["target_audience"],
                        "platform": content_item.get("platform", "blog"),
                        "status": "draft",
                        "scheduled_date": scheduled_date
                    }

                    content_id = await self.db_manager.create_content(content_data)
                    created_items.append({
                        "id": content_id,
                        "day": i + 1,
                        **content_item,
                        "scheduled_date": scheduled_date
                    })

                self.logger.info(f"📅 Generated 30-day content calendar for mission {mission_id}")

                return {
                    "calendar_items": created_items,
                    "total_items": len(created_items),
                    "mission_id": mission_id,
                    "generated_at": datetime.now().isoformat()
                }

            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse content calendar JSON: {e}")
                return {"error": "Failed to parse content calendar response"}

        except Exception as e:
            self.logger.error(f"Error generating content calendar: {e}")
            return {"error": str(e)}

    async def _create_content(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create content for a specific calendar item"""
        try:
            content_id = input_data.get("content_id")
            if not content_id:
                return {"error": "Content ID is required"}

            # Get content item from database
            content_items = await self.db_manager.get_content_calendar()
            content_item = next((item for item in content_items if item["id"] == content_id), None)

            if not content_item:
                return {"error": f"Content item {content_id} not found"}

            # Get mission data for context
            mission = await self.db_manager.get_mission_by_id(content_item["mission_id"])
            if not mission:
                return {"error": f"Mission {content_item['mission_id']} not found"}

            # Route to specific content creation method
            if content_item["content_type"] == "blog_post":
                result = await self._generate_blog_post({
                    "content_item": content_item,
                    "mission": mission
                })
            elif content_item["content_type"] in ["social_media", "social_post"]:
                result = await self._create_social_media_post({
                    "content_item": content_item,
                    "mission": mission
                })
            else:
                result = await self._generate_generic_content({
                    "content_item": content_item,
                    "mission": mission
                })

            if "error" in result:
                return result

            # Update content item with generated content
            await self.db_manager.connection.execute("""
                UPDATE content SET content_body = ?, meta_description = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (result["content"], result.get("meta_description", ""), content_id))
            await self.db_manager.connection.commit()

            self.logger.info(f"✍️ Generated content for item {content_id}: {content_item['title']}")

            return {
                "content_id": content_id,
                "title": content_item["title"],
                "content": result["content"],
                "meta_description": result.get("meta_description", ""),
                "word_count": len(result["content"].split()),
                "status": "ready_for_approval"
            }

        except Exception as e:
            self.logger.error(f"Error creating content: {e}")
            return {"error": str(e)}

    async def _generate_blog_post(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a full blog post"""
        try:
            content_item = input_data["content_item"]
            mission = input_data["mission"]

            system_prompt = f"""You are a professional content writer creating blog posts that build brand authority.
Write in the following brand voice: {mission['brand_voice']}
Create engaging, valuable content that resonates with the target audience and establishes thought leadership."""

            user_prompt = f"""Write a comprehensive blog post with the following details:

BUSINESS CONTEXT:
- Business Goal: {mission['business_goal']}
- Target Audience: {mission['target_audience']}
- Brand Voice: {mission['brand_voice']}
- Service Offerings: {json.dumps(mission['service_offerings'])}

BLOG POST DETAILS:
- Title: {content_item['title']}
- Topic: {content_item['topic']}
- Platform: {content_item.get('platform', 'blog')}

Write a complete blog post (800-1200 words) that:
1. Has an engaging introduction
2. Provides valuable insights and information
3. Includes actionable advice
4. Maintains the specified brand voice
5. Ends with a compelling call-to-action
6. Is optimized for the target audience

Also provide a meta description (150-160 characters) for SEO."""

            response = await llm_service.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=2500,
                temperature=0.7
            )

            if response.error:
                return {"error": f"LLM generation failed: {response.error}"}

            # Extract meta description if provided
            content_lines = response.content.split('\n')
            meta_description = ""
            content = response.content

            # Look for meta description in the response
            for i, line in enumerate(content_lines):
                if "meta description" in line.lower():
                    if i + 1 < len(content_lines):
                        meta_description = content_lines[i + 1].strip()
                        break

            return {
                "content": content,
                "meta_description": meta_description,
                "content_type": "blog_post"
            }

        except Exception as e:
            self.logger.error(f"Error generating blog post: {e}")
            return {"error": str(e)}

    async def _create_social_media_post(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a social media post"""
        try:
            content_item = input_data["content_item"]
            mission = input_data["mission"]
            platform = content_item.get("platform", "linkedin").lower()

            # Platform-specific character limits and styles
            platform_specs = {
                "twitter": {"limit": 280, "style": "concise and punchy"},
                "linkedin": {"limit": 1300, "style": "professional and insightful"},
                "facebook": {"limit": 500, "style": "engaging and conversational"},
                "instagram": {"limit": 300, "style": "visual and inspiring"}
            }

            spec = platform_specs.get(platform, platform_specs["linkedin"])

            system_prompt = f"""You are a social media content creator writing for {platform.title()}.
Write in the following brand voice: {mission['brand_voice']}
Create {spec['style']} content that engages the target audience and builds brand authority."""

            user_prompt = f"""Create a {platform} post with the following details:

BUSINESS CONTEXT:
- Business Goal: {mission['business_goal']}
- Target Audience: {mission['target_audience']}
- Brand Voice: {mission['brand_voice']}

POST DETAILS:
- Title/Topic: {content_item['title']}
- Description: {content_item['topic']}
- Platform: {platform}
- Character Limit: {spec['limit']}
- Style: {spec['style']}

Create an engaging {platform} post that:
1. Captures attention immediately
2. Provides value to the audience
3. Maintains the brand voice
4. Includes relevant hashtags (if appropriate for platform)
5. Encourages engagement
6. Stays within the character limit

Keep it {spec['style']} and optimized for {platform}."""

            response = await llm_service.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=800,
                temperature=0.8  # Higher creativity for social media
            )

            if response.error:
                return {"error": f"LLM generation failed: {response.error}"}

            return {
                "content": response.content,
                "platform": platform,
                "content_type": "social_media"
            }

        except Exception as e:
            self.logger.error(f"Error creating social media post: {e}")
            return {"error": str(e)}

    async def _generate_generic_content(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate generic content for other content types"""
        try:
            content_item = input_data["content_item"]
            mission = input_data["mission"]
            content_type = content_item["content_type"]

            system_prompt = f"""You are a professional content creator specializing in {content_type}.
Write in the following brand voice: {mission['brand_voice']}
Create valuable, engaging content that builds brand authority and serves the target audience."""

            user_prompt = f"""Create {content_type} content with the following details:

BUSINESS CONTEXT:
- Business Goal: {mission['business_goal']}
- Target Audience: {mission['target_audience']}
- Brand Voice: {mission['brand_voice']}
- Service Offerings: {json.dumps(mission['service_offerings'])}

CONTENT DETAILS:
- Title: {content_item['title']}
- Topic: {content_item['topic']}
- Content Type: {content_type}
- Platform: {content_item.get('platform', 'general')}

Create comprehensive {content_type} content that:
1. Aligns with the business goals
2. Provides value to the target audience
3. Maintains the brand voice
4. Is appropriate for the specified platform
5. Encourages audience engagement

Make it professional, valuable, and on-brand."""

            response = await llm_service.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=2000,
                temperature=0.7
            )

            if response.error:
                return {"error": f"LLM generation failed: {response.error}"}

            return {
                "content": response.content,
                "content_type": content_type
            }

        except Exception as e:
            self.logger.error(f"Error generating generic content: {e}")
            return {"error": str(e)}
