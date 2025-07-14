"""
Project Chimera - Error Classification and Routing System
Routes different error types to appropriate handlers and recovery strategies
"""

import asyncio
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum

from utils.error_handler import DiagnosticReport, ErrorCategory, ErrorSeverity, error_handler
from utils.logger import ChimeraLogger


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types"""
    AUTO_REPAIR = "auto_repair"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    ESCALATE_IMMEDIATE = "escalate_immediate"
    IGNORE_AND_CONTINUE = "ignore_and_continue"
    RESTART_COMPONENT = "restart_component"
    FALLBACK_MODE = "fallback_mode"


@dataclass
class ErrorRoute:
    """Defines how to handle a specific error type"""
    category: ErrorCategory
    severity: ErrorSeverity
    strategy: RecoveryStrategy
    max_retries: int = 3
    retry_delay: float = 1.0
    escalation_threshold: int = 5
    handler_function: Optional[str] = None
    requires_human: bool = False


class ErrorRouter:
    """Routes errors to appropriate handlers based on classification"""
    
    def __init__(self):
        self.logger = ChimeraLogger.get_logger(__name__)
        self.routes: Dict[str, ErrorRoute] = {}
        self.error_counts: Dict[str, int] = {}
        self.recovery_handlers: Dict[str, Callable] = {}
        
        # Initialize default routing rules
        self._setup_default_routes()
    
    def _setup_default_routes(self):
        """Setup default error routing rules"""
        
        # LLM Errors - Usually auto-repairable
        self.add_route(ErrorRoute(
            category=ErrorCategory.LLM_ERROR,
            severity=ErrorSeverity.HIGH,
            strategy=RecoveryStrategy.AUTO_REPAIR,
            max_retries=2,
            escalation_threshold=3
        ))
        
        self.add_route(ErrorRoute(
            category=ErrorCategory.LLM_ERROR,
            severity=ErrorSeverity.MEDIUM,
            strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
            max_retries=3,
            retry_delay=2.0
        ))
        
        # API Errors - Retry with backoff
        self.add_route(ErrorRoute(
            category=ErrorCategory.API_ERROR,
            severity=ErrorSeverity.MEDIUM,
            strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
            max_retries=3,
            retry_delay=5.0
        ))
        
        self.add_route(ErrorRoute(
            category=ErrorCategory.API_ERROR,
            severity=ErrorSeverity.HIGH,
            strategy=RecoveryStrategy.ESCALATE_IMMEDIATE,
            requires_human=True
        ))
        
        # Network Errors - Retry with exponential backoff
        self.add_route(ErrorRoute(
            category=ErrorCategory.NETWORK_ERROR,
            severity=ErrorSeverity.MEDIUM,
            strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
            max_retries=5,
            retry_delay=1.0
        ))
        
        # Database Errors - Critical, escalate immediately
        self.add_route(ErrorRoute(
            category=ErrorCategory.DATABASE_ERROR,
            severity=ErrorSeverity.HIGH,
            strategy=RecoveryStrategy.ESCALATE_IMMEDIATE,
            requires_human=True
        ))
        
        # Browser Errors - Auto-repair or restart
        self.add_route(ErrorRoute(
            category=ErrorCategory.BROWSER_ERROR,
            severity=ErrorSeverity.MEDIUM,
            strategy=RecoveryStrategy.AUTO_REPAIR,
            max_retries=2
        ))
        
        self.add_route(ErrorRoute(
            category=ErrorCategory.BROWSER_ERROR,
            severity=ErrorSeverity.HIGH,
            strategy=RecoveryStrategy.RESTART_COMPONENT,
            max_retries=1
        ))
        
        # Email Errors - Retry or escalate
        self.add_route(ErrorRoute(
            category=ErrorCategory.EMAIL_ERROR,
            severity=ErrorSeverity.MEDIUM,
            strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
            max_retries=3,
            retry_delay=10.0
        ))
        
        # Memory/Vector DB Errors - Auto-repair
        self.add_route(ErrorRoute(
            category=ErrorCategory.MEMORY_ERROR,
            severity=ErrorSeverity.MEDIUM,
            strategy=RecoveryStrategy.AUTO_REPAIR,
            max_retries=2
        ))
        
        # Validation Errors - Usually auto-repairable
        self.add_route(ErrorRoute(
            category=ErrorCategory.VALIDATION_ERROR,
            severity=ErrorSeverity.LOW,
            strategy=RecoveryStrategy.AUTO_REPAIR,
            max_retries=1
        ))
        
        # System Errors - Critical, immediate escalation
        self.add_route(ErrorRoute(
            category=ErrorCategory.SYSTEM_ERROR,
            severity=ErrorSeverity.CRITICAL,
            strategy=RecoveryStrategy.ESCALATE_IMMEDIATE,
            requires_human=True
        ))
        
        # Unknown Errors - Conservative approach
        self.add_route(ErrorRoute(
            category=ErrorCategory.UNKNOWN_ERROR,
            severity=ErrorSeverity.MEDIUM,
            strategy=RecoveryStrategy.AUTO_REPAIR,
            max_retries=1,
            escalation_threshold=1
        ))
    
    def add_route(self, route: ErrorRoute):
        """Add or update an error route"""
        key = f"{route.category.value}_{route.severity.value}"
        self.routes[key] = route
        self.logger.debug(f"Added error route: {key} -> {route.strategy.value}")
    
    def get_route(self, category: ErrorCategory, severity: ErrorSeverity) -> Optional[ErrorRoute]:
        """Get error route for category and severity"""
        key = f"{category.value}_{severity.value}"
        return self.routes.get(key)
    
    async def route_error(self, report: DiagnosticReport) -> Dict[str, Any]:
        """Route error to appropriate handler"""
        
        # Get routing rule
        route = self.get_route(report.error_category, report.error_severity)
        if not route:
            self.logger.warning(f"No route found for {report.error_category.value}_{report.error_severity.value}")
            route = self._get_default_route()
        
        # Track error frequency
        error_key = f"{report.agent_name}_{report.error_category.value}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Check if we should escalate due to frequency
        if self.error_counts[error_key] >= route.escalation_threshold:
            self.logger.warning(f"Error frequency threshold reached for {error_key}, escalating")
            route = ErrorRoute(
                category=report.error_category,
                severity=ErrorSeverity.HIGH,
                strategy=RecoveryStrategy.ESCALATE_IMMEDIATE,
                requires_human=True
            )
        
        # Execute recovery strategy
        recovery_result = await self._execute_recovery_strategy(report, route)
        
        return {
            "report_id": report.report_id,
            "route_strategy": route.strategy.value,
            "recovery_result": recovery_result,
            "error_frequency": self.error_counts[error_key],
            "escalated": recovery_result.get("escalated", False)
        }
    
    async def _execute_recovery_strategy(self, report: DiagnosticReport, 
                                       route: ErrorRoute) -> Dict[str, Any]:
        """Execute the recovery strategy for an error"""
        
        strategy = route.strategy
        
        try:
            if strategy == RecoveryStrategy.AUTO_REPAIR:
                return await self._handle_auto_repair(report, route)
            
            elif strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
                return await self._handle_retry_with_backoff(report, route)
            
            elif strategy == RecoveryStrategy.ESCALATE_IMMEDIATE:
                return await self._handle_escalate_immediate(report, route)
            
            elif strategy == RecoveryStrategy.IGNORE_AND_CONTINUE:
                return await self._handle_ignore_and_continue(report, route)
            
            elif strategy == RecoveryStrategy.RESTART_COMPONENT:
                return await self._handle_restart_component(report, route)
            
            elif strategy == RecoveryStrategy.FALLBACK_MODE:
                return await self._handle_fallback_mode(report, route)
            
            else:
                self.logger.error(f"Unknown recovery strategy: {strategy}")
                return {"success": False, "error": f"Unknown strategy: {strategy}"}
                
        except Exception as e:
            self.logger.error(f"Recovery strategy execution failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_auto_repair(self, report: DiagnosticReport, 
                                route: ErrorRoute) -> Dict[str, Any]:
        """Handle auto-repair strategy"""
        
        # Submit to TechnicianAgent for auto-repair
        from agents.orchestrator import OrchestratorAgent
        
        # This would be implemented to submit a job to the TechnicianAgent
        self.logger.info(f"🔧 Submitting {report.report_id} for auto-repair")
        
        return {
            "success": True,
            "strategy": "auto_repair",
            "submitted_for_repair": True,
            "report_id": report.report_id
        }
    
    async def _handle_retry_with_backoff(self, report: DiagnosticReport, 
                                       route: ErrorRoute) -> Dict[str, Any]:
        """Handle retry with backoff strategy"""
        
        self.logger.info(f"🔄 Scheduling retry for {report.report_id} with {route.retry_delay}s delay")
        
        # Schedule retry (this would integrate with the job queue system)
        return {
            "success": True,
            "strategy": "retry_with_backoff",
            "retry_delay": route.retry_delay,
            "max_retries": route.max_retries,
            "report_id": report.report_id
        }
    
    async def _handle_escalate_immediate(self, report: DiagnosticReport, 
                                       route: ErrorRoute) -> Dict[str, Any]:
        """Handle immediate escalation strategy"""
        
        report.escalated = True
        report.context_data['escalation_reason'] = "Immediate escalation due to error severity/frequency"
        error_handler._save_report(report)
        
        self.logger.warning(f"🚨 Immediately escalated {report.report_id} to human intervention")
        
        return {
            "success": True,
            "strategy": "escalate_immediate",
            "escalated": True,
            "requires_human": route.requires_human,
            "report_id": report.report_id
        }
    
    async def _handle_ignore_and_continue(self, report: DiagnosticReport, 
                                        route: ErrorRoute) -> Dict[str, Any]:
        """Handle ignore and continue strategy"""
        
        self.logger.info(f"⏭️ Ignoring error {report.report_id} and continuing")
        
        return {
            "success": True,
            "strategy": "ignore_and_continue",
            "ignored": True,
            "report_id": report.report_id
        }
    
    async def _handle_restart_component(self, report: DiagnosticReport, 
                                      route: ErrorRoute) -> Dict[str, Any]:
        """Handle component restart strategy"""
        
        self.logger.info(f"🔄 Scheduling component restart for {report.agent_name}")
        
        # This would integrate with the agent management system
        return {
            "success": True,
            "strategy": "restart_component",
            "component": report.agent_name,
            "report_id": report.report_id
        }
    
    async def _handle_fallback_mode(self, report: DiagnosticReport, 
                                  route: ErrorRoute) -> Dict[str, Any]:
        """Handle fallback mode strategy"""
        
        self.logger.info(f"🛡️ Activating fallback mode for {report.agent_name}")
        
        return {
            "success": True,
            "strategy": "fallback_mode",
            "fallback_activated": True,
            "report_id": report.report_id
        }
    
    def _get_default_route(self) -> ErrorRoute:
        """Get default route for unknown error types"""
        return ErrorRoute(
            category=ErrorCategory.UNKNOWN_ERROR,
            severity=ErrorSeverity.MEDIUM,
            strategy=RecoveryStrategy.AUTO_REPAIR,
            max_retries=1,
            escalation_threshold=1
        )
    
    def get_routing_statistics(self) -> Dict[str, Any]:
        """Get error routing statistics"""
        return {
            "total_routes": len(self.routes),
            "error_counts": self.error_counts.copy(),
            "most_frequent_errors": sorted(
                self.error_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
        }


# Global error router instance
error_router = ErrorRouter()
