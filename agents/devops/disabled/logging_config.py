"""Enhanced logging configuration with correlation IDs and structured logging."""

import logging
import logging.config
import json
import uuid
import threading
import os
import sys
from typing import Dict, Any, Optional
from contextvars import ContextVar
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

# Context variables for correlation
correlation_id: ContextVar[str] = ContextVar('correlation_id', default='')
user_session_id: ContextVar[str] = ContextVar('user_session_id', default='')
operation_context: ContextVar[Dict[str, Any]] = ContextVar('operation_context', default={})

# Context variable to store active spans for proper lifecycle management
active_spans: ContextVar[Dict[str, trace.Span]] = ContextVar('active_spans', default={})

class CorrelationIDFilter(logging.Filter):
    """Add correlation ID and trace information to log records."""
    
    def filter(self, record):
        # Add correlation ID
        record.correlation_id = correlation_id.get() or str(uuid.uuid4())
        
        # Add user session ID
        record.user_session_id = user_session_id.get() or "unknown"
        
        # Add OpenTelemetry trace context
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            span_context = current_span.get_span_context()
            record.trace_id = format(span_context.trace_id, '032x')
            record.span_id = format(span_context.span_id, '016x')
        else:
            record.trace_id = "none"
            record.span_id = "none"
            
        # Add operation context
        op_context = operation_context.get()
        record.operation = op_context.get('operation', 'unknown')
        record.component = op_context.get('component', 'devops_agent')
        
        return True


class InteractiveSessionFilter(logging.Filter):
    """Filter logs during interactive sessions to reduce console noise."""
    
    def __init__(self, interactive_mode: bool = False):
        super().__init__()
        self.interactive_mode = interactive_mode
        
        # Loggers that should be quiet during interactive sessions
        self.quiet_loggers = {
            'httpx',
            'openlit', 
            'chromadb',
            'opentelemetry',
            'google_genai',
            'google_adk',
            'devops.components.context_management',
            'devops.tools.rag_components',
        }
        
        # Only allow these levels for quiet loggers during interactive mode
        self.allowed_levels = {logging.WARNING, logging.ERROR, logging.CRITICAL}
    
    def filter(self, record):
        if not self.interactive_mode:
            return True
            
        # Check if this logger should be quiet during interactive sessions
        for quiet_logger in self.quiet_loggers:
            if record.name.startswith(quiet_logger):
                # Only allow warnings and errors from quiet loggers
                return record.levelno in self.allowed_levels
                
        # Allow all logs from other loggers
        return True


class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter."""
    
    def format(self, record):
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, 'correlation_id', 'unknown'),
            "user_session_id": getattr(record, 'user_session_id', 'unknown'),
            "trace_id": getattr(record, 'trace_id', 'none'),
            "span_id": getattr(record, 'span_id', 'none'),
            "operation": getattr(record, 'operation', 'unknown'),
            "component": getattr(record, 'component', 'devops_agent'),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "thread_name": record.threadName,
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
            
        # Add any extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 
                          'exc_text', 'stack_info', 'correlation_id', 'user_session_id',
                          'trace_id', 'span_id', 'operation', 'component']:
                log_entry[key] = value
                
        return json.dumps(log_entry, default=str)


class DevOpsAgentLogger:
    """Enhanced logger for DevOps Agent with correlation tracking."""
    
    def __init__(self, interactive_mode: bool = None):
        # Auto-detect interactive mode if not specified
        if interactive_mode is None:
            interactive_mode = self._detect_interactive_mode()
            
        self.interactive_mode = interactive_mode
        self.setup_logging()
        
    def _detect_interactive_mode(self) -> bool:
        """Detect if we're running in interactive mode."""
        # Check environment variables
        if os.getenv('DEVOPS_AGENT_INTERACTIVE', '').lower() in ('true', '1', 'yes'):
            return True
        if os.getenv('DEVOPS_AGENT_QUIET', '').lower() in ('true', '1', 'yes'):
            return True
            
        # Check if we're likely in an interactive session
        # This is a heuristic - you might want to adjust based on your setup
        return hasattr(sys, 'ps1') or sys.stdin.isatty()
        
    def setup_logging(self):
        """Setup enhanced logging configuration."""
        
        # Create correlation filter
        correlation_filter = CorrelationIDFilter()
        
        # Create interactive session filter
        interactive_filter = InteractiveSessionFilter(self.interactive_mode)
        
        # Determine console log level based on mode
        console_level = logging.WARNING if self.interactive_mode else logging.INFO
        
        # Setup console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_handler.addFilter(correlation_filter)
        console_handler.addFilter(interactive_filter)
        
        # Human-readable formatter for console
        if self.interactive_mode:
            # Minimal format for interactive mode
            console_formatter = logging.Formatter(
                '%(levelname)s: %(message)s'
            )
        else:
            # Full format for non-interactive mode
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] [%(trace_id)s:%(span_id)s] - %(message)s'
            )
        console_handler.setFormatter(console_formatter)
        
        # File handler with structured logging (always full detail)
        file_handler = logging.FileHandler('devops_agent.log')
        file_handler.setLevel(logging.INFO)
        file_handler.addFilter(correlation_filter)
        
        # Structured formatter for file
        structured_formatter = StructuredFormatter()
        file_handler.setFormatter(structured_formatter)
        
        # Setup root logger
        handlers = [file_handler]
        
        # Only add console handler if not in quiet mode
        if not os.getenv('DEVOPS_AGENT_QUIET', '').lower() in ('true', '1', 'yes'):
            handlers.append(console_handler)
        
        logging.basicConfig(
            level=logging.DEBUG,
            handlers=handlers,
            force=True
        )
        
        # Log the configuration
        logger = logging.getLogger(__name__)
        if self.interactive_mode:
            logger.debug("Logging configured for interactive mode - reduced console output")
        else:
            logger.info("Logging configured for non-interactive mode - full console output")
        
    def start_operation(self, operation_name: str, **context) -> str:
        """Start a new operation with correlation tracking."""
        corr_id = str(uuid.uuid4())
        correlation_id.set(corr_id)
        
        # Set operation context
        op_context = {
            'operation': operation_name,
            **context
        }
        operation_context.set(op_context)
        
        # Create OpenTelemetry span and make it current
        tracer = trace.get_tracer("devops_agent_logger")
        span = tracer.start_span(operation_name)
        span.set_attribute("correlation_id", corr_id)
        
        for key, value in context.items():
            span.set_attribute(f"operation.{key}", str(value))
        
        # Store the span reference for proper lifecycle management
        current_spans = active_spans.get({})
        current_spans[corr_id] = span
        active_spans.set(current_spans)
            
        logger = logging.getLogger(__name__)
        logger.info(f"Started operation: {operation_name}", extra={
            "operation_start": True,
            **context
        })
        
        return corr_id
        
    def end_operation(self, operation_name: str, success: bool = True, correlation_id_to_end: str = None, **context):
        """End an operation with correlation tracking."""
        current_spans = active_spans.get({})
        
        # Try to find the span to end
        span_to_end = None
        span_key_to_remove = None
        
        if correlation_id_to_end and correlation_id_to_end in current_spans:
            # Use specific correlation ID if provided
            span_to_end = current_spans[correlation_id_to_end]
            span_key_to_remove = correlation_id_to_end
        elif current_spans:
            # Find the most recent span for this operation
            for corr_id, span in current_spans.items():
                if span.is_recording():
                    span_to_end = span
                    span_key_to_remove = corr_id
                    break
        
        # If no specific span found, fall back to current span (but be careful)
        if not span_to_end:
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                span_to_end = current_span
        
        # Set span status and end it if valid
        if span_to_end and span_to_end.is_recording():
            if success:
                span_to_end.set_status(Status(StatusCode.OK))
            else:
                span_to_end.set_status(Status(StatusCode.ERROR))
            
            span_to_end.end()
            
            # Remove from active spans if we have the key
            if span_key_to_remove:
                current_spans.pop(span_key_to_remove, None)
                active_spans.set(current_spans)
        
        logger = logging.getLogger(__name__)
        logger.info(f"Completed operation: {operation_name}", extra={
            "operation_end": True,
            "success": success,
            **context
        })


# Global logger instance
agent_logger = DevOpsAgentLogger()


def get_logger(name: str) -> logging.Logger:
    """Get a logger with enhanced correlation tracking."""
    return logging.getLogger(name)


def set_interactive_mode(interactive: bool):
    """Set interactive mode for logging."""
    global agent_logger
    agent_logger = DevOpsAgentLogger(interactive_mode=interactive)


def log_performance_metrics(operation_name: str, duration: float, **metrics):
    """Log performance metrics with structured data."""
    logger = get_logger("performance")
    logger.info(f"Performance metrics for {operation_name}", extra={
        "metric_type": "performance",
        "operation": operation_name,
        "duration_seconds": duration,
        **metrics
    })


def log_security_event(event_type: str, details: Dict[str, Any]):
    """Log security-related events."""
    logger = get_logger("security")
    logger.warning(f"Security event: {event_type}", extra={
        "event_type": "security",
        "security_event_type": event_type,
        **details
    })


def log_business_event(event_type: str, details: Dict[str, Any]):
    """Log business-related events."""
    logger = get_logger("business")
    logger.info(f"Business event: {event_type}", extra={
        "event_type": "business",
        "business_event_type": event_type,
        **details
    })


def set_user_context(user_id: str, session_id: str = None):
    """Set user context for correlation tracking."""
    correlation_id.set(str(uuid.uuid4()))
    user_session_id.set(session_id or str(uuid.uuid4()))
    
    logger = get_logger("user_context")
    logger.info(f"User context set: {user_id}", extra={
        "user_id": user_id,
        "session_id": session_id
    })


def log_tool_usage(tool_name: str, input_size: int, output_size: int, 
                  duration: float, success: bool, **metadata):
    """Log tool usage metrics."""
    logger = get_logger("tools")
    logger.info(f"Tool usage: {tool_name}", extra={
        "event_type": "tool_usage",
        "tool_name": tool_name,
        "input_size_bytes": input_size,
        "output_size_bytes": output_size,
        "duration_seconds": duration,
        "success": success,
        **metadata
    })


def log_context_management(operation: str, context_size: int, tokens_used: int, 
                          optimization_applied: bool = False, **details):
    """Log context management operations."""
    logger = get_logger("context")
    logger.debug(f"Context management: {operation}", extra={
        "event_type": "context_management",
        "operation": operation,
        "context_size_chars": context_size,
        "tokens_used": tokens_used,
        "optimization_applied": optimization_applied,
        **details
    })


def log_operation(operation_name: str, **context):
    """Decorator for logging operations with correlation tracking."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            corr_id = agent_logger.start_operation(operation_name, **context)
            try:
                result = func(*args, **kwargs)
                agent_logger.end_operation(operation_name, success=True, correlation_id_to_end=corr_id)
                return result
            except Exception as e:
                agent_logger.end_operation(operation_name, success=False, correlation_id_to_end=corr_id, error=str(e))
                raise
        return wrapper
    return decorator 