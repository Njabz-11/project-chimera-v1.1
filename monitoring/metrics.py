"""
Metrics collection system for Project Chimera Enterprise
"""
import time
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from functools import wraps
from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry, generate_latest
from prometheus_client.multiprocess import MultiProcessCollector
from utils.logger import ChimeraLogger

logger = ChimeraLogger.get_logger(__name__)


class ChimeraMetrics:
    """Centralized metrics collection for Project Chimera"""

    def __init__(self):
        self.registry = CollectorRegistry()
        
        # Application metrics
        self.http_requests_total = Counter(
            'chimera_http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code', 'tenant_id'],
            registry=self.registry
        )
        
        self.http_request_duration = Histogram(
            'chimera_http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint', 'tenant_id'],
            registry=self.registry
        )
        
        self.active_connections = Gauge(
            'chimera_active_connections',
            'Number of active WebSocket connections',
            ['tenant_id'],
            registry=self.registry
        )
        
        # Agent metrics
        self.agent_executions_total = Counter(
            'chimera_agent_executions_total',
            'Total agent executions',
            ['agent_name', 'status', 'tenant_id'],
            registry=self.registry
        )
        
        self.agent_execution_duration = Histogram(
            'chimera_agent_execution_duration_seconds',
            'Agent execution duration in seconds',
            ['agent_name', 'tenant_id'],
            registry=self.registry
        )
        
        self.active_agents = Gauge(
            'chimera_active_agents',
            'Number of currently active agents',
            ['agent_name', 'tenant_id'],
            registry=self.registry
        )
        
        # Business metrics
        self.leads_generated_total = Counter(
            'chimera_leads_generated_total',
            'Total leads generated',
            ['source', 'tenant_id'],
            registry=self.registry
        )
        
        self.emails_sent_total = Counter(
            'chimera_emails_sent_total',
            'Total emails sent',
            ['type', 'status', 'tenant_id'],
            registry=self.registry
        )
        
        self.conversations_total = Counter(
            'chimera_conversations_total',
            'Total conversations',
            ['status', 'tenant_id'],
            registry=self.registry
        )
        
        self.missions_total = Counter(
            'chimera_missions_total',
            'Total missions created',
            ['status', 'tenant_id'],
            registry=self.registry
        )
        
        # Database metrics
        self.db_connections_active = Gauge(
            'chimera_db_connections_active',
            'Active database connections',
            registry=self.registry
        )
        
        self.db_query_duration = Histogram(
            'chimera_db_query_duration_seconds',
            'Database query duration in seconds',
            ['operation', 'table'],
            registry=self.registry
        )
        
        self.db_queries_total = Counter(
            'chimera_db_queries_total',
            'Total database queries',
            ['operation', 'table', 'status'],
            registry=self.registry
        )
        
        # System metrics
        self.memory_usage_bytes = Gauge(
            'chimera_memory_usage_bytes',
            'Memory usage in bytes',
            ['component'],
            registry=self.registry
        )
        
        self.cpu_usage_percent = Gauge(
            'chimera_cpu_usage_percent',
            'CPU usage percentage',
            ['component'],
            registry=self.registry
        )
        
        # Error metrics
        self.errors_total = Counter(
            'chimera_errors_total',
            'Total errors',
            ['component', 'error_type', 'tenant_id'],
            registry=self.registry
        )
        
        # Tenant metrics
        self.tenant_usage = Gauge(
            'chimera_tenant_usage',
            'Tenant resource usage',
            ['tenant_id', 'resource_type'],
            registry=self.registry
        )
        
        self.tenant_limits = Gauge(
            'chimera_tenant_limits',
            'Tenant resource limits',
            ['tenant_id', 'resource_type'],
            registry=self.registry
        )
        
        # Application info
        self.app_info = Info(
            'chimera_app_info',
            'Application information',
            registry=self.registry
        )

    def record_http_request(self, method: str, endpoint: str, status_code: int, 
                          duration: float, tenant_id: Optional[str] = None):
        """Record HTTP request metrics"""
        tenant_id = tenant_id or "unknown"
        
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            tenant_id=tenant_id
        ).inc()
        
        self.http_request_duration.labels(
            method=method,
            endpoint=endpoint,
            tenant_id=tenant_id
        ).observe(duration)

    def record_agent_execution(self, agent_name: str, status: str, 
                             duration: float, tenant_id: Optional[str] = None):
        """Record agent execution metrics"""
        tenant_id = tenant_id or "unknown"
        
        self.agent_executions_total.labels(
            agent_name=agent_name,
            status=status,
            tenant_id=tenant_id
        ).inc()
        
        self.agent_execution_duration.labels(
            agent_name=agent_name,
            tenant_id=tenant_id
        ).observe(duration)

    def record_lead_generated(self, source: str, tenant_id: Optional[str] = None):
        """Record lead generation"""
        tenant_id = tenant_id or "unknown"
        
        self.leads_generated_total.labels(
            source=source,
            tenant_id=tenant_id
        ).inc()

    def record_email_sent(self, email_type: str, status: str, tenant_id: Optional[str] = None):
        """Record email sent"""
        tenant_id = tenant_id or "unknown"
        
        self.emails_sent_total.labels(
            type=email_type,
            status=status,
            tenant_id=tenant_id
        ).inc()

    def record_conversation(self, status: str, tenant_id: Optional[str] = None):
        """Record conversation"""
        tenant_id = tenant_id or "unknown"
        
        self.conversations_total.labels(
            status=status,
            tenant_id=tenant_id
        ).inc()

    def record_mission(self, status: str, tenant_id: Optional[str] = None):
        """Record mission"""
        tenant_id = tenant_id or "unknown"
        
        self.missions_total.labels(
            status=status,
            tenant_id=tenant_id
        ).inc()

    def record_db_query(self, operation: str, table: str, duration: float, status: str = "success"):
        """Record database query metrics"""
        self.db_queries_total.labels(
            operation=operation,
            table=table,
            status=status
        ).inc()
        
        self.db_query_duration.labels(
            operation=operation,
            table=table
        ).observe(duration)

    def record_error(self, component: str, error_type: str, tenant_id: Optional[str] = None):
        """Record error"""
        tenant_id = tenant_id or "unknown"
        
        self.errors_total.labels(
            component=component,
            error_type=error_type,
            tenant_id=tenant_id
        ).inc()

    def update_tenant_usage(self, tenant_id: str, resource_type: str, value: float):
        """Update tenant usage metrics"""
        self.tenant_usage.labels(
            tenant_id=tenant_id,
            resource_type=resource_type
        ).set(value)

    def update_tenant_limits(self, tenant_id: str, resource_type: str, value: float):
        """Update tenant limits metrics"""
        self.tenant_limits.labels(
            tenant_id=tenant_id,
            resource_type=resource_type
        ).set(value)

    def set_active_connections(self, count: int, tenant_id: Optional[str] = None):
        """Set active connections count"""
        tenant_id = tenant_id or "unknown"
        
        self.active_connections.labels(tenant_id=tenant_id).set(count)

    def set_active_agents(self, agent_name: str, count: int, tenant_id: Optional[str] = None):
        """Set active agents count"""
        tenant_id = tenant_id or "unknown"
        
        self.active_agents.labels(
            agent_name=agent_name,
            tenant_id=tenant_id
        ).set(count)

    def set_app_info(self, version: str, environment: str, build_date: str):
        """Set application information"""
        self.app_info.info({
            'version': version,
            'environment': environment,
            'build_date': build_date
        })

    def get_metrics(self) -> str:
        """Get all metrics in Prometheus format"""
        return generate_latest(self.registry).decode('utf-8')


# Global metrics instance
metrics = ChimeraMetrics()


def track_time(metric_name: str, labels: Optional[Dict[str, str]] = None):
    """Decorator to track execution time"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Record success metric
                if metric_name == "agent_execution":
                    metrics.record_agent_execution(
                        agent_name=labels.get("agent_name", "unknown"),
                        status="success",
                        duration=duration,
                        tenant_id=labels.get("tenant_id")
                    )
                elif metric_name == "db_query":
                    metrics.record_db_query(
                        operation=labels.get("operation", "unknown"),
                        table=labels.get("table", "unknown"),
                        duration=duration,
                        status="success"
                    )
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                # Record error metric
                if metric_name == "agent_execution":
                    metrics.record_agent_execution(
                        agent_name=labels.get("agent_name", "unknown"),
                        status="error",
                        duration=duration,
                        tenant_id=labels.get("tenant_id")
                    )
                elif metric_name == "db_query":
                    metrics.record_db_query(
                        operation=labels.get("operation", "unknown"),
                        table=labels.get("table", "unknown"),
                        duration=duration,
                        status="error"
                    )
                
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Record success metric (simplified for sync functions)
                return result
            except Exception as e:
                duration = time.time() - start_time
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator
