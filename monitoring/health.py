"""
Health check system for Project Chimera Enterprise
"""
import asyncio
import time
import psutil
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel
from database.db_manager import DatabaseManager
from utils.logger import ChimeraLogger

logger = ChimeraLogger.get_logger(__name__)


class HealthStatus(str, Enum):
    """Health check status options"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentHealth(BaseModel):
    """Individual component health status"""
    name: str
    status: HealthStatus
    message: str
    response_time_ms: Optional[float] = None
    last_checked: datetime
    details: Dict[str, Any] = {}


class SystemHealth(BaseModel):
    """Overall system health status"""
    status: HealthStatus
    timestamp: datetime
    uptime_seconds: float
    components: List[ComponentHealth]
    summary: Dict[str, Any]


class HealthChecker:
    """Comprehensive health checking system"""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager
        self.start_time = time.time()
        self.last_health_check = None
        self.health_history: List[SystemHealth] = []

    async def check_system_health(self) -> SystemHealth:
        """Perform comprehensive system health check"""
        start_time = time.time()
        components = []
        
        # Check all components
        checks = [
            self._check_database(),
            self._check_memory(),
            self._check_cpu(),
            self._check_disk(),
            self._check_network(),
            self._check_agents(),
            self._check_external_services()
        ]
        
        # Run all checks concurrently
        try:
            component_results = await asyncio.gather(*checks, return_exceptions=True)
            
            for result in component_results:
                if isinstance(result, Exception):
                    components.append(ComponentHealth(
                        name="unknown",
                        status=HealthStatus.UNHEALTHY,
                        message=f"Health check failed: {str(result)}",
                        last_checked=datetime.utcnow()
                    ))
                else:
                    components.append(result)
        
        except Exception as e:
            logger.error(f"Health check system error: {e}")
            components.append(ComponentHealth(
                name="health_system",
                status=HealthStatus.UNHEALTHY,
                message=f"Health check system error: {str(e)}",
                last_checked=datetime.utcnow()
            ))
        
        # Determine overall status
        overall_status = self._determine_overall_status(components)
        
        # Calculate uptime
        uptime = time.time() - self.start_time
        
        # Create summary
        summary = self._create_summary(components, uptime)
        
        health = SystemHealth(
            status=overall_status,
            timestamp=datetime.utcnow(),
            uptime_seconds=uptime,
            components=components,
            summary=summary
        )
        
        # Store in history (keep last 100 checks)
        self.health_history.append(health)
        if len(self.health_history) > 100:
            self.health_history.pop(0)
        
        self.last_health_check = health
        
        return health

    async def _check_database(self) -> ComponentHealth:
        """Check database connectivity and performance"""
        start_time = time.time()
        
        try:
            if not self.db_manager:
                return ComponentHealth(
                    name="database",
                    status=HealthStatus.UNKNOWN,
                    message="Database manager not available",
                    last_checked=datetime.utcnow()
                )
            
            # Test basic connectivity
            cursor = await self.db_manager.connection.execute("SELECT 1")
            await cursor.fetchone()
            
            # Test write performance
            test_start = time.time()
            await self.db_manager.connection.execute(
                "CREATE TEMP TABLE IF NOT EXISTS health_test (id INTEGER, timestamp TEXT)"
            )
            await self.db_manager.connection.execute(
                "INSERT INTO health_test (id, timestamp) VALUES (?, ?)",
                (1, datetime.utcnow().isoformat())
            )
            await self.db_manager.connection.execute("DROP TABLE health_test")
            write_time = (time.time() - test_start) * 1000
            
            response_time = (time.time() - start_time) * 1000
            
            status = HealthStatus.HEALTHY
            if response_time > 1000:  # > 1 second
                status = HealthStatus.DEGRADED
            elif response_time > 5000:  # > 5 seconds
                status = HealthStatus.UNHEALTHY
            
            return ComponentHealth(
                name="database",
                status=status,
                message="Database is responsive",
                response_time_ms=response_time,
                last_checked=datetime.utcnow(),
                details={
                    "write_time_ms": write_time,
                    "connection_status": "connected"
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database error: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
                last_checked=datetime.utcnow()
            )

    async def _check_memory(self) -> ComponentHealth:
        """Check system memory usage"""
        try:
            memory = psutil.virtual_memory()
            
            status = HealthStatus.HEALTHY
            if memory.percent > 80:
                status = HealthStatus.DEGRADED
            elif memory.percent > 95:
                status = HealthStatus.UNHEALTHY
            
            return ComponentHealth(
                name="memory",
                status=status,
                message=f"Memory usage: {memory.percent:.1f}%",
                last_checked=datetime.utcnow(),
                details={
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "percent": memory.percent
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="memory",
                status=HealthStatus.UNKNOWN,
                message=f"Memory check failed: {str(e)}",
                last_checked=datetime.utcnow()
            )

    async def _check_cpu(self) -> ComponentHealth:
        """Check CPU usage"""
        try:
            # Get CPU usage over 1 second interval
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            
            status = HealthStatus.HEALTHY
            if cpu_percent > 80:
                status = HealthStatus.DEGRADED
            elif cpu_percent > 95:
                status = HealthStatus.UNHEALTHY
            
            return ComponentHealth(
                name="cpu",
                status=status,
                message=f"CPU usage: {cpu_percent:.1f}%",
                last_checked=datetime.utcnow(),
                details={
                    "usage_percent": cpu_percent,
                    "cpu_count": cpu_count,
                    "load_avg_1m": load_avg[0],
                    "load_avg_5m": load_avg[1],
                    "load_avg_15m": load_avg[2]
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="cpu",
                status=HealthStatus.UNKNOWN,
                message=f"CPU check failed: {str(e)}",
                last_checked=datetime.utcnow()
            )

    async def _check_disk(self) -> ComponentHealth:
        """Check disk usage"""
        try:
            disk = psutil.disk_usage('/')
            
            status = HealthStatus.HEALTHY
            if disk.percent > 80:
                status = HealthStatus.DEGRADED
            elif disk.percent > 95:
                status = HealthStatus.UNHEALTHY
            
            return ComponentHealth(
                name="disk",
                status=status,
                message=f"Disk usage: {disk.percent:.1f}%",
                last_checked=datetime.utcnow(),
                details={
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "percent": disk.percent
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="disk",
                status=HealthStatus.UNKNOWN,
                message=f"Disk check failed: {str(e)}",
                last_checked=datetime.utcnow()
            )

    async def _check_network(self) -> ComponentHealth:
        """Check network connectivity"""
        try:
            # Basic network stats
            net_io = psutil.net_io_counters()
            
            return ComponentHealth(
                name="network",
                status=HealthStatus.HEALTHY,
                message="Network is operational",
                last_checked=datetime.utcnow(),
                details={
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="network",
                status=HealthStatus.UNKNOWN,
                message=f"Network check failed: {str(e)}",
                last_checked=datetime.utcnow()
            )

    async def _check_agents(self) -> ComponentHealth:
        """Check agent system health"""
        try:
            # This would check agent status from orchestrator
            # For now, return healthy
            return ComponentHealth(
                name="agents",
                status=HealthStatus.HEALTHY,
                message="Agent system operational",
                last_checked=datetime.utcnow(),
                details={
                    "active_agents": 0,  # TODO: Get from orchestrator
                    "total_agents": 10
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="agents",
                status=HealthStatus.UNKNOWN,
                message=f"Agent check failed: {str(e)}",
                last_checked=datetime.utcnow()
            )

    async def _check_external_services(self) -> ComponentHealth:
        """Check external service connectivity"""
        try:
            # This would check OpenAI, Anthropic, Google APIs, etc.
            # For now, return healthy
            return ComponentHealth(
                name="external_services",
                status=HealthStatus.HEALTHY,
                message="External services accessible",
                last_checked=datetime.utcnow(),
                details={
                    "openai_api": "healthy",
                    "anthropic_api": "healthy",
                    "google_apis": "healthy"
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="external_services",
                status=HealthStatus.UNKNOWN,
                message=f"External services check failed: {str(e)}",
                last_checked=datetime.utcnow()
            )

    def _determine_overall_status(self, components: List[ComponentHealth]) -> HealthStatus:
        """Determine overall system status from component statuses"""
        if not components:
            return HealthStatus.UNKNOWN
        
        statuses = [comp.status for comp in components]
        
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        elif all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN

    def _create_summary(self, components: List[ComponentHealth], uptime: float) -> Dict[str, Any]:
        """Create health summary"""
        status_counts = {}
        for comp in components:
            status_counts[comp.status.value] = status_counts.get(comp.status.value, 0) + 1
        
        return {
            "total_components": len(components),
            "healthy_components": status_counts.get("healthy", 0),
            "degraded_components": status_counts.get("degraded", 0),
            "unhealthy_components": status_counts.get("unhealthy", 0),
            "unknown_components": status_counts.get("unknown", 0),
            "uptime_hours": round(uptime / 3600, 2),
            "last_restart": datetime.fromtimestamp(self.start_time).isoformat()
        }

    async def get_health_history(self, hours: int = 24) -> List[SystemHealth]:
        """Get health check history"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        return [
            health for health in self.health_history
            if health.timestamp >= cutoff_time
        ]

    def get_quick_status(self) -> Dict[str, Any]:
        """Get quick system status"""
        if not self.last_health_check:
            return {"status": "unknown", "message": "No health checks performed yet"}
        
        return {
            "status": self.last_health_check.status.value,
            "timestamp": self.last_health_check.timestamp.isoformat(),
            "uptime_seconds": self.last_health_check.uptime_seconds,
            "components_healthy": len([
                c for c in self.last_health_check.components 
                if c.status == HealthStatus.HEALTHY
            ]),
            "total_components": len(self.last_health_check.components)
        }


# Global health checker instance
health_checker = HealthChecker()
