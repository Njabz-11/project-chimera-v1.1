"""
Project Chimera - Sandbox Manager
Manages secure Docker-based sandbox environment for code testing
"""

import os
import json
import time
import tempfile
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path

import docker
from docker.errors import DockerException, ContainerError, ImageNotFound

from utils.logger import ChimeraLogger


class SandboxManager:
    """Manages secure sandbox environment for code execution"""
    
    def __init__(self):
        self.logger = ChimeraLogger.get_logger(__name__)
        self.docker_client = None
        self.sandbox_image = "chimera-sandbox:latest"
        self.default_timeout = 30
        self.max_memory = "128m"
        self.cpu_quota = 50000  # 50% CPU
        
    async def initialize(self) -> bool:
        """Initialize sandbox environment"""
        try:
            # Initialize Docker client
            self.docker_client = docker.from_env()
            
            # Check if sandbox image exists, build if not
            if not await self._check_sandbox_image():
                await self._build_sandbox_image()
            
            self.logger.info("🐳 Sandbox environment initialized successfully")
            return True
            
        except DockerException as e:
            self.logger.error(f"❌ Failed to initialize Docker: {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize sandbox: {e}")
            return False
    
    async def _check_sandbox_image(self) -> bool:
        """Check if sandbox image exists"""
        try:
            self.docker_client.images.get(self.sandbox_image)
            return True
        except ImageNotFound:
            return False
    
    async def _build_sandbox_image(self) -> bool:
        """Build sandbox Docker image"""
        try:
            dockerfile_path = Path("docker/sandbox")
            if not dockerfile_path.exists():
                self.logger.error("Sandbox Dockerfile not found")
                return False
            
            self.logger.info("🔨 Building sandbox Docker image...")
            
            # Build image
            image, logs = self.docker_client.images.build(
                path=str(dockerfile_path),
                tag=self.sandbox_image,
                rm=True,
                forcerm=True
            )
            
            self.logger.info(f"✅ Built sandbox image: {image.id[:12]}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to build sandbox image: {e}")
            return False
    
    async def execute_code(self, code: str, test_case: str = "", 
                          timeout: Optional[int] = None) -> Dict[str, Any]:
        """Execute code in secure sandbox"""
        
        if not self.docker_client:
            return {
                "success": False,
                "safe": False,
                "error": "Sandbox not initialized",
                "output": ""
            }
        
        timeout = timeout or self.default_timeout
        
        try:
            # Create test script
            test_script = self._create_test_script(code, test_case)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(test_script)
                script_path = f.name
            
            try:
                # Run in sandbox container
                result = await self._run_in_container(script_path, timeout)
                return result
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(script_path)
                except OSError:
                    pass
                    
        except Exception as e:
            self.logger.error(f"Sandbox execution failed: {e}")
            return {
                "success": False,
                "safe": False,
                "error": str(e),
                "output": ""
            }
    
    def _create_test_script(self, code: str, test_case: str = "") -> str:
        """Create test script for sandbox execution"""
        
        return f"""
import sys
import json
import traceback
import io
from contextlib import redirect_stdout, redirect_stderr

def run_test():
    try:
        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            # Execute the code
            exec('''
{code}
            ''')
            
            # Execute test case if provided
            if '''{test_case}'''.strip():
                exec('''
{test_case}
                ''')
        
        stdout_output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()
        
        return {{
            "success": True,
            "safe": True,
            "error": None,
            "output": stdout_output,
            "stderr": stderr_output,
            "execution_completed": True
        }}
        
    except SyntaxError as e:
        return {{
            "success": False,
            "safe": True,
            "error": f"Syntax Error: {{str(e)}}",
            "output": "",
            "stderr": "",
            "error_type": "SyntaxError"
        }}
    except Exception as e:
        return {{
            "success": False,
            "safe": True,
            "error": str(e),
            "output": "",
            "stderr": "",
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }}

if __name__ == "__main__":
    try:
        result = run_test()
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({{
            "success": False,
            "safe": False,
            "error": f"Critical execution error: {{str(e)}}",
            "output": "",
            "stderr": "",
            "error_type": "CriticalError"
        }}))
"""
    
    async def _run_in_container(self, script_path: str, timeout: int) -> Dict[str, Any]:
        """Run script in Docker container"""
        
        try:
            # Run container with security restrictions
            container = self.docker_client.containers.run(
                image=self.sandbox_image,
                command=["python", "/test_script.py"],
                volumes={script_path: {'bind': '/test_script.py', 'mode': 'ro'}},
                mem_limit=self.max_memory,
                cpu_quota=self.cpu_quota,
                network_disabled=True,
                remove=True,
                detach=False,
                timeout=timeout,
                user="1000:1000",
                security_opt=["no-new-privileges:true"],
                read_only=True,
                tmpfs={"/tmp": "noexec,nosuid,size=50m"}
            )
            
            # Parse output
            output = container.decode('utf-8').strip()
            
            try:
                result = json.loads(output)
                return result
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "safe": True,
                    "error": "Failed to parse container output",
                    "output": output,
                    "stderr": ""
                }
                
        except ContainerError as e:
            error_output = e.stderr.decode('utf-8') if e.stderr else str(e)
            return {
                "success": False,
                "safe": False,
                "error": f"Container execution error: {error_output}",
                "output": "",
                "stderr": error_output,
                "exit_code": e.exit_status
            }
        except Exception as e:
            return {
                "success": False,
                "safe": False,
                "error": f"Sandbox execution failed: {str(e)}",
                "output": "",
                "stderr": ""
            }
    
    def is_available(self) -> bool:
        """Check if sandbox is available"""
        return self.docker_client is not None
    
    async def cleanup(self):
        """Cleanup sandbox resources"""
        if self.docker_client:
            try:
                # Remove any running containers
                containers = self.docker_client.containers.list(
                    filters={"ancestor": self.sandbox_image}
                )
                for container in containers:
                    container.stop(timeout=5)
                    container.remove()
                
                self.logger.info("🧹 Sandbox cleanup completed")
            except Exception as e:
                self.logger.warning(f"Sandbox cleanup warning: {e}")


# Global sandbox manager instance
sandbox_manager = SandboxManager()
