"""Enhanced telemetry implementation for DevOps Agent."""

import functools
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from . import config as agent_config

logger = logging.getLogger(__name__)

# Initialize observability components conditionally
OBSERVABILITY_ENABLED = agent_config.should_enable_observability()

if OBSERVABILITY_ENABLED:
    # OpenTelemetry imports for custom instrumentation
    from opentelemetry import metrics, trace
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.metrics import CallbackOptions, Observation
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.trace import Status, StatusCode
else:
    # Create no-op imports when observability is disabled
    class NoOpTrace:
        def get_tracer(self, name):
            return NoOpTracer()
    
    class NoOpMetrics:
        def get_meter(self, name):
            return NoOpMeter()
        def set_meter_provider(self, provider):
            pass
    
    class NoOpTracer:
        def start_span(self, name, **kwargs):
            return NoOpSpan()
        def start_as_current_span(self, name, **kwargs):
            return NoOpSpan()
    
    class NoOpMeter:
        def create_counter(self, name="noop", **kwargs):
            return NoOpCounter()
        def create_histogram(self, name="noop", **kwargs):
            return NoOpHistogram()
        def create_up_down_counter(self, name="noop", **kwargs):
            return NoOpCounter()
        def create_observable_gauge(self, name="noop", **kwargs):
            return NoOpGauge()
    
    class NoOpSpan:
        def set_attribute(self, key, value):
            pass
        def set_status(self, status):
            pass
        def record_exception(self, exception):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
    
    class NoOpCounter:
        def add(self, amount, attributes=None):
            pass
    
    class NoOpHistogram:
        def record(self, amount, attributes=None):
            pass
    
    class NoOpGauge:
        pass
    
    class NoOpCallbackOptions:
        pass
    
    class NoOpObservation:
        def __init__(self, *args, **kwargs):
            pass
    
    # Create no-op instances
    trace = NoOpTrace()
    metrics = NoOpMetrics()
    
    class NoOpStatus:
        def __init__(self, *args, **kwargs):
            pass
    
    Status = NoOpStatus
    
    class NoOpStatusCode:
        ERROR = 'ERROR'
        OK = 'OK'
    
    StatusCode = NoOpStatusCode
    CallbackOptions = NoOpCallbackOptions
    Observation = NoOpObservation

class OperationType(Enum):
    """Types of agent operations to track."""
    TOOL_EXECUTION = "tool_execution"
    LLM_REQUEST = "llm_request"
    CONTEXT_MANAGEMENT = "context_management"
    PLANNING = "planning"
    FILE_OPERATION = "file_operation"
    SHELL_COMMAND = "shell_command"
    MEMORY_OPERATION = "memory_operation"
    RAG_OPERATION = "rag_operation"


@dataclass
class MetricSnapshot:
    """Snapshot of performance metrics."""
    timestamp: float
    memory_usage_mb: float
    token_usage: int
    operation_count: int
    error_count: int
    average_response_time: float


class DevOpsAgentTelemetry:
    """Enhanced telemetry for DevOps Agent operations."""
    
    def __init__(self):
        self.enabled = OBSERVABILITY_ENABLED
        
        if self.enabled:
            # Configure OpenTelemetry for Grafana Cloud export
            self._configure_grafana_cloud_export()
            
            # OpenTelemetry setup
            self.tracer = trace.get_tracer("devops_agent")
            self.meter = metrics.get_meter("devops_agent")
            
            # Initialize custom metrics
            self._setup_custom_metrics()
        else:
            logger.info("🚫 Telemetry disabled - using no-op telemetry")
            self.tracer = trace.get_tracer("devops_agent")
            self.meter = metrics.get_meter("devops_agent")
            
            # Initialize no-op metric attributes
            self.operation_counter = self.meter.create_counter(name="noop_operation_counter")
            self.error_counter = self.meter.create_counter(name="noop_error_counter")
            self.token_counter = self.meter.create_counter(name="noop_token_counter")
            self.tool_usage_counter = self.meter.create_counter(name="noop_tool_usage_counter")
            self.context_operations_counter = self.meter.create_counter(name="noop_context_operations_counter")
            self.operation_duration = self.meter.create_histogram(name="noop_operation_duration")
            self.llm_response_time = self.meter.create_histogram(name="noop_llm_response_time")
            self.context_size = self.meter.create_histogram(name="noop_context_size")
            self.tool_execution_time = self.meter.create_histogram(name="noop_tool_execution_time")
            self.file_operation_size = self.meter.create_histogram(name="noop_file_operation_size")
            self.active_tools = self.meter.create_up_down_counter(name="noop_active_tools")
            self.context_cache_size = self.meter.create_up_down_counter(name="noop_context_cache_size")
        
        # Performance tracking (always available for basic functionality)
        self.operation_metrics: Dict[str, List[float]] = {}
        self.error_counts: Dict[str, int] = {}
        self.token_usage_history: List[int] = []
        self.memory_snapshots: List[MetricSnapshot] = []
    
    def _configure_grafana_cloud_export(self):
        """Configure OpenTelemetry to export to Grafana Cloud if credentials are available."""
        if not self.enabled:
            return
            
        # Check if telemetry export is disabled
        if agent_config.DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT:
            logger.info("🚫 Telemetry export disabled via DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT")
            return
            
        # Check for Grafana Cloud configuration
        grafana_otlp_endpoint = agent_config.GRAFANA_OTLP_ENDPOINT
        grafana_otlp_token = agent_config.GRAFANA_OTLP_TOKEN
        
        if grafana_otlp_endpoint and grafana_otlp_token:
            logger.info("Configuring Grafana Cloud OTLP export...")
            
            # Get export interval from environment or use default
            export_interval_seconds = agent_config.GRAFANA_EXPORT_INTERVAL_SECONDS
            export_timeout_seconds = agent_config.GRAFANA_EXPORT_TIMEOUT_SECONDS
            
            # Configure OTLP metric exporter for Grafana Cloud
            otlp_exporter = OTLPMetricExporter(
                endpoint=grafana_otlp_endpoint,
                headers={
                    "Authorization": f"Basic {grafana_otlp_token}"
                },
                timeout=export_timeout_seconds
            )
            
            # Set up metric reader with OTLP exporter
            metric_reader = PeriodicExportingMetricReader(
                exporter=otlp_exporter,
                export_interval_millis=export_interval_seconds * 1000,  # Convert to milliseconds
                export_timeout_millis=export_timeout_seconds * 1000     # Convert to milliseconds
            )
            
            # Configure the global metric provider
            metrics.set_meter_provider(
                MeterProvider(metric_readers=[metric_reader])
            )
            
            logger.info(f"✅ Grafana Cloud OTLP export configured successfully")
            logger.info(f"📊 Export interval: {export_interval_seconds}s, Timeout: {export_timeout_seconds}s")
        else:
            logger.info("🔍 Grafana Cloud credentials not found - using local metrics only")
            logger.info("💡 Set GRAFANA_OTLP_ENDPOINT and GRAFANA_OTLP_TOKEN for Grafana Cloud export")
        
    def _setup_custom_metrics(self):
        """Setup custom OpenTelemetry metrics."""
        if not self.enabled:
            return
        
        # Counter metrics
        self.operation_counter = self.meter.create_counter(
            name="devops_agent_operations_total",
            description="Total number of operations by type",
            unit="1"
        )
        
        self.error_counter = self.meter.create_counter(
            name="devops_agent_errors_total", 
            description="Total number of errors by type",
            unit="1"
        )
        
        self.token_counter = self.meter.create_counter(
            name="devops_agent_tokens_total",
            description="Total tokens consumed",
            unit="1"
        )
        
        # New: Tool usage counter
        self.tool_usage_counter = self.meter.create_counter(
            name="devops_agent_tool_usage_total",
            description="Total tool executions by tool type",
            unit="1"
        )
        
        # New: Context operations counter
        self.context_operations_counter = self.meter.create_counter(
            name="devops_agent_context_operations_total",
            description="Total context management operations",
            unit="1"
        )
        
        # Histogram metrics
        self.operation_duration = self.meter.create_histogram(
            name="devops_agent_operation_duration_seconds",
            description="Duration of agent operations",
            unit="s"
        )
        
        self.llm_response_time = self.meter.create_histogram(
            name="devops_agent_llm_response_time_seconds", 
            description="LLM response time",
            unit="s"
        )
        
        self.context_size = self.meter.create_histogram(
            name="devops_agent_context_size_tokens",
            description="Size of context in tokens",
            unit="tokens"
        )
        
        # New: Tool execution time
        self.tool_execution_time = self.meter.create_histogram(
            name="devops_agent_tool_execution_seconds",
            description="Time taken for tool executions",
            unit="s"
        )
        
        # New: File operation size
        self.file_operation_size = self.meter.create_histogram(
            name="devops_agent_file_operation_bytes",
            description="Size of file operations in bytes",
            unit="bytes"
        )
        
        # Gauge metrics
        self.active_tools = self.meter.create_up_down_counter(
            name="devops_agent_active_tools",
            description="Number of currently active tools",
            unit="1"
        )
        
        # New: Context cache size
        self.context_cache_size = self.meter.create_up_down_counter(
            name="devops_agent_context_cache_items",
            description="Number of items in context cache",
            unit="1"
        )
        
        # Observable metrics for system resources - only create if enabled
        if self.enabled:
            self.meter.create_observable_gauge(
                name="devops_agent_memory_usage_mb",
                callbacks=[self._get_memory_usage],
                description="Current memory usage in MB"
            )
            
            self.meter.create_observable_gauge(
                name="devops_agent_avg_response_time",
                callbacks=[self._get_avg_response_time],
                description="Average response time over last N operations"
            )
            
            # New: CPU usage gauge
            self.meter.create_observable_gauge(
                name="devops_agent_cpu_usage_percent",
                callbacks=[self._get_cpu_usage],
                description="Current CPU usage percentage"
            )
            
            # New: Disk usage gauge
            self.meter.create_observable_gauge(
                name="devops_agent_disk_usage_mb",
                callbacks=[self._get_disk_usage],
                description="Current disk usage in MB"
            )
        
    def _get_memory_usage(self, options):
        """Callback for memory usage metric."""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            if self.enabled:
                yield Observation(memory_mb, {"component": "devops_agent"})
            else:
                yield NoOpObservation(memory_mb, {"component": "devops_agent"})
        except ImportError:
            # Fallback if psutil not available
            if self.enabled:
                yield Observation(0, {"component": "devops_agent", "status": "unavailable"})
            else:
                yield NoOpObservation(0, {"component": "devops_agent", "status": "unavailable"})
    
    def _get_avg_response_time(self, options):
        """Callback for average response time metric."""
        if self.operation_metrics:
            all_times = []
            for times in self.operation_metrics.values():
                all_times.extend(times[-10:])  # Last 10 operations per type
            
            if all_times:
                avg_time = sum(all_times) / len(all_times)
                if self.enabled:
                    yield Observation(avg_time, {"metric": "avg_response_time"})
                else:
                    yield NoOpObservation(avg_time, {"metric": "avg_response_time"})
    
    def _get_cpu_usage(self, options):
        """Callback for CPU usage metric."""
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=None)
            if self.enabled:
                yield Observation(cpu_percent, {"component": "devops_agent"})
            else:
                yield NoOpObservation(cpu_percent, {"component": "devops_agent"})
        except ImportError:
            # Fallback if psutil not available
            if self.enabled:
                yield Observation(0, {"component": "devops_agent", "status": "unavailable"})
            else:
                yield NoOpObservation(0, {"component": "devops_agent", "status": "unavailable"})
    
    def _get_disk_usage(self, options):
        """Callback for disk usage metric."""
        try:
            import os

            import psutil

            # Get disk usage for current working directory
            disk_usage = psutil.disk_usage(os.getcwd())
            used_mb = disk_usage.used / 1024 / 1024
            if self.enabled:
                yield Observation(used_mb, {"component": "devops_agent", "path": os.getcwd()})
            else:
                yield NoOpObservation(used_mb, {"component": "devops_agent", "path": os.getcwd()})
        except ImportError:
            # Fallback if psutil not available
            if self.enabled:
                yield Observation(0, {"component": "devops_agent", "status": "unavailable"})
            else:
                yield NoOpObservation(0, {"component": "devops_agent", "status": "unavailable"})
    
    def track_operation(self, operation_type: OperationType, operation_name: str = ""):
        """Decorator to track operation performance and errors."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                operation_key = f"{operation_type.value}_{operation_name or func.__name__}"
                
                # Start OpenTelemetry span
                with self.tracer.start_as_current_span(operation_key) as span:
                    span.set_attribute("operation.type", operation_type.value)
                    span.set_attribute("operation.name", operation_name or func.__name__)
                    span.set_attribute("function.name", func.__name__)
                    
                    # Track active operation
                    self.active_tools.add(1, {"operation": operation_type.value})
                    
                    try:
                        # Execute the operation
                        result = func(*args, **kwargs)
                        
                        # Track success
                        duration = time.time() - start_time
                        self._record_success(operation_key, duration, span)
                        
                        return result
                        
                    except Exception as e:
                        # Track error
                        duration = time.time() - start_time
                        self._record_error(operation_key, duration, span, e)
                        raise
                        
                    finally:
                        # Track operation completion
                        self.active_tools.add(-1, {"operation": operation_type.value})
                        
            return wrapper
        return decorator
    
    def _record_success(self, operation_key: str, duration: float, span):
        """Record successful operation metrics."""
        # Record metrics
        self.operation_counter.add(1, {"operation": operation_key, "status": "success"})
        self.operation_duration.record(duration, {"operation": operation_key, "status": "success"})
        
        # Update internal tracking
        if operation_key not in self.operation_metrics:
            self.operation_metrics[operation_key] = []
        self.operation_metrics[operation_key].append(duration)
        
        # Keep only last 100 measurements per operation
        if len(self.operation_metrics[operation_key]) > 100:
            self.operation_metrics[operation_key] = self.operation_metrics[operation_key][-100:]
            
        # Set span attributes
        span.set_attribute("operation.duration", duration)
        span.set_attribute("operation.status", "success")
        span.set_status(Status(StatusCode.OK))
        
        logger.debug(f"Operation {operation_key} completed successfully in {duration:.2f}s")
    
    def _record_error(self, operation_key: str, duration: float, span, error: Exception):
        """Record error metrics."""
        error_type = type(error).__name__
        
        # Record metrics
        self.error_counter.add(1, {"operation": operation_key, "error_type": error_type})
        self.operation_duration.record(duration, {"operation": operation_key, "status": "error"})
        
        # Update internal tracking
        error_key = f"{operation_key}_{error_type}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Set span attributes and status
        span.set_attribute("operation.duration", duration)
        span.set_attribute("operation.status", "error")
        span.set_attribute("error.type", error_type)
        span.set_attribute("error.message", str(error))
        span.set_status(Status(StatusCode.ERROR, str(error)))
        span.record_exception(error)
        
        logger.error(f"Operation {operation_key} failed after {duration:.2f}s: {error}")
    
    def track_llm_request(self, model: str, tokens_used: int, response_time: float, 
                         prompt_tokens: int = 0, completion_tokens: int = 0):
        """Track LLM request metrics."""
        
        # Handle None values by converting to 0
        prompt_tokens = prompt_tokens or 0
        completion_tokens = completion_tokens or 0
        
        # Record metrics
        self.token_counter.add(tokens_used, {"model": model, "type": "total"})
        if prompt_tokens > 0:
            self.token_counter.add(prompt_tokens, {"model": model, "type": "prompt"}) 
        if completion_tokens > 0:
            self.token_counter.add(completion_tokens, {"model": model, "type": "completion"})
            
        self.llm_response_time.record(response_time, {"model": model})
        
        # Update internal tracking
        self.token_usage_history.append(tokens_used)
        if len(self.token_usage_history) > 1000:
            self.token_usage_history = self.token_usage_history[-1000:]
        
        logger.debug(f"LLM request: {model}, tokens: {tokens_used}, time: {response_time:.2f}s")
    
    def track_context_usage(self, context_tokens: int, context_type: str = "general"):
        """Track context size metrics."""
        self.context_size.record(context_tokens, {"type": context_type})
        
    def take_performance_snapshot(self) -> MetricSnapshot:
        """Take a snapshot of current performance metrics."""
        try:
            import psutil
            memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
        except:
            memory_mb = 0
            
        # Calculate averages
        all_times = []
        total_ops = 0
        total_errors = sum(self.error_counts.values())
        
        for times in self.operation_metrics.values():
            all_times.extend(times)
            total_ops += len(times)
            
        avg_response = sum(all_times) / len(all_times) if all_times else 0
        total_tokens = sum(self.token_usage_history[-100:]) if self.token_usage_history else 0
        
        snapshot = MetricSnapshot(
            timestamp=time.time(),
            memory_usage_mb=memory_mb,
            token_usage=total_tokens,
            operation_count=total_ops,
            error_count=total_errors,
            average_response_time=avg_response
        )
        
        self.memory_snapshots.append(snapshot)
        if len(self.memory_snapshots) > 100:
            self.memory_snapshots = self.memory_snapshots[-100:]
            
        return snapshot
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        current_snapshot = self.take_performance_snapshot()
        
        # Calculate trends if we have historical data
        trends = {}
        if len(self.memory_snapshots) >= 2:
            prev_snapshot = self.memory_snapshots[-2]
            trends = {
                "memory_trend": current_snapshot.memory_usage_mb - prev_snapshot.memory_usage_mb,
                "response_time_trend": current_snapshot.average_response_time - prev_snapshot.average_response_time,
                "operation_rate": (current_snapshot.operation_count - prev_snapshot.operation_count) / max(1, current_snapshot.timestamp - prev_snapshot.timestamp)
            }
        
        return {
            "current_metrics": {
                "memory_usage_mb": current_snapshot.memory_usage_mb,
                "total_operations": current_snapshot.operation_count,
                "total_errors": current_snapshot.error_count,
                "average_response_time": current_snapshot.average_response_time,
                "total_tokens": current_snapshot.token_usage
            },
            "trends": trends,
            "top_operations": self._get_top_operations(),
            "top_errors": self._get_top_errors(),
            "error_rate": current_snapshot.error_count / max(1, current_snapshot.operation_count)
        }
    
    def _get_top_operations(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top operations by frequency and average duration."""
        operations = []
        for op_name, durations in self.operation_metrics.items():
            operations.append({
                "operation": op_name,
                "count": len(durations),
                "avg_duration": sum(durations) / len(durations),
                "total_duration": sum(durations)
            })
        
        return sorted(operations, key=lambda x: x["count"], reverse=True)[:limit]
    
    def _get_top_errors(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top errors by frequency."""
        errors = [{"error": error, "count": count} for error, count in self.error_counts.items()]
        return sorted(errors, key=lambda x: x["count"], reverse=True)[:limit]


# Global telemetry instance
telemetry = DevOpsAgentTelemetry()


# Convenience decorators
def track_tool_execution(tool_name: str = ""):
    """Decorator for tracking tool executions."""
    return telemetry.track_operation(OperationType.TOOL_EXECUTION, tool_name)


def track_llm_request_decorator(func: Callable) -> Callable:
    """Decorator for tracking LLM requests."""
    return telemetry.track_operation(OperationType.LLM_REQUEST)(func)


def track_context_operation_decorator(func: Callable) -> Callable:
    """Decorator for tracking context management operations."""
    return telemetry.track_operation(OperationType.CONTEXT_MANAGEMENT)(func)


def track_file_operation_decorator(operation_name: str = ""):
    """Decorator for tracking file operations."""
    return telemetry.track_operation(OperationType.FILE_OPERATION, operation_name)


def track_shell_command(func: Callable) -> Callable:
    """Decorator for tracking shell commands."""
    return telemetry.track_operation(OperationType.SHELL_COMMAND)(func)


def track_tool_usage(tool_name: str, execution_time: float, success: bool, **metadata):
    """Track tool usage metrics."""
    telemetry.tool_usage_counter.add(1, {
        "tool_name": tool_name,
        "status": "success" if success else "error",
        **metadata
    })
    telemetry.tool_execution_time.record(execution_time, {
        "tool_name": tool_name,
        "status": "success" if success else "error"
    })


def track_llm_request(model: str, tokens_used: int, response_time: float, 
                     prompt_tokens: int = 0, completion_tokens: int = 0):
    """Track LLM request metrics."""
    telemetry.track_llm_request(model, tokens_used, response_time, prompt_tokens, completion_tokens)


def track_context_operation(operation: str, items_count: int = 0):
    """Track context management operations."""
    telemetry.context_operations_counter.add(1, {"operation": operation})
    if items_count > 0:
        telemetry.context_cache_size.add(items_count, {"operation": operation})


def track_file_operation(operation: str, file_size_bytes: int = 0, success: bool = True):
    """Track file operations with size metrics."""
    if file_size_bytes > 0:
        telemetry.file_operation_size.record(file_size_bytes, {
            "operation": operation,
            "status": "success" if success else "error"
        })


def get_openlit_metrics_status() -> dict:
    """Get status of OpenLIT metrics configuration."""
    return {
        "openlit_enabled": True,  # Always true since we initialize it
        "gpu_monitoring": agent_config.OPENLIT_COLLECT_GPU_STATS,
        "metrics_disabled": agent_config.OPENLIT_DISABLE_METRICS,
        "environment": agent_config.OPENLIT_ENVIRONMENT,
        "available_metrics": {
            "llm_metrics": ["gen_ai.total.requests", "gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens", "gen_ai.usage.total_tokens", "gen_ai.usage.cost"],
            "vectordb_metrics": ["db.total.requests"],
            "gpu_metrics": ["gpu.utilization", "gpu.memory.used", "gpu.temperature", "gpu.power.draw"] if agent_config.OPENLIT_COLLECT_GPU_STATS else [],
            "custom_agent_metrics": [
                "devops_agent_operations_total",
                "devops_agent_errors_total", 
                "devops_agent_tool_usage_total",
                "devops_agent_context_operations_total",
                "devops_agent_operation_duration_seconds",
                "devops_agent_tool_execution_seconds",
                "devops_agent_file_operation_bytes",
                "devops_agent_memory_usage_mb",
                "devops_agent_cpu_usage_percent",
                "devops_agent_disk_usage_mb"
            ]
        }
    }
