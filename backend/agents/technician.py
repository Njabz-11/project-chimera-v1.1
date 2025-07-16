"""
Project Chimera - Technician Agent (WRENCH)
Autonomously detects and repairs software errors within the platform
"""

import time
import json
import asyncio
import tempfile
import subprocess
import docker
from typing import Dict, Any, Optional, List
from pathlib import Path

from .base_agent import BaseAgent, AgentJob, AgentResult
from utils.error_handler import DiagnosticReport, ErrorCategory, ErrorSeverity, error_handler
from utils.llm_service import LLMService


class CodeFixAttempt:
    """Represents a code fix attempt by the TechnicianAgent"""

    def __init__(self, attempt_id: str, original_code: str, fixed_code: str,
                 fix_description: str, llm_reasoning: str):
        self.attempt_id = attempt_id
        self.original_code = original_code
        self.fixed_code = fixed_code
        self.fix_description = fix_description
        self.llm_reasoning = llm_reasoning
        self.test_result = None
        self.validation_passed = False
        self.timestamp = time.time()


class TechnicianAgent(BaseAgent):
    """WRENCH - Error detection and auto-repair specialist"""

    def __init__(self, db_manager):
        super().__init__("WRENCH", db_manager)
        self.llm_service = LLMService()
        self.docker_client = None
        self.max_fix_attempts = 3
        self.sandbox_timeout = 30  # seconds
        self.active_repairs = {}  # Track ongoing repair attempts

    async def initialize(self):
        """Initialize the TechnicianAgent"""
        await super().initialize()

        # Initialize Docker client for sandboxed execution
        try:
            self.docker_client = docker.from_env()
            self.logger.info("🔧 Docker client initialized for sandboxed execution")
        except Exception as e:
            self.logger.warning(f"⚠️ Docker not available, sandboxed execution disabled: {e}")
            self.docker_client = None

        self.logger.info("🔧 WRENCH technician agent initialized and ready")

    async def execute(self, job: AgentJob) -> AgentResult:
        """Execute technician-specific jobs"""
        start_time = time.time()

        try:
            job_type = job.job_type

            if job_type == "diagnose_error":
                return await self._handle_diagnose_error(job)
            elif job_type == "auto_repair":
                return await self._handle_auto_repair(job)
            elif job_type == "validate_fix":
                return await self._handle_validate_fix(job)
            elif job_type == "escalate_error":
                return await self._handle_escalate_error(job)
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
            self.logger.error(f"Error in TechnicianAgent: {e}")
            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="error",
                output_data={},
                execution_time_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            )

    async def _handle_diagnose_error(self, job: AgentJob) -> AgentResult:
        """Diagnose an error from a diagnostic report"""
        start_time = time.time()

        try:
            report_id = job.input_data.get("report_id")
            if not report_id:
                raise ValueError("No report_id provided for diagnosis")

            # Load diagnostic report
            report = error_handler.load_report(report_id)
            if not report:
                raise ValueError(f"Diagnostic report {report_id} not found")

            self.logger.info(f"🔍 Diagnosing error report {report_id} from {report.agent_name}")

            # Analyze the error and determine if it's auto-repairable
            diagnosis = await self._analyze_error_repairability(report)

            # Update report with diagnosis
            report.context_data['diagnosis'] = diagnosis
            error_handler._save_report(report)

            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="success",
                output_data={
                    "report_id": report_id,
                    "diagnosis": diagnosis,
                    "auto_repairable": diagnosis.get("auto_repairable", False),
                    "confidence": diagnosis.get("confidence", 0.0)
                },
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

        except Exception as e:
            self.logger.error(f"Failed to diagnose error for job {job.job_id}: {e}")
            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="error",
                output_data={},
                execution_time_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            )

    async def _handle_auto_repair(self, job: AgentJob) -> AgentResult:
        """Attempt automatic repair of a diagnosed error"""
        start_time = time.time()

        try:
            report_id = job.input_data.get("report_id")
            if not report_id:
                raise ValueError("No report_id provided for auto-repair")

            # Load diagnostic report
            report = error_handler.load_report(report_id)
            if not report:
                raise ValueError(f"Diagnostic report {report_id} not found")

            self.logger.info(f"🔧 Attempting auto-repair for report {report_id}")

            # Check if we've already attempted repairs
            if report.retry_count >= self.max_fix_attempts:
                self.logger.warning(f"Max repair attempts reached for {report_id}, escalating")
                return await self._escalate_to_human(report)

            # Generate code fix using LLM
            fix_attempt = await self._generate_code_fix(report)
            if not fix_attempt:
                raise Exception("Failed to generate code fix")

            # Validate fix in sandbox
            validation_result = await self._validate_fix_in_sandbox(fix_attempt, report)
            fix_attempt.test_result = validation_result
            fix_attempt.validation_passed = validation_result.get("success", False)

            # Update report with fix attempt
            report.fix_attempts.append({
                "attempt_id": fix_attempt.attempt_id,
                "timestamp": fix_attempt.timestamp,
                "fix_description": fix_attempt.fix_description,
                "validation_passed": fix_attempt.validation_passed,
                "test_result": fix_attempt.test_result
            })
            report.retry_count += 1

            if fix_attempt.validation_passed:
                # Apply the fix
                apply_result = await self._apply_code_fix(fix_attempt, report)
                if apply_result["success"]:
                    report.resolved = True
                    self.logger.info(f"✅ Successfully repaired error {report_id}")

                    # Update error statistics
                    error_handler.error_stats['resolved_errors'] += 1

                    result_data = {
                        "report_id": report_id,
                        "repair_successful": True,
                        "fix_applied": True,
                        "attempt_count": report.retry_count,
                        "fix_description": fix_attempt.fix_description
                    }
                else:
                    result_data = {
                        "report_id": report_id,
                        "repair_successful": False,
                        "fix_applied": False,
                        "error": apply_result.get("error", "Unknown error applying fix")
                    }
            else:
                self.logger.warning(f"Fix validation failed for {report_id}, will retry")
                result_data = {
                    "report_id": report_id,
                    "repair_successful": False,
                    "fix_applied": False,
                    "validation_failed": True,
                    "attempt_count": report.retry_count
                }

            # Save updated report
            error_handler._save_report(report)

            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="success",
                output_data=result_data,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

        except Exception as e:
            self.logger.error(f"Failed auto-repair for job {job.job_id}: {e}")
            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="error",
                output_data={},
                execution_time_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            )

    async def _handle_validate_fix(self, job: AgentJob) -> AgentResult:
        """Validate a proposed code fix"""
        start_time = time.time()

        try:
            fix_code = job.input_data.get("fix_code")
            original_code = job.input_data.get("original_code")
            test_case = job.input_data.get("test_case", "")

            if not fix_code or not original_code:
                raise ValueError("Missing fix_code or original_code for validation")

            # Create temporary fix attempt for validation
            fix_attempt = CodeFixAttempt(
                attempt_id="validation_" + str(int(time.time())),
                original_code=original_code,
                fixed_code=fix_code,
                fix_description="Manual validation",
                llm_reasoning="Manual fix validation"
            )

            # Validate in sandbox
            validation_result = await self._validate_fix_in_sandbox(fix_attempt, None, test_case)

            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="success",
                output_data={
                    "validation_passed": validation_result.get("success", False),
                    "test_result": validation_result,
                    "fix_safe": validation_result.get("safe", False)
                },
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

        except Exception as e:
            self.logger.error(f"Failed to validate fix for job {job.job_id}: {e}")
            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="error",
                output_data={},
                execution_time_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            )

    async def _handle_escalate_error(self, job: AgentJob) -> AgentResult:
        """Escalate error to human intervention queue"""
        start_time = time.time()

        try:
            report_id = job.input_data.get("report_id")
            reason = job.input_data.get("reason", "Auto-repair failed")

            if not report_id:
                raise ValueError("No report_id provided for escalation")

            # Load and update report
            report = error_handler.load_report(report_id)
            if report:
                report.escalated = True
                report.context_data['escalation_reason'] = reason
                report.context_data['escalation_timestamp'] = time.time()
                error_handler._save_report(report)

                # Update statistics
                error_handler.error_stats['escalated_errors'] += 1

            self.logger.warning(f"🚨 Escalated error {report_id} to human intervention: {reason}")

            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="success",
                output_data={
                    "report_id": report_id,
                    "escalated": True,
                    "reason": reason
                },
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

        except Exception as e:
            self.logger.error(f"Failed to escalate error for job {job.job_id}: {e}")
            return AgentResult(
                job_id=job.job_id,
                agent_name=self.agent_name,
                status="error",
                output_data={},
                execution_time_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            )

    async def _analyze_error_repairability(self, report: DiagnosticReport) -> Dict[str, Any]:
        """Analyze if an error is automatically repairable using LLM"""

        analysis_prompt = f"""
You are an expert software engineer analyzing a system error for automatic repairability.

ERROR DETAILS:
- Type: {report.exception_type}
- Message: {report.exception_message}
- Category: {report.error_category.value}
- Severity: {report.error_severity.value}
- Agent: {report.agent_name}

FAILING CODE:
```python
{report.failing_code_snippet}
```

FULL TRACEBACK:
{report.full_traceback}

CONTEXT:
{json.dumps(report.context_data, indent=2)}

Analyze this error and determine:
1. Is this error automatically repairable? (true/false)
2. Confidence level (0.0 to 1.0)
3. Repair strategy (if repairable)
4. Risk assessment (low/medium/high)
5. Estimated complexity (simple/moderate/complex)

Respond in JSON format:
{{
    "auto_repairable": boolean,
    "confidence": float,
    "repair_strategy": "string description",
    "risk_assessment": "low|medium|high",
    "complexity": "simple|moderate|complex",
    "reasoning": "detailed explanation"
}}
"""

        try:
            response = await self.llm_service.generate_response(
                prompt=analysis_prompt,
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                temperature=0.1
            )

            # Parse JSON response
            response_text = response.content if hasattr(response, 'content') else str(response)
            analysis = json.loads(response_text)

            self.logger.info(f"🔍 Error analysis complete: {analysis.get('auto_repairable', False)} (confidence: {analysis.get('confidence', 0.0)})")

            return analysis

        except Exception as e:
            self.logger.error(f"Failed to analyze error repairability: {e}")
            return {
                "auto_repairable": False,
                "confidence": 0.0,
                "repair_strategy": "Analysis failed",
                "risk_assessment": "high",
                "complexity": "complex",
                "reasoning": f"Analysis failed due to: {str(e)}"
            }

    async def _generate_code_fix(self, report: DiagnosticReport) -> Optional[CodeFixAttempt]:
        """Generate a code fix using specialized coder LLM"""

        # Build context from previous attempts
        previous_attempts = ""
        if report.fix_attempts:
            previous_attempts = "\n\nPREVIOUS FAILED ATTEMPTS:\n"
            for attempt in report.fix_attempts[-2:]:  # Last 2 attempts
                previous_attempts += f"- {attempt['fix_description']}: {attempt.get('test_result', {}).get('error', 'Unknown error')}\n"

        fix_prompt = f"""
You are an expert software engineer. The following Python code failed with an error.
Analyze the code and the error, and provide a corrected version.

ERROR DETAILS:
- Type: {report.exception_type}
- Message: {report.exception_message}
- Function: {report.failing_function}
- File: {report.failing_file}
- Line: {report.failing_line_number}

FAILING CODE:
```python
{report.failing_code_snippet}
```

FULL TRACEBACK:
{report.full_traceback}

ORIGINAL GOAL: {report.original_goal}

CONTEXT DATA:
{json.dumps(report.context_data, indent=2)}
{previous_attempts}

INSTRUCTIONS:
1. Identify the root cause of the error
2. Provide a corrected version of the code
3. Ensure the fix is minimal and focused
4. Add proper error handling if missing
5. Maintain the original functionality

Respond in JSON format:
{{
    "root_cause": "detailed explanation of what caused the error",
    "fix_description": "brief description of the fix",
    "fixed_code": "the corrected code snippet",
    "reasoning": "detailed explanation of why this fix works",
    "risk_level": "low|medium|high",
    "additional_notes": "any important considerations"
}}

Output ONLY the JSON response.
"""

        try:
            response = await self.llm_service.generate_response(
                prompt=fix_prompt,
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                temperature=0.1
            )

            # Parse JSON response
            response_text = response.content if hasattr(response, 'content') else str(response)
            fix_data = json.loads(response_text)

            # Create fix attempt
            attempt_id = f"fix_{report.report_id}_{len(report.fix_attempts) + 1}"
            fix_attempt = CodeFixAttempt(
                attempt_id=attempt_id,
                original_code=report.failing_code_snippet,
                fixed_code=fix_data["fixed_code"],
                fix_description=fix_data["fix_description"],
                llm_reasoning=fix_data["reasoning"]
            )

            self.logger.info(f"🔧 Generated code fix: {fix_data['fix_description']}")

            return fix_attempt

        except Exception as e:
            self.logger.error(f"Failed to generate code fix: {e}")
            return None

    async def _validate_fix_in_sandbox(self, fix_attempt: CodeFixAttempt,
                                     report: Optional[DiagnosticReport],
                                     custom_test: str = "") -> Dict[str, Any]:
        """Validate code fix in secure sandbox environment"""

        if not self.docker_client:
            self.logger.warning("Docker not available, skipping sandbox validation")
            return {
                "success": False,
                "safe": False,
                "error": "Sandbox environment not available",
                "validation_method": "none"
            }

        try:
            # Create test script
            test_script = self._create_test_script(fix_attempt, report, custom_test)

            # Run in Docker container
            result = await self._run_in_docker_sandbox(test_script)

            self.logger.info(f"🧪 Sandbox validation result: {result.get('success', False)}")

            return result

        except Exception as e:
            self.logger.error(f"Sandbox validation failed: {e}")
            return {
                "success": False,
                "safe": False,
                "error": str(e),
                "validation_method": "docker"
            }

    def _create_test_script(self, fix_attempt: CodeFixAttempt,
                           report: Optional[DiagnosticReport],
                           custom_test: str = "") -> str:
        """Create test script for sandbox validation"""

        test_script = f"""
import sys
import traceback
import json
import tempfile
import os

def test_fix():
    try:
        # Original failing code (commented out)
        '''
        ORIGINAL CODE:
        {fix_attempt.original_code}
        '''

        # Fixed code to test
        {fix_attempt.fixed_code}

        # Custom test if provided
        {custom_test}

        return {{
            "success": True,
            "safe": True,
            "error": None,
            "output": "Fix validation passed"
        }}

    except Exception as e:
        return {{
            "success": False,
            "safe": True,  # Code ran but failed
            "error": str(e),
            "traceback": traceback.format_exc()
        }}

if __name__ == "__main__":
    try:
        result = test_fix()
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({{
            "success": False,
            "safe": False,  # Code couldn't even run safely
            "error": f"Critical error: {{str(e)}}",
            "traceback": traceback.format_exc()
        }}))
"""
        return test_script

    async def _run_in_docker_sandbox(self, test_script: str) -> Dict[str, Any]:
        """Run test script in Docker sandbox"""

        try:
            # Create temporary file for test script
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(test_script)
                script_path = f.name

            # Run in Docker container with restrictions
            container = self.docker_client.containers.run(
                image="python:3.11-slim",
                command=f"python /test_script.py",
                volumes={script_path: {'bind': '/test_script.py', 'mode': 'ro'}},
                mem_limit="128m",
                cpu_quota=50000,  # 50% CPU
                network_disabled=True,
                remove=True,
                detach=False,
                timeout=self.sandbox_timeout
            )

            # Parse output
            output = container.decode('utf-8').strip()
            result = json.loads(output)

            # Clean up
            os.unlink(script_path)

            return result

        except docker.errors.ContainerError as e:
            return {
                "success": False,
                "safe": False,
                "error": f"Container error: {e.stderr.decode('utf-8') if e.stderr else str(e)}",
                "validation_method": "docker"
            }
        except Exception as e:
            return {
                "success": False,
                "safe": False,
                "error": f"Sandbox execution failed: {str(e)}",
                "validation_method": "docker"
            }

    async def _apply_code_fix(self, fix_attempt: CodeFixAttempt,
                            report: DiagnosticReport) -> Dict[str, Any]:
        """Apply validated code fix to the actual file"""

        try:
            # For safety, we'll create a backup and apply the fix
            file_path = Path(report.failing_file)

            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"Source file not found: {report.failing_file}"
                }

            # Create backup
            backup_path = file_path.with_suffix(f"{file_path.suffix}.backup_{int(time.time())}")
            backup_path.write_text(file_path.read_text(encoding='utf-8'), encoding='utf-8')

            # Read current file content
            current_content = file_path.read_text(encoding='utf-8')

            # Apply the fix (simple replacement for now)
            # In a more sophisticated implementation, we'd use AST manipulation
            fixed_content = current_content.replace(
                fix_attempt.original_code.strip(),
                fix_attempt.fixed_code.strip()
            )

            # Write fixed content
            file_path.write_text(fixed_content, encoding='utf-8')

            self.logger.info(f"✅ Applied code fix to {report.failing_file} (backup: {backup_path})")

            return {
                "success": True,
                "backup_path": str(backup_path),
                "applied_fix": fix_attempt.fix_description
            }

        except Exception as e:
            self.logger.error(f"Failed to apply code fix: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _escalate_to_human(self, report: DiagnosticReport) -> AgentResult:
        """Escalate error to human intervention after max attempts"""

        report.escalated = True
        report.context_data['escalation_reason'] = f"Max repair attempts ({self.max_fix_attempts}) exceeded"
        report.context_data['escalation_timestamp'] = time.time()

        # Save updated report
        error_handler._save_report(report)

        # Update statistics
        error_handler.error_stats['escalated_errors'] += 1

        self.logger.warning(f"🚨 Escalated error {report.report_id} to human intervention after {self.max_fix_attempts} attempts")

        return AgentResult(
            job_id="escalation",
            agent_name=self.agent_name,
            status="success",
            output_data={
                "report_id": report.report_id,
                "escalated": True,
                "reason": "Max repair attempts exceeded",
                "attempts_made": len(report.fix_attempts)
            },
            execution_time_ms=0
        )

    def get_repair_statistics(self) -> Dict[str, Any]:
        """Get technician repair statistics"""
        return {
            "active_repairs": len(self.active_repairs),
            "max_fix_attempts": self.max_fix_attempts,
            "sandbox_enabled": self.docker_client is not None,
            "sandbox_timeout": self.sandbox_timeout,
            **error_handler.get_error_stats()
        }
