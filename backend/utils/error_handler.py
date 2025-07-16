"""
Project Chimera - Enhanced Error Handling Infrastructure
Provides diagnostic reporting and error classification for the Resilience Engine
"""

import traceback
import inspect
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Type
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

from utils.logger import ChimeraLogger


class ErrorSeverity(Enum):
    """Error severity levels for classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for routing to appropriate handlers"""
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    DATABASE_ERROR = "database_error"
    BROWSER_ERROR = "browser_error"
    LLM_ERROR = "llm_error"
    EMAIL_ERROR = "email_error"
    MEMORY_ERROR = "memory_error"
    VALIDATION_ERROR = "validation_error"
    SYSTEM_ERROR = "system_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class DiagnosticReport:
    """Comprehensive diagnostic report for system errors"""
    report_id: str
    timestamp: datetime
    agent_name: str
    job_id: Optional[str]
    error_category: ErrorCategory
    error_severity: ErrorSeverity
    exception_type: str
    exception_message: str
    full_traceback: str
    failing_code_snippet: str
    failing_function: str
    failing_file: str
    failing_line_number: int
    context_data: Dict[str, Any]
    original_goal: str
    retry_count: int = 0
    fix_attempts: List[Dict[str, Any]] = None
    escalated: bool = False
    resolved: bool = False
    
    def __post_init__(self):
        if self.fix_attempts is None:
            self.fix_attempts = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['error_category'] = self.error_category.value
        data['error_severity'] = self.error_severity.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DiagnosticReport':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['error_category'] = ErrorCategory(data['error_category'])
        data['error_severity'] = ErrorSeverity(data['error_severity'])
        return cls(**data)


class ErrorClassifier:
    """Classifies errors into categories and severity levels"""
    
    def __init__(self):
        self.logger = ChimeraLogger.get_logger(__name__)
        
        # Error classification rules
        self.classification_rules = {
            # API Errors
            'openai': (ErrorCategory.LLM_ERROR, ErrorSeverity.HIGH),
            'anthropic': (ErrorCategory.LLM_ERROR, ErrorSeverity.HIGH),
            'HttpError': (ErrorCategory.API_ERROR, ErrorSeverity.MEDIUM),
            'APIError': (ErrorCategory.API_ERROR, ErrorSeverity.MEDIUM),
            'RateLimitError': (ErrorCategory.API_ERROR, ErrorSeverity.LOW),
            'AuthenticationError': (ErrorCategory.API_ERROR, ErrorSeverity.HIGH),
            
            # Network Errors
            'ConnectionError': (ErrorCategory.NETWORK_ERROR, ErrorSeverity.MEDIUM),
            'TimeoutError': (ErrorCategory.NETWORK_ERROR, ErrorSeverity.MEDIUM),
            'httpx.TimeoutException': (ErrorCategory.NETWORK_ERROR, ErrorSeverity.MEDIUM),
            
            # Database Errors
            'sqlite3': (ErrorCategory.DATABASE_ERROR, ErrorSeverity.HIGH),
            'aiosqlite': (ErrorCategory.DATABASE_ERROR, ErrorSeverity.HIGH),
            
            # Browser Errors
            'playwright': (ErrorCategory.BROWSER_ERROR, ErrorSeverity.MEDIUM),
            'TargetClosedError': (ErrorCategory.BROWSER_ERROR, ErrorSeverity.MEDIUM),
            
            # Email Errors
            'gmail': (ErrorCategory.EMAIL_ERROR, ErrorSeverity.MEDIUM),
            'google.auth': (ErrorCategory.EMAIL_ERROR, ErrorSeverity.HIGH),
            
            # Memory/Vector DB Errors
            'chromadb': (ErrorCategory.MEMORY_ERROR, ErrorSeverity.MEDIUM),
            
            # Validation Errors
            'ValidationError': (ErrorCategory.VALIDATION_ERROR, ErrorSeverity.LOW),
            'ValueError': (ErrorCategory.VALIDATION_ERROR, ErrorSeverity.LOW),
            'KeyError': (ErrorCategory.VALIDATION_ERROR, ErrorSeverity.LOW),
            
            # System Errors
            'MemoryError': (ErrorCategory.SYSTEM_ERROR, ErrorSeverity.CRITICAL),
            'OSError': (ErrorCategory.SYSTEM_ERROR, ErrorSeverity.HIGH),
            'PermissionError': (ErrorCategory.SYSTEM_ERROR, ErrorSeverity.HIGH),
        }
    
    def classify_error(self, exception: Exception, traceback_str: str) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify error based on exception type and traceback"""
        exception_name = type(exception).__name__
        exception_str = str(exception).lower()
        traceback_lower = traceback_str.lower()
        
        # Check exception type first
        for pattern, (category, severity) in self.classification_rules.items():
            if pattern.lower() in exception_name.lower():
                return category, severity
        
        # Check exception message and traceback
        for pattern, (category, severity) in self.classification_rules.items():
            if pattern.lower() in exception_str or pattern.lower() in traceback_lower:
                return category, severity
        
        # Default classification
        return ErrorCategory.UNKNOWN_ERROR, ErrorSeverity.MEDIUM


class ChimeraErrorHandler:
    """Enhanced error handler with diagnostic reporting capabilities"""
    
    def __init__(self, db_manager=None):
        self.logger = ChimeraLogger.get_logger(__name__)
        self.db_manager = db_manager
        self.classifier = ErrorClassifier()
        self.reports_dir = Path("data/diagnostic_reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Error handling statistics
        self.error_stats = {
            'total_errors': 0,
            'resolved_errors': 0,
            'escalated_errors': 0,
            'by_category': {},
            'by_severity': {}
        }
    
    def create_diagnostic_report(
        self,
        exception: Exception,
        agent_name: str,
        job_id: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
        original_goal: str = ""
    ) -> DiagnosticReport:
        """Create comprehensive diagnostic report from exception"""
        
        # Generate unique report ID
        report_id = str(uuid.uuid4())
        
        # Get traceback information
        tb = traceback.format_exc()
        
        # Extract code context from traceback
        failing_code, failing_function, failing_file, failing_line = self._extract_code_context(exception)
        
        # Classify error
        category, severity = self.classifier.classify_error(exception, tb)
        
        # Create diagnostic report
        report = DiagnosticReport(
            report_id=report_id,
            timestamp=datetime.now(),
            agent_name=agent_name,
            job_id=job_id,
            error_category=category,
            error_severity=severity,
            exception_type=type(exception).__name__,
            exception_message=str(exception),
            full_traceback=tb,
            failing_code_snippet=failing_code,
            failing_function=failing_function,
            failing_file=failing_file,
            failing_line_number=failing_line,
            context_data=context_data or {},
            original_goal=original_goal
        )
        
        # Save report to disk
        self._save_report(report)
        
        # Update statistics
        self._update_stats(category, severity)
        
        self.logger.error(f"🚨 Created diagnostic report {report_id} for {agent_name}: {exception}")
        
        return report
    
    def _extract_code_context(self, exception: Exception) -> tuple[str, str, str, int]:
        """Extract code context from exception traceback"""
        try:
            tb = exception.__traceback__
            if tb is None:
                return "", "", "", 0
            
            # Get the last frame (where error occurred)
            while tb.tb_next:
                tb = tb.tb_next
            
            frame = tb.tb_frame
            filename = frame.f_code.co_filename
            function_name = frame.f_code.co_name
            line_number = tb.tb_lineno
            
            # Try to read the source code
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Get context around the failing line (5 lines before and after)
                start_line = max(0, line_number - 6)
                end_line = min(len(lines), line_number + 5)
                
                code_snippet = ''.join(lines[start_line:end_line])
                
            except (FileNotFoundError, IOError):
                code_snippet = f"# Could not read source file: {filename}"
            
            return code_snippet, function_name, filename, line_number
            
        except Exception as e:
            self.logger.warning(f"Failed to extract code context: {e}")
            return "", "", "", 0
    
    def _save_report(self, report: DiagnosticReport):
        """Save diagnostic report to disk"""
        try:
            report_file = self.reports_dir / f"{report.report_id}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report.to_dict(), f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save diagnostic report: {e}")
    
    def _update_stats(self, category: ErrorCategory, severity: ErrorSeverity):
        """Update error statistics"""
        self.error_stats['total_errors'] += 1
        
        # Update by category
        cat_key = category.value
        if cat_key not in self.error_stats['by_category']:
            self.error_stats['by_category'][cat_key] = 0
        self.error_stats['by_category'][cat_key] += 1
        
        # Update by severity
        sev_key = severity.value
        if sev_key not in self.error_stats['by_severity']:
            self.error_stats['by_severity'][sev_key] = 0
        self.error_stats['by_severity'][sev_key] += 1
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get current error statistics"""
        return self.error_stats.copy()
    
    def load_report(self, report_id: str) -> Optional[DiagnosticReport]:
        """Load diagnostic report from disk"""
        try:
            report_file = self.reports_dir / f"{report_id}.json"
            if report_file.exists():
                with open(report_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return DiagnosticReport.from_dict(data)
        except Exception as e:
            self.logger.error(f"Failed to load diagnostic report {report_id}: {e}")
        return None
    
    def list_reports(self, category: Optional[ErrorCategory] = None, 
                    unresolved_only: bool = False) -> List[str]:
        """List diagnostic report IDs with optional filtering"""
        try:
            report_ids = []
            for report_file in self.reports_dir.glob("*.json"):
                if unresolved_only or category:
                    # Load report to check filters
                    report = self.load_report(report_file.stem)
                    if report:
                        if category and report.error_category != category:
                            continue
                        if unresolved_only and report.resolved:
                            continue
                
                report_ids.append(report_file.stem)
            
            return sorted(report_ids, reverse=True)  # Most recent first
            
        except Exception as e:
            self.logger.error(f"Failed to list diagnostic reports: {e}")
            return []


# Global error handler instance
error_handler = ChimeraErrorHandler()


def handle_agent_error(agent_name: str, job_id: Optional[str] = None, 
                      context_data: Optional[Dict[str, Any]] = None,
                      original_goal: str = ""):
    """Decorator for handling agent errors with diagnostic reporting"""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Create diagnostic report
                report = error_handler.create_diagnostic_report(
                    exception=e,
                    agent_name=agent_name,
                    job_id=job_id,
                    context_data=context_data,
                    original_goal=original_goal
                )
                
                # Submit to TechnicianAgent for auto-repair
                from agents.orchestrator import OrchestratorAgent
                # This will be implemented when TechnicianAgent is ready
                
                # Re-raise the exception for now
                raise
        return wrapper
    return decorator
