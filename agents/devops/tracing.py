"""Enhanced tracing implementation for DevOps Agent using OpenLIT manual tracing."""

from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
import functools
import logging
import time
from typing import Any, Callable, Optional

try:
    import openlit

    OPENLIT_AVAILABLE = True
except ImportError:
    OPENLIT_AVAILABLE = False
    logging.warning("OpenLIT not available - manual tracing will be disabled")

from opentelemetry import trace

# Import agent configuration
from .config import (
    OPENLIT_CAPTURE_CONTENT,
    OPENLIT_DISABLE_BATCH,
    OPENLIT_DISABLED_INSTRUMENTORS,
    TRACE_SAMPLING_RATE,
)

logger = logging.getLogger(__name__)


class TraceCategory(Enum):
    """Categories of operations to trace."""

    AGENT_LIFECYCLE = "agent_lifecycle"
    LLM_INTERACTION = "llm_interaction"
    TOOL_EXECUTION = "tool_execution"
    CONTEXT_MANAGEMENT = "context_management"
    PLANNING = "planning"
    FILE_OPERATION = "file_operation"
    SHELL_COMMAND = "shell_command"
    RAG_OPERATION = "rag_operation"
    USER_INTERACTION = "user_interaction"
    ERROR_HANDLING = "error_handling"


@dataclass
class TraceMetadata:
    """Metadata for trace operations."""

    category: TraceCategory
    operation: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    model_name: Optional[str] = None
    tool_name: Optional[str] = None
    input_size: Optional[int] = None
    output_size: Optional[int] = None
    custom_attributes: Optional[dict[str, Any]] = None


class DevOpsAgentTracer:
    """Enhanced tracing for DevOps Agent operations using OpenLIT."""

    def __init__(self):
        self.openlit_available = OPENLIT_AVAILABLE
        self.otel_tracer = trace.get_tracer("devops_agent_tracer")
        self.active_traces: dict[str, Any] = {}

        # Configuration
        self.capture_content = OPENLIT_CAPTURE_CONTENT
        self.trace_sampling_rate = TRACE_SAMPLING_RATE

        logger.info(
            f"DevOpsAgentTracer initialized - OpenLIT: {'✅' if self.openlit_available else '❌'}"
        )

    def should_trace(self) -> bool:
        """Determine if we should create a trace based on sampling rate."""
        import random

        return random.random() < self.trace_sampling_rate

    def trace_agent_operation(
        self, operation_name: str, category: TraceCategory = TraceCategory.AGENT_LIFECYCLE
    ):
        """Decorator for tracing agent operations with OpenLIT."""

        def decorator(func: Callable) -> Callable:
            if not self.openlit_available or not self.should_trace():
                return func

            @openlit.trace
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Set up trace metadata
                TraceMetadata(
                    category=category,
                    operation=operation_name,
                    custom_attributes={
                        "function_name": func.__name__,
                        "module": func.__module__,
                        "args_count": len(args),
                        "kwargs_count": len(kwargs),
                    },
                )

                start_time = time.time()

                try:
                    result = func(*args, **kwargs)

                    # Calculate metrics
                    duration = time.time() - start_time

                    # Log successful operation
                    logger.debug(f"Traced operation {operation_name} completed in {duration:.2f}s")

                    return result

                except Exception as e:
                    duration = time.time() - start_time
                    logger.error(
                        f"Traced operation {operation_name} failed after {duration:.2f}s: {e}"
                    )
                    raise

            return wrapper

        return decorator

    @contextmanager
    def trace_llm_interaction(self, model_name: str, operation: str, **metadata):
        """Context manager for tracing LLM interactions with detailed metadata."""
        if not self.openlit_available or not self.should_trace():
            yield None
            return

        trace_name = f"LLM_{operation}_{model_name}"

        with openlit.start_trace(name=trace_name) as trace:
            # Set initial metadata
            trace.set_metadata(
                {
                    "model_name": model_name,
                    "operation": operation,
                    "category": TraceCategory.LLM_INTERACTION.value,
                    "start_time": time.time(),
                    **metadata,
                }
            )

            start_time = time.time()

            try:
                yield trace

                # Set success result
                duration = time.time() - start_time
                trace.set_result(f"LLM {operation} completed successfully")
                trace.set_metadata({"duration_seconds": duration, "status": "success"})

            except Exception as e:
                # Set error result
                duration = time.time() - start_time
                trace.set_result(f"LLM {operation} failed: {e!s}")
                trace.set_metadata(
                    {
                        "duration_seconds": duration,
                        "status": "error",
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    }
                )
                raise

    @contextmanager
    def trace_tool_execution(self, tool_name: str, **metadata):
        """Context manager for tracing tool executions."""
        if not self.openlit_available or not self.should_trace():
            yield None
            return

        trace_name = f"Tool_{tool_name}"

        with openlit.start_trace(name=trace_name) as trace:
            # Set initial metadata
            trace.set_metadata(
                {
                    "tool_name": tool_name,
                    "category": TraceCategory.TOOL_EXECUTION.value,
                    "start_time": time.time(),
                    **metadata,
                }
            )

            start_time = time.time()

            try:
                yield trace

                # Set success result
                duration = time.time() - start_time
                trace.set_result(f"Tool {tool_name} executed successfully")
                trace.set_metadata({"duration_seconds": duration, "status": "success"})

            except Exception as e:
                # Set error result
                duration = time.time() - start_time
                trace.set_result(f"Tool {tool_name} failed: {e!s}")
                trace.set_metadata(
                    {
                        "duration_seconds": duration,
                        "status": "error",
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    }
                )
                raise

    @contextmanager
    def trace_context_operation(self, operation: str, **metadata):
        """Context manager for tracing context management operations."""
        if not self.openlit_available or not self.should_trace():
            yield None
            return

        trace_name = f"Context_{operation}"

        with openlit.start_trace(name=trace_name) as trace:
            # Set initial metadata
            trace.set_metadata(
                {
                    "operation": operation,
                    "category": TraceCategory.CONTEXT_MANAGEMENT.value,
                    "start_time": time.time(),
                    **metadata,
                }
            )

            start_time = time.time()

            try:
                yield trace

                # Set success result
                duration = time.time() - start_time
                trace.set_result(f"Context {operation} completed successfully")
                trace.set_metadata({"duration_seconds": duration, "status": "success"})

            except Exception as e:
                # Set error result
                duration = time.time() - start_time
                trace.set_result(f"Context {operation} failed: {e!s}")
                trace.set_metadata(
                    {
                        "duration_seconds": duration,
                        "status": "error",
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    }
                )
                raise

    def trace_user_interaction(self, interaction_type: str):
        """Decorator for tracing user interactions."""

        def decorator(func: Callable) -> Callable:
            if not self.openlit_available or not self.should_trace():
                return func

            @openlit.trace
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()

                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time

                    logger.debug(
                        f"User interaction {interaction_type} completed in {duration:.2f}s"
                    )
                    return result

                except Exception as e:
                    duration = time.time() - start_time
                    logger.error(
                        f"User interaction {interaction_type} failed after {duration:.2f}s: {e}"
                    )
                    raise

            return wrapper

        return decorator

    def create_custom_trace(self, name: str, _category: TraceCategory, **_attributes):
        """Create a custom trace with OpenTelemetry fallback."""
        if self.openlit_available and self.should_trace():
            return openlit.start_trace(name=name)
        # Fallback to OpenTelemetry
        return self.otel_tracer.start_span(name)

    def get_trace_status(self) -> dict[str, Any]:
        """Get current tracing status and configuration."""
        return {
            "openlit_available": self.openlit_available,
            "capture_content": self.capture_content,
            "sampling_rate": self.trace_sampling_rate,
            "active_traces": len(self.active_traces),
            "configuration": {
                "OPENLIT_CAPTURE_CONTENT": OPENLIT_CAPTURE_CONTENT,
                "OPENLIT_DISABLE_BATCH": OPENLIT_DISABLE_BATCH,
                "TRACE_SAMPLING_RATE": TRACE_SAMPLING_RATE,
                "OPENLIT_DISABLED_INSTRUMENTORS": OPENLIT_DISABLED_INSTRUMENTORS,
            },
        }


# Global tracer instance
agent_tracer = DevOpsAgentTracer()


# Convenience decorators
def trace_agent_lifecycle(operation_name: str):
    """Decorator for tracing agent lifecycle operations."""
    return agent_tracer.trace_agent_operation(operation_name, TraceCategory.AGENT_LIFECYCLE)


def trace_llm_operation(operation_name: str):
    """Decorator for tracing LLM operations."""
    return agent_tracer.trace_agent_operation(operation_name, TraceCategory.LLM_INTERACTION)


def trace_tool_operation(tool_name: str):
    """Decorator for tracing tool operations."""
    return agent_tracer.trace_agent_operation(tool_name, TraceCategory.TOOL_EXECUTION)


def trace_context_operation_decorator(operation_name: str):
    """Decorator for tracing context operations."""
    return agent_tracer.trace_agent_operation(operation_name, TraceCategory.CONTEXT_MANAGEMENT)


def trace_user_interaction_decorator(interaction_type: str):
    """Decorator for tracing user interactions."""
    return agent_tracer.trace_user_interaction(interaction_type)


# Context managers (preferred for complex operations)
def trace_llm_request(model_name: str, operation: str = "request", **metadata):
    """Context manager for LLM requests."""
    return agent_tracer.trace_llm_interaction(model_name, operation, **metadata)


def trace_tool_execution(tool_name: str, **metadata):
    """Context manager for tool executions."""
    return agent_tracer.trace_tool_execution(tool_name, **metadata)


def trace_context_operation(operation: str, **metadata):
    """Context manager for context operations."""
    return agent_tracer.trace_context_operation(operation, **metadata)


# Utility functions
def get_tracing_status() -> dict[str, Any]:
    """Get current tracing status."""
    return agent_tracer.get_trace_status()


def set_trace_sampling_rate(rate: float):
    """Set the trace sampling rate (0.0 to 1.0)."""
    agent_tracer.trace_sampling_rate = max(0.0, min(1.0, rate))
    logger.info(f"Trace sampling rate set to {agent_tracer.trace_sampling_rate}")


# Integration with existing telemetry
def create_grouped_trace(_name: str, operations: list[Callable]):
    """Create a grouped trace that encompasses multiple operations."""
    if not agent_tracer.openlit_available:
        # Execute operations without tracing
        results = []
        for op in operations:
            results.append(op())
        return results

    @openlit.trace
    def grouped_operation():
        results = []
        for op in operations:
            results.append(op())
        return results

    return grouped_operation()
