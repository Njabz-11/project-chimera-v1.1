"""
Project Chimera - Guardian Agent (AEGIS)
Acts as the final ethical and safety checkpoint for all external communications
"""

import re
import time
from typing import Dict, Any, List
from datetime import datetime

from .base_agent import BaseAgent, AgentJob, AgentResult
from utils.llm_service import LLMService

class GuardianAgent(BaseAgent):
    """AEGIS - Ethical and safety checkpoint specialist"""

    def __init__(self, db_manager):
        super().__init__("AEGIS", db_manager)
        self.llm_service = LLMService()

        # Safety rules for content validation
        self.safety_rules = [
            "No insults, offensive language, or personal attacks",
            "No financial guarantees or unrealistic promises",
            "No spammy language or excessive promotional content",
            "No misleading claims about products or services",
            "No requests for sensitive personal information",
            "No inappropriate or unprofessional tone",
            "Must maintain professional business communication standards",
            "Must respect privacy and data protection principles"
        ]

        # Prohibited patterns (regex)
        self.prohibited_patterns = [
            r'\b(guaranteed|100%|promise)\s+(profit|money|income|return)',
            r'\b(get\s+rich\s+quick|make\s+money\s+fast)',
            r'\b(scam|fraud|cheat|trick)',
            r'\b(urgent|act\s+now|limited\s+time|expires\s+soon)',
            r'\b(free\s+money|no\s+risk|risk\s+free)',
            r'[A-Z]{5,}',  # Excessive caps
            r'!{3,}',      # Multiple exclamation marks
        ]

    async def execute(self, job: AgentJob) -> AgentResult:
        """Execute guardian-specific jobs"""
        start_time = time.time()
        job_type = job.job_type

        try:
            if job_type == "validate_message":
                return await self._validate_message(job)
            elif job_type == "validate_content":
                return await self._validate_content(job)
            elif job_type == "safety_check":
                return await self._safety_check(job)
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
            self.logger.error(f"Guardian validation failed: {e}")
            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="error",
                output_data={"error": str(e)},
                execution_time_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            )

    async def _validate_message(self, job: AgentJob) -> AgentResult:
        """Validate an outgoing message for safety and ethics"""
        message_text = job.input_data.get("message_text", "")
        message_type = job.input_data.get("message_type", "email")

        if not message_text:
            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="error",
                output_data={"validation_result": "FAIL", "reason": "Empty message"},
                execution_time_ms=0,
                error_message="No message text provided"
            )

        # Run validation checks
        validation_result = await self._run_validation_checks(message_text, message_type)

        # Log validation result
        await self.db_manager.log_agent_activity(
            agent_name=self.agent_name,
            activity_type="message_validation",
            description=f"Validated {message_type} message",
            status="success" if validation_result["passed"] else "warning",
            input_data={"message_length": len(message_text), "message_type": message_type},
            output_data=validation_result
        )

        return AgentResult(
            job_id=job.job_id,
            agent_name=self.agent_name,
            status="success",
            output_data={
                "validation_result": "PASS" if validation_result["passed"] else "FAIL",
                "safety_score": validation_result["safety_score"],
                "issues_found": validation_result["issues"],
                "recommendations": validation_result["recommendations"]
            },
            execution_time_ms=validation_result["execution_time_ms"]
        )

    async def _validate_content(self, job: AgentJob) -> AgentResult:
        """Validate content (social media posts, articles, etc.)"""
        content_text = job.input_data.get("content_text", "")
        content_type = job.input_data.get("content_type", "article")

        validation_result = await self._run_validation_checks(content_text, content_type)

        return AgentResult(
            job_id=job.job_id,
            agent_name=self.agent_name,
            status="success",
            output_data={
                "validation_result": "PASS" if validation_result["passed"] else "FAIL",
                "safety_score": validation_result["safety_score"],
                "issues_found": validation_result["issues"],
                "recommendations": validation_result["recommendations"]
            },
            execution_time_ms=validation_result["execution_time_ms"]
        )

    async def _safety_check(self, job: AgentJob) -> AgentResult:
        """Perform comprehensive safety check on any text"""
        text = job.input_data.get("text", "")
        context = job.input_data.get("context", "general")

        validation_result = await self._run_validation_checks(text, context)

        return AgentResult(
            job_id=job.job_id,
            agent_name=self.agent_name,
            status="success",
            output_data={
                "safety_passed": validation_result["passed"],
                "safety_score": validation_result["safety_score"],
                "issues_found": validation_result["issues"],
                "risk_level": validation_result.get("risk_level", "low")
            },
            execution_time_ms=validation_result["execution_time_ms"]
        )

    async def _run_validation_checks(self, text: str, context: str) -> Dict[str, Any]:
        """Run comprehensive validation checks on text"""
        start_time = time.time()
        issues = []
        recommendations = []
        safety_score = 100  # Start with perfect score

        # 1. Pattern-based checks
        pattern_issues = self._check_prohibited_patterns(text)
        issues.extend(pattern_issues)
        safety_score -= len(pattern_issues) * 10

        # 2. Rule-based checks
        rule_issues = self._check_safety_rules(text)
        issues.extend(rule_issues)
        safety_score -= len(rule_issues) * 15

        # 3. LLM-based ethical review
        try:
            llm_result = await self._llm_ethical_review(text, context)
            if not llm_result.get("ethical", True):
                issues.append(f"Ethical concern: {llm_result.get('reason', 'Unknown')}")
                safety_score -= 20
                recommendations.extend(llm_result.get("recommendations", []))
        except Exception as e:
            self.logger.warning(f"LLM ethical review failed: {e}")

        # 4. Professional tone check
        tone_issues = self._check_professional_tone(text)
        issues.extend(tone_issues)
        safety_score -= len(tone_issues) * 5

        # Ensure safety score doesn't go below 0
        safety_score = max(0, safety_score)

        # Determine if validation passed (score >= 70)
        passed = safety_score >= 70 and len(issues) == 0

        # Generate recommendations if issues found
        if issues and not recommendations:
            recommendations = self._generate_recommendations(issues)

        return {
            "passed": passed,
            "safety_score": safety_score,
            "issues": issues,
            "recommendations": recommendations,
            "risk_level": "high" if safety_score < 50 else "medium" if safety_score < 70 else "low",
            "execution_time_ms": int((time.time() - start_time) * 1000)
        }

    def _check_prohibited_patterns(self, text: str) -> List[str]:
        """Check for prohibited patterns using regex"""
        issues = []

        for pattern in self.prohibited_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append(f"Prohibited pattern detected: {pattern}")

        return issues

    def _check_safety_rules(self, text: str) -> List[str]:
        """Check against safety rules"""
        issues = []
        text_lower = text.lower()

        # Check for financial guarantees
        if any(word in text_lower for word in ["guarantee", "guaranteed", "100%", "promise"]):
            if any(word in text_lower for word in ["profit", "money", "income", "return"]):
                issues.append("Contains financial guarantees or unrealistic promises")

        # Check for spam indicators
        spam_indicators = ["act now", "limited time", "urgent", "expires soon", "free money"]
        if any(indicator in text_lower for indicator in spam_indicators):
            issues.append("Contains spammy language")

        # Check for excessive caps
        caps_ratio = sum(1 for c in text if c.isupper()) / len(text) if text else 0
        if caps_ratio > 0.3:
            issues.append("Excessive use of capital letters")

        return issues

    def _check_professional_tone(self, text: str) -> List[str]:
        """Check for professional tone"""
        issues = []

        # Check for excessive punctuation
        if "!!!" in text or "???" in text:
            issues.append("Excessive punctuation usage")

        # Check for informal language
        informal_words = ["gonna", "wanna", "gotta", "yeah", "nah", "omg", "lol"]
        if any(word in text.lower() for word in informal_words):
            issues.append("Contains informal language")

        return issues

    async def _llm_ethical_review(self, text: str, context: str) -> Dict[str, Any]:
        """Use LLM for ethical review of content"""
        prompt = f"""
        Please review the following {context} message for ethical concerns and professional appropriateness:

        MESSAGE:
        {text}

        EVALUATION CRITERIA:
        - Professional business communication standards
        - No misleading claims or false promises
        - Respectful and appropriate tone
        - No spam-like characteristics
        - Ethical business practices

        Please respond with a JSON object containing:
        - "ethical": boolean (true if ethical, false if concerns)
        - "reason": string (explanation if not ethical)
        - "recommendations": array of strings (suggestions for improvement)
        - "professional_score": number 1-10 (professionalism rating)
        """

        try:
            response = await self.llm_service.generate_response(
                prompt=prompt,
                model="claude-3-haiku-20240307",
                max_tokens=500,
                temperature=0.1
            )

            # Parse JSON response
            import json
            result = json.loads(response)
            return result

        except Exception as e:
            self.logger.warning(f"LLM ethical review parsing failed: {e}")
            return {
                "ethical": True,
                "reason": "Review unavailable",
                "recommendations": [],
                "professional_score": 7
            }

    def _generate_recommendations(self, issues: List[str]) -> List[str]:
        """Generate recommendations based on issues found"""
        recommendations = []

        for issue in issues:
            if "financial guarantee" in issue.lower():
                recommendations.append("Remove financial guarantees and focus on value proposition")
            elif "spammy language" in issue.lower():
                recommendations.append("Use more professional, consultative language")
            elif "excessive caps" in issue.lower():
                recommendations.append("Use normal capitalization for better readability")
            elif "excessive punctuation" in issue.lower():
                recommendations.append("Use standard punctuation for professional communication")
            elif "informal language" in issue.lower():
                recommendations.append("Replace informal words with professional alternatives")
            else:
                recommendations.append("Review content for professional business standards")

        return recommendations
