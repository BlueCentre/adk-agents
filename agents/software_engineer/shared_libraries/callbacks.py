"""Shared callback utilities for Software Engineer Agent."""

import functools
import logging
import os
import time
from typing import Any, Optional, Protocol

# from google import genai
from google.adk.agents.callback_context import CallbackContext

# from google.adk.agents.invocation_context import InvocationContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types as genai_types

from .. import config as agent_config

logger = logging.getLogger(__name__)


def _callback_error_handler(agent_name: str, callback_name: str):
    """A decorator to handle errors in callback functions gracefully."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except AttributeError as e:
                logger.error(
                    f"[{agent_name}] Attribute error in {callback_name}: {e}",
                    exc_info=True,
                )
            except TypeError as e:
                logger.error(
                    f"[{agent_name}] Type error in {callback_name}: {e}",
                    exc_info=True,
                )
            except Exception as e:
                logger.error(
                    f"[{agent_name}] Unexpected error in {callback_name}: {e}",
                    exc_info=True,
                )

        return wrapper

    return decorator


class TelemetryProvider(Protocol):
    """Protocol for telemetry providers to avoid tight coupling."""

    def track_llm_request(
        self, model: str, tokens_used: int, response_time: float, prompt_tokens: int
    ) -> None:
        """Track an LLM request."""
        ...

    def track_tool_execution(self, tool_name: str, execution_time: float, success: bool) -> None:
        """Track a tool execution."""
        ...

    def track_agent_session_start(self, agent_name: str, session_id: str) -> None:
        """Track agent session start."""
        ...

    def track_agent_session_end(self, agent_name: str, session_id: str, duration: float) -> None:
        """Track agent session end."""
        ...


class NoOpTelemetryProvider:
    """No-op implementation for when no telemetry is available."""

    def track_llm_request(
        self, model: str, tokens_used: int, response_time: float, prompt_tokens: int
    ) -> None:
        pass

    def track_tool_execution(self, tool_name: str, execution_time: float, success: bool) -> None:
        pass

    def track_agent_session_start(self, agent_name: str, session_id: str) -> None:
        pass

    def track_agent_session_end(self, agent_name: str, session_id: str, duration: float) -> None:
        pass


class DevOpsTelemetryProvider:
    """Adapter for DevOps telemetry when available."""

    def __init__(self):
        try:
            from ...devops.telemetry import track_llm_request, track_tool_usage

            self.track_llm_request_impl = track_llm_request
            self.track_tool_usage_impl = track_tool_usage
            self.available = True
            logger.debug("DevOps telemetry provider initialized successfully")
        except ImportError:
            self.available = False
            logger.debug("DevOps telemetry not available")

    def track_llm_request(
        self, model: str, tokens_used: int, response_time: float, prompt_tokens: int
    ) -> None:
        if self.available:
            try:
                self.track_llm_request_impl(
                    model=model,
                    tokens_used=tokens_used,
                    response_time=response_time,
                    prompt_tokens=prompt_tokens,
                )
            except Exception as e:
                logger.warning(f"Failed to track LLM request: {e}")

    def track_tool_usage(
        self, agent_name: str, tool_name: str, invocation_id: str, event: str, **kwargs
    ) -> None:
        if self.available:
            try:
                self.track_tool_usage_impl(
                    tool_name=tool_name,
                    execution_time=kwargs.get("execution_time", 0.0),
                    success=kwargs.get("success", True),
                )
            except Exception as e:
                logger.warning(f"Failed to track tool usage: {e}")

    def track_agent_session(self, agent_name: str, session_id: str, event: str, **kwargs) -> None:
        """Track agent lifecycle events (start/end)."""
        if self.available:
            try:
                # DevOps telemetry may not have specific session tracking
                # Log locally for now
                logger.debug(f"Agent session {event}: {agent_name} ({session_id})")
                if kwargs.get("duration"):
                    logger.debug(f"Session duration: {kwargs['duration']:.2f}s")
            except Exception as e:
                logger.warning(f"Failed to track agent session: {e}")

    def track_model_request(
        self, agent_name: str, model: str, invocation_id: str, event: str, **kwargs
    ) -> None:
        """Track model request events (start/end)."""
        if self.available:
            try:
                # DevOps telemetry may not have specific model request tracking
                # Log locally for now
                logger.debug(f"Model request {event}: {model} ({invocation_id})")
            except Exception as e:
                logger.warning(f"Failed to track model request: {e}")


def _get_telemetry_provider() -> TelemetryProvider:
    """Get the appropriate telemetry provider based on availability."""
    # Try DevOps telemetry first
    devops_provider = DevOpsTelemetryProvider()
    if devops_provider.available:
        return devops_provider

    # Fall back to no-op
    return NoOpTelemetryProvider()


def _load_project_context(
    callback_context: CallbackContext = None,
) -> Optional[dict[str, Any]]:
    """Load project context information for the agent session."""
    try:
        # Try multiple strategies to determine the working directory
        current_dir = _determine_working_directory(callback_context)

        if not current_dir or not os.path.exists(current_dir):
            logger.warning(f"Could not determine valid working directory: {current_dir}")
            return None

        # Safely list directory contents with count limit check
        MAX_PROJECT_FILES = 10000
        project_files = []

        try:
            with os.scandir(current_dir) as it:
                for entry in it:
                    project_files.append(entry.name)
                    if len(project_files) > MAX_PROJECT_FILES:
                        logger.warning(
                            f"Project directory '{current_dir}' contains more than {MAX_PROJECT_FILES} files. "
                            f"Skipping project context analysis to prevent performance issues."
                        )
                        return None
        except (PermissionError, OSError) as e:
            logger.warning(f"Could not list directory contents for {current_dir}: {e}")
            return None

        # Detect project type using multiple strategies
        project_type = _detect_project_type(project_files, current_dir)

        # Get basic project statistics
        total_files = len(project_files)
        python_files = len([f for f in project_files if f.endswith(".py")])
        js_files = len([f for f in project_files if f.endswith((".js", ".ts"))])

        project_context = {
            "working_directory": current_dir,
            "project_name": os.path.basename(current_dir),
            "project_type": project_type,
            "total_files": total_files,
            "python_files": python_files,
            "javascript_files": js_files,
            "files_found": project_files[:20],  # First 20 files
        }

        # Store context information in the callback context for tools to use
        if callback_context and hasattr(callback_context, "user_data"):
            callback_context.user_data["project_context"] = project_context

        return project_context

    except PermissionError as e:
        logger.warning(f"Permission denied accessing project context: {e}")
        return None
    except FileNotFoundError as e:
        logger.warning(f"Directory not found for project context: {e}")
        return None
    except OSError as e:
        logger.warning(f"OS error loading project context: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading project context: {e}")
        return None


def _determine_working_directory(
    callback_context: CallbackContext = None,
) -> Optional[str]:
    """Determine working directory using multiple strategies."""
    # Strategy 1: Try to get from callback context if available
    if callback_context:
        if hasattr(callback_context, "working_directory") and callback_context.working_directory:
            return callback_context.working_directory
        if hasattr(callback_context, "user_data") and callback_context.user_data:
            if "working_directory" in callback_context.user_data:
                return callback_context.user_data["working_directory"]

    # Strategy 2: Try environment variables
    for env_var in ["PWD", "PROJECT_ROOT", "WORKSPACE_ROOT"]:
        env_dir = os.getenv(env_var)
        if env_dir:
            # Normalize path to prevent traversal and ensure it's a directory.
            safe_path = os.path.abspath(env_dir)
            if os.path.isdir(safe_path):
                return safe_path

    # Strategy 3: Fall back to os.getcwd() with error handling
    try:
        return os.getcwd()
    except (OSError, PermissionError) as e:
        logger.warning(f"os.getcwd() failed: {e}")
        return None


def _safe_list_directory(directory: str) -> Optional[list[str]]:
    """Safely list directory contents with proper error handling."""
    try:
        if not os.path.exists(directory):
            return None
        if not os.path.isdir(directory):
            return None
        return os.listdir(directory)
    except PermissionError:
        logger.warning(f"Permission denied listing directory: {directory}")
        return None
    except OSError as e:
        logger.warning(f"OS error listing directory {directory}: {e}")
        return None


def _detect_project_type(project_files: list[str], current_dir: str) -> str:
    """Detect project type using multiple indicators."""
    # Check for specific configuration files in order of precedence
    type_indicators = [
        (["pyproject.toml", "uv.lock"], "python"),
        (["requirements.txt", "setup.py", "setup.cfg"], "python"),
        (["package.json", "package-lock.json", "yarn.lock"], "javascript"),
        (["Cargo.toml", "Cargo.lock"], "rust"),
        (["go.mod", "go.sum"], "go"),
        (["composer.json", "composer.lock"], "php"),
        (["Gemfile", "Gemfile.lock"], "ruby"),
        (["pom.xml", "build.gradle", "build.gradle.kts"], "java"),
        (["tsconfig.json"], "typescript"),
        (["Dockerfile", "docker-compose.yml", "docker-compose.yaml"], "docker"),
    ]

    for indicators, project_type in type_indicators:
        if any(indicator in project_files for indicator in indicators):
            return project_type

    # Check for language-specific directories
    if "src" in project_files or "lib" in project_files:
        # Look for language hints in subdirectories
        try:
            src_path = os.path.join(current_dir, "src")
            if os.path.exists(src_path):
                src_files = os.listdir(src_path)
                if any(f.endswith((".py", ".pyx")) for f in src_files):
                    return "python"
                if any(f.endswith((".js", ".ts", ".jsx", ".tsx")) for f in src_files):
                    return "javascript"
                if any(f.endswith((".rs",)) for f in src_files):
                    return "rust"
        except (OSError, PermissionError):
            pass  # Ignore errors in subdirectory inspection

    return "unknown"


def create_telemetry_callbacks(agent_name: str, enhanced: bool = False):
    """
    Create telemetry callbacks for an agent.

    Args:
        agent_name: Name of the agent for logging and metrics
        enhanced: Whether to attempt enhanced telemetry (DevOps integration)

    Returns:
        Dictionary containing callback functions
    """
    # Get appropriate telemetry provider
    telemetry_provider = _get_telemetry_provider() if enhanced else NoOpTelemetryProvider()

    @_callback_error_handler(agent_name, "before_agent_callback")
    def before_agent_callback(callback_context: CallbackContext = None):
        """Callback executed before agent starts processing."""
        session_id = (
            getattr(callback_context, "session_id", "unknown")
            if callback_context and hasattr(callback_context, "session_id")
            else "unknown"
        )

        prefix = "Enhanced" if enhanced else "Basic"
        logger.info(f"[{agent_name}] {prefix} agent session started - Session ID: {session_id}")

        # Track agent session start time
        start_time = time.time()
        if callback_context:
            callback_context._agent_session_start_time = start_time

        # Load project context
        project_context = _load_project_context(callback_context)
        if project_context:
            logger.info(f"[{agent_name}] Project context loaded:")
            logger.info(f"  - Working directory: {project_context.get('working_dir', 'unknown')}")
            logger.info(f"  - Project type: {project_context.get('project_type', 'unknown')}")
            logger.info(f"  - File count: {project_context.get('total_files', 0)}")

        # Initialize session metrics
        if callback_context:
            callback_context._agent_metrics = {
                "session_start_time": start_time,
                "total_model_calls": 0,
                "total_tool_calls": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_response_time": 0.0,
                "project_context": project_context,
            }

        # Log agent lifecycle event
        logger.info(f"[{agent_name}] Agent lifecycle: SESSION_START")

        # Track with telemetry provider if enhanced mode and available
        if enhanced and telemetry_provider and telemetry_provider.available:
            telemetry_provider.track_agent_session(
                agent_name=agent_name,
                session_id=session_id,
                event="start",
                project_context=project_context,
            )

    @_callback_error_handler(agent_name, "after_agent_callback")
    def after_agent_callback(callback_context: CallbackContext = None):
        """Callback executed after agent completes processing."""
        session_id = (
            getattr(callback_context, "session_id", "unknown") if callback_context else "unknown"
        )

        prefix = "Enhanced" if enhanced else "Basic"
        logger.info(f"[{agent_name}] {prefix} agent session completed - Session ID: {session_id}")

        # Calculate session duration and generate summary
        if callback_context and hasattr(callback_context, "_agent_session_start_time"):
            session_duration = time.time() - callback_context._agent_session_start_time
            logger.info(f"[{agent_name}] Session duration: {session_duration:.2f} seconds")

            # Generate session summary
            if hasattr(callback_context, "_agent_metrics"):
                metrics = callback_context._agent_metrics
                logger.info(f"[{agent_name}] Session summary:")
                logger.info(f"  - Total model calls: {metrics.get('total_model_calls', 0)}")
                logger.info(f"  - Total tool calls: {metrics.get('total_tool_calls', 0)}")
                logger.info(f"  - Total input tokens: {metrics.get('total_input_tokens', 0)}")
                logger.info(f"  - Total output tokens: {metrics.get('total_output_tokens', 0)}")
                logger.info(
                    f"  - Total response time: {metrics.get('total_response_time', 0.0):.2f}s"
                )

        # Log agent lifecycle event
        logger.info(f"[{agent_name}] Agent lifecycle: SESSION_END")

        # Track with telemetry provider if enhanced mode and available
        if enhanced and telemetry_provider and telemetry_provider.available:
            telemetry_provider.track_agent_session(
                agent_name=agent_name,
                session_id=session_id,
                event="end",
                duration=session_duration if "session_duration" in locals() else 0,
            )

    @_callback_error_handler(agent_name, "before_model_callback")
    def before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest):
        """Callback executed before LLM model request."""
        invocation_id = (
            getattr(callback_context, "invocation_id", "unknown") if callback_context else "unknown"
        )
        logger.debug(f"[{agent_name}] Before model request - ID: {invocation_id}")

        # DEBUG: Inspect the LLM request configuration
        if hasattr(llm_request, "config") and llm_request.config:
            logger.info(f"[{agent_name}] LLM Request Config: {llm_request.config}")
        else:
            logger.info(f"[{agent_name}] LLM Request has no config attribute or config is None.")

        # Update session metrics
        if callback_context and hasattr(callback_context, "_agent_metrics"):
            callback_context._agent_metrics["total_model_calls"] += 1

        # Track request start time
        if callback_context:
            callback_context._model_request_start_time = time.time()

        # Track with telemetry provider if enhanced mode and available
        if enhanced and telemetry_provider and telemetry_provider.available:
            model_name = getattr(llm_request, "model", "unknown") if llm_request else "unknown"
            telemetry_provider.track_model_request(
                agent_name=agent_name,
                model=model_name,
                invocation_id=invocation_id,
                event="start",
            )

    @_callback_error_handler(agent_name, "after_model_callback")
    def after_model_callback(callback_context: CallbackContext, llm_response: LlmResponse):
        """Callback executed after LLM model response."""
        invocation_id = (
            getattr(callback_context, "invocation_id", "unknown") if callback_context else "unknown"
        )
        logger.debug(f"[{agent_name}] After model response - ID: {invocation_id}")

        # Calculate response time
        response_time = 0.0
        if callback_context and hasattr(callback_context, "_model_request_start_time"):
            response_time = time.time() - callback_context._model_request_start_time

        # Update session metrics
        if callback_context and hasattr(callback_context, "_agent_metrics"):
            metrics = callback_context._agent_metrics
            if llm_response and hasattr(llm_response, "usage"):
                usage = llm_response.usage
                if usage:
                    metrics["total_input_tokens"] += getattr(usage, "input_tokens", 0)
                    metrics["total_output_tokens"] += getattr(usage, "output_tokens", 0)
            metrics["total_response_time"] += response_time

        # Track with telemetry provider if enhanced mode and available
        if enhanced and telemetry_provider and telemetry_provider.available:
            # Extract token usage information
            input_tokens = 0
            output_tokens = 0
            if llm_response and hasattr(llm_response, "usage"):
                usage = llm_response.usage
                if usage:
                    input_tokens = getattr(usage, "input_tokens", 0)
                    output_tokens = getattr(usage, "output_tokens", 0)

            telemetry_provider.track_llm_request(
                model=getattr(llm_response, "model", "unknown") if llm_response else "unknown",
                tokens_used=input_tokens + output_tokens,
                response_time=response_time,
                prompt_tokens=input_tokens,
            )

    @_callback_error_handler(agent_name, "before_tool_callback")
    def before_tool_callback(
        tool: BaseTool,
        args: dict,
        tool_context: ToolContext,
        callback_context: CallbackContext = None,
    ):
        """Callback executed before tool execution."""
        tool_name = getattr(tool, "name", "unknown") if tool else "unknown"
        invocation_id = (
            getattr(callback_context, "invocation_id", "unknown") if callback_context else "unknown"
        )
        logger.debug(
            f"[{agent_name}] Before tool execution - Tool: {tool_name}, ID: {invocation_id}"
        )

        # Update session metrics
        if callback_context and hasattr(callback_context, "_agent_metrics"):
            callback_context._agent_metrics["total_tool_calls"] += 1

        # Track tool start time
        if callback_context:
            callback_context._tool_start_time = time.time()

        # Track with telemetry provider if enhanced mode and available
        if enhanced and telemetry_provider and telemetry_provider.available:
            telemetry_provider.track_tool_usage(
                agent_name=agent_name,
                tool_name=tool_name,
                invocation_id=invocation_id,
                event="start",
                args=args,
            )

    @_callback_error_handler(agent_name, "after_tool_callback")
    def after_tool_callback(
        tool: BaseTool,
        tool_response: Any,
        callback_context: CallbackContext = None,
        args: Optional[dict] = None,
        tool_context: ToolContext = None,
    ):
        """Callback executed after tool execution."""
        tool_name = getattr(tool, "name", "unknown") if tool else "unknown"
        invocation_id = (
            getattr(callback_context, "invocation_id", "unknown") if callback_context else "unknown"
        )
        logger.debug(
            f"[{agent_name}] After tool execution - Tool: {tool_name}, ID: {invocation_id}"
        )

        # Calculate tool execution time
        execution_time = 0.0
        if callback_context and hasattr(callback_context, "_tool_start_time"):
            execution_time = time.time() - callback_context._tool_start_time

        # Log tool result preview
        if tool_response is not None:
            result_preview = (
                str(tool_response)[:200] + "..."
                if len(str(tool_response)) > 200
                else str(tool_response)
            )
            logger.debug(f"[{agent_name}] Tool result preview: {result_preview}")

        # Track with telemetry provider if enhanced mode and available
        if enhanced and telemetry_provider and telemetry_provider.available:
            telemetry_provider.track_tool_usage(
                agent_name=agent_name,
                tool_name=tool_name,
                invocation_id=invocation_id,
                event="end",
                execution_time=execution_time,
                result=tool_response,
            )

    return {
        "before_agent": before_agent_callback,
        "after_agent": after_agent_callback,
        "before_model": before_model_callback,
        "after_model": after_model_callback,
        "before_tool": before_tool_callback,
        "after_tool": after_tool_callback,
    }


def create_enhanced_telemetry_callbacks(agent_name: str):
    """
    Create enhanced telemetry callbacks that use DevOps telemetry when available.

    This is a convenience function that calls create_telemetry_callbacks with enhanced=True.
    """
    return create_telemetry_callbacks(agent_name, enhanced=True)


def _create_thinking_config(model_name: str) -> Optional[genai_types.ThinkingConfig]:
    """
    Create thinking configuration if thinking is enabled and supported for the current model.

    Ref: @devops_agent.py:MyDevopsAgent:_create_thinking_config
    """

    if not agent_config.should_enable_thinking(model_name):
        logger.info(f"Thinking is not enabled for model {model_name}")
        return None

    logger.info(f"Creating thinking configuration for model {model_name}")
    logger.info(f"  Include thoughts: {agent_config.GEMINI_THINKING_INCLUDE_THOUGHTS}")
    logger.info(f"  Thinking budget: {agent_config.GEMINI_THINKING_BUDGET}")

    return genai_types.ThinkingConfig(
        include_thoughts=agent_config.GEMINI_THINKING_INCLUDE_THOUGHTS,
        thinking_budget=agent_config.GEMINI_THINKING_BUDGET,
    )


def create_model_config_callbacks(model_name: str):
    """
    Create model config callbacks for an agent.

    Ref: @devops_agent.py:MyDevopsAgent:handle_before_model

    Args:
        model_name: Name of the model to enable thinking config

    Returns:
        Dictionary containing callback functions
    """

    # @_callback_error_handler(model_name, "before_model_callback")
    def before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest):
        """Callback executed before LLM model request."""
        invocation_id = (
            getattr(callback_context, "invocation_id", "unknown") if callback_context else "unknown"
        )
        logger.debug(f"[{model_name}] Before model request - ID: {invocation_id}")
        # Apply thinking configuration if supported and enabled
        thinking_config = _create_thinking_config(model_name)
        if thinking_config and hasattr(llm_request, "config"):
            # Apply thinking config to the existing request config
            if hasattr(llm_request.config, "thinking_config"):
                llm_request.config.thinking_config = thinking_config
                logger.info("Applied thinking configuration to LLM request")
            else:
                logger.warning("LLM request config does not support thinking_config attribute")
        elif thinking_config:
            logger.warning(
                "LLM request does not have config attribute to apply thinking configuration"
            )

    return {
        "before_model": before_model_callback,
    }
