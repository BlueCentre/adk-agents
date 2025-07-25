"""Shared callback utilities for Software Engineer Agent."""

import functools
import logging
import os
from pathlib import Path
import time
from typing import Any, Callable, Optional, Protocol

# from google import genai
from google.adk.agents.callback_context import CallbackContext

# from google.adk.agents.invocation_context import InvocationContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types as genai_types

from .. import config as agent_config
from .content_prioritizer import ContentPrioritizer
from .context_assembler import ContextAssembler
from .context_bridge_builder import BridgingStrategy, ContextBridgeBuilder
from .context_correlator import ContextCorrelator
from .conversation_analyzer import ConversationAnalyzer
from .conversation_filter import ConversationFilter, FilteringPolicy, FilterStrategy
from .token_optimization import ContextBudgetManager, TokenCounter

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

    def __init__(self):
        self.available = False

    def track_llm_request(
        self,
        model: str,
        tokens_used: int,
        response_time: float,
        prompt_tokens: int,
    ) -> None:
        pass

    def track_tool_execution(self, tool_name: str, execution_time: float, success: bool) -> None:
        pass

    def track_agent_session_start(self, agent_name: str, session_id: str) -> None:
        pass

    def track_agent_session_end(self, agent_name: str, session_id: str, duration: float) -> None:
        pass

    def track_agent_session(self, agent_name: str, session_id: str, event: str, **kwargs) -> None:
        """Track agent lifecycle events (start/end) - no-op implementation."""

    def track_model_request(
        self, agent_name: str, model: str, invocation_id: str, event: str, **kwargs
    ) -> None:
        """Track model request events (start/end) - no-op implementation."""

    def track_tool_usage(
        self, agent_name: str, tool_name: str, invocation_id: str, event: str, **kwargs
    ) -> None:
        """Track tool usage events - no-op implementation."""


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
        self,
        model: str,
        tokens_used: int,
        response_time: float,
        prompt_tokens: int,
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
        self,
        agent_name: str,  # noqa: ARG002
        tool_name: str,
        invocation_id: str,  # noqa: ARG002
        event: str,  # noqa: ARG002
        **kwargs,
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
        self,
        agent_name: str,  # noqa: ARG002
        model: str,
        invocation_id: str,
        event: str,
        **kwargs,  # noqa: ARG002
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

        if not current_dir or not Path(current_dir).exists():
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
                            f"Project directory '{current_dir}' contains more than "
                            f"{MAX_PROJECT_FILES} files. "
                            "Skipping project context analysis to prevent performance issues."
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
            "project_name": Path(current_dir).name,
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
        env_value = os.getenv(env_var)
        if env_value:
            env_dir = Path(env_value)
            # Normalize path to prevent traversal and ensure it's a directory.
            safe_path = env_dir.resolve()
            if safe_path.is_dir():
                return str(safe_path)

    # Strategy 3: Fall back to os.getcwd() with error handling
    try:
        return str(Path.cwd())
    except (OSError, PermissionError) as e:
        logger.warning(f"os.getcwd() failed: {e}")
        return None


def _safe_list_directory(directory: str) -> Optional[list[str]]:
    """Safely list directory contents with proper error handling."""
    try:
        if not Path(directory).exists():
            return None
        if not Path(directory).is_dir():
            return None
        return [str(p.name) for p in Path(directory).iterdir()]
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
            src_path = Path(current_dir) / "src"
            if src_path.exists():
                src_files = [str(p.name) for p in Path(src_path).iterdir()]
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
        tool_context: ToolContext,  # noqa: ARG001
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
        args: Optional[dict] = None,  # noqa: ARG001
        tool_context: ToolContext = None,  # noqa: ARG001
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


def create_token_optimization_callbacks(
    agent_name: str,
    model_name: Optional[str] = None,
    max_token_limit: Optional[int] = None,
) -> dict[str, Callable]:
    """
    Create focused token optimization callbacks.

    Single purpose: Token budget management and context optimization.
    Does NOT handle telemetry - designed to work alongside telemetry callbacks.

    Args:
        agent_name: Name of the agent for logging context
        model_name: Optional model name (derives from config if not provided)
        max_token_limit: Optional token limit (derives from config if not provided)

    Returns:
        Dictionary containing focused token optimization callback functions
    """
    # Derive from config with parameter fallback
    resolved_model_name = model_name or agent_config.DEFAULT_AGENT_MODEL
    resolved_token_limit = max_token_limit or agent_config.GEMINI_FLASH_TOKEN_LIMIT_FALLBACK

    # Initialize complete token optimization pipeline (Phase 1 + Phase 2)
    token_counter = TokenCounter(resolved_model_name)
    budget_manager = ContextBudgetManager(resolved_token_limit)
    analyzer = ConversationAnalyzer()
    conversation_filter = ConversationFilter(analyzer=analyzer, token_counter=token_counter)

    # Initialize advanced Phase 2 components
    content_prioritizer = ContentPrioritizer()
    context_correlator = ContextCorrelator()
    context_assembler = ContextAssembler(token_counter=token_counter)
    context_bridge_builder = ContextBridgeBuilder(correlator=context_correlator)

    @_callback_error_handler(agent_name, "token_optimization_before_agent")
    def token_optimization_before_agent(callback_context: CallbackContext):
        """Initialize token optimization session."""
        invocation_id = (
            getattr(callback_context, "invocation_id", "unknown") if callback_context else "unknown"
        )

        logger.info(f"[{agent_name}] Token optimization session starting - ID: {invocation_id}")

        # Initialize session optimization state
        if callback_context:
            callback_context._token_optimization_session = {
                "session_start_time": time.time(),
                "total_optimizations": 0,
                "total_tokens_saved": 0,
                "model_name": resolved_model_name,
                "token_limit": resolved_token_limit,
            }

    @_callback_error_handler(agent_name, "token_optimization_after_agent")
    def token_optimization_after_agent(callback_context: CallbackContext):
        """Session cleanup and final optimization metrics."""
        invocation_id = (
            getattr(callback_context, "invocation_id", "unknown") if callback_context else "unknown"
        )

        if callback_context and hasattr(callback_context, "_token_optimization_session"):
            session_data = callback_context._token_optimization_session
            session_duration = time.time() - session_data["session_start_time"]

            logger.info(f"[{agent_name}] Token optimization session complete - ID: {invocation_id}")
            logger.info(f"  Session duration: {session_duration:.2f}s")
            logger.info(f"  Total optimizations: {session_data['total_optimizations']}")
            logger.info(f"  Total tokens saved: {session_data['total_tokens_saved']:,}")

            # Cleanup session state
            delattr(callback_context, "_token_optimization_session")

    @_callback_error_handler(agent_name, "token_optimization_before_model")
    def token_optimization_before_model(callback_context: CallbackContext, llm_request: LlmRequest):
        """Token optimization before LLM model request."""
        invocation_id = (
            getattr(callback_context, "invocation_id", "unknown") if callback_context else "unknown"
        )

        # Apply advanced token optimization pipeline
        logger.info(f"[{agent_name}] Starting advanced token optimization - ID: {invocation_id}")

        try:
            # Step 1: Token Analysis & Budget Calculation
            available_budget, budget_breakdown = budget_manager.calculate_available_context_budget(
                llm_request, token_counter
            )

            logger.info(
                f"[{agent_name}] Step 1: Token budget calculated: {available_budget:,} tokens"
            )
            logger.info(
                f"[{agent_name}] Base utilization: {budget_breakdown['utilization_pct']:.1f}%"
            )

            # Convert content to format expected by advanced components
            content_items = []
            if hasattr(llm_request, "contents") and llm_request.contents:
                for i, content in enumerate(llm_request.contents):
                    content_items.append(
                        {
                            "id": f"content_{i}",
                            "text": getattr(content, "text", str(content)) if content else "",
                            "role": getattr(content, "role", "unknown") if content else "unknown",
                            "has_function_call": hasattr(content, "parts")
                            and any(
                                hasattr(part, "function_call")
                                for part in getattr(content, "parts", [])
                            )
                            if content
                            else False,
                            "has_function_response": hasattr(content, "parts")
                            and any(
                                hasattr(part, "function_response")
                                for part in getattr(content, "parts", [])
                            )
                            if content
                            else False,
                            "is_system_message": getattr(content, "role", "") == "system"
                            if content
                            else False,
                            "is_current_turn": i == len(llm_request.contents) - 1,
                            "timestamp": time.time()
                            - (len(llm_request.contents) - i) * 60,  # Approximate timestamps
                        }
                    )

            # Store initial optimization state
            if callback_context:
                callback_context._token_optimization = {
                    "available_budget": available_budget,
                    "budget_breakdown": budget_breakdown,
                    "original_content_count": len(content_items),
                    "optimization_applied": False,
                    "pipeline_used": "advanced",
                    "steps_completed": ["token_analysis"],
                }

            # Check if advanced optimization is needed
            if (
                len(content_items) > 5  # Minimum content for advanced optimization
                and budget_breakdown["utilization_pct"] > 70.0  # Trigger when >70% utilized
            ):
                logger.info(f"[{agent_name}] Applying advanced optimization pipeline")

                # Step 2: Content Prioritization
                logger.info(f"[{agent_name}] Step 2: Prioritizing content...")
                current_query = content_items[-1].get("text", "") if content_items else ""
                context = {"user_query": current_query}

                prioritized_content = content_prioritizer.prioritize_content_list(
                    content_items, context
                )
                callback_context._token_optimization["steps_completed"].append(
                    "content_prioritization"
                )

                # Step 3: Cross-Turn Dependency Analysis
                logger.info(f"[{agent_name}] Step 3: Analyzing dependencies...")
                correlation_result = context_correlator.correlate_context(prioritized_content)
                callback_context._token_optimization["steps_completed"].append(
                    "dependency_analysis"
                )
                callback_context._token_optimization["dependencies_found"] = len(
                    correlation_result.references
                )

                # Step 4: Priority-Based Context Assembly
                logger.info(f"[{agent_name}] Step 4: Assembling prioritized context...")
                assembly_result = context_assembler.assemble_prioritized_context(
                    prioritized_content, available_budget
                )
                callback_context._token_optimization["steps_completed"].append("context_assembly")

                # Step 5: Smart Context Bridging
                logger.info(f"[{agent_name}] Step 5: Building context bridges...")
                preserved_content_ids = {
                    item.get("id") for item in assembly_result.assembled_content
                }

                # Determine bridging strategy based on budget pressure
                utilization_pct = budget_breakdown["utilization_pct"]
                if utilization_pct > 90:
                    bridging_strategy = BridgingStrategy.AGGRESSIVE
                elif utilization_pct > 80:
                    bridging_strategy = BridgingStrategy.MODERATE
                else:
                    bridging_strategy = BridgingStrategy.CONSERVATIVE

                bridging_result = context_bridge_builder.build_context_bridges(
                    prioritized_content, preserved_content_ids, bridging_strategy
                )
                callback_context._token_optimization["steps_completed"].append("context_bridging")
                callback_context._token_optimization["bridges_created"] = len(
                    bridging_result.bridges
                )

                # Step 6: Final Content Assembly with Bridges
                logger.info(f"[{agent_name}] Step 6: Final content assembly...")
                final_content = []

                # Add preserved content and bridges in order
                content_lookup = {item.get("id"): item for item in prioritized_content}
                bridge_positions = {}

                # Map bridge positions
                for bridge in bridging_result.bridges:
                    for source_id in bridge.source_content_ids:
                        bridge_positions[source_id] = bridge

                # Build final content with bridges
                for item in assembly_result.assembled_content:
                    item_id = item.get("id")
                    final_content.append(content_lookup.get(item_id, item))

                    # Add bridge if this content has one
                    if item_id in bridge_positions:
                        bridge = bridge_positions[item_id]
                        bridge_content = {
                            "id": bridge.bridge_id,
                            "text": bridge.bridge_content,
                            "role": "system",
                            "is_bridge": True,
                            "bridge_type": bridge.bridge_type.value,
                        }
                        final_content.append(bridge_content)

                # Step 7: Update LLM Request
                logger.info(f"[{agent_name}] Step 7: Updating request...")

                # Create mapping of content IDs to original content objects BEFORE the loop
                original_contents_map = {}
                for i, orig_content in enumerate(llm_request.contents):
                    content_id = f"content_{i}"  # This matches how IDs were created earlier
                    original_contents_map[content_id] = orig_content

                # Convert back to original format using direct ID lookup
                optimized_contents = []
                for item in final_content:
                    if not item.get("is_bridge", False):
                        # Use direct lookup by content ID to avoid ambiguity
                        item_id = item.get("id")
                        if item_id and item_id in original_contents_map:
                            optimized_contents.append(original_contents_map[item_id])
                        else:
                            logger.warning(
                                f"[{agent_name}] Could not find original content for ID: {item_id}"
                            )
                    else:
                        # Create bridge content in appropriate format
                        try:
                            # Try to create content in same format as original
                            if llm_request.contents:
                                sample_content = llm_request.contents[0]
                                if hasattr(sample_content, "__class__"):
                                    # Create new content object of same type
                                    bridge_obj = sample_content.__class__()
                                    if hasattr(bridge_obj, "text"):
                                        bridge_obj.text = item.get("text", "")
                                    if hasattr(bridge_obj, "role"):
                                        bridge_obj.role = "assistant"  # Bridge as assistant message
                                    optimized_contents.append(bridge_obj)
                        except Exception as e:
                            # Fallback: skip bridge if can't create compatible format, but
                            # log the error.
                            logger.warning(
                                f"[{agent_name}] Failed to create bridge content: {e}",
                                exc_info=True,
                            )

                # Update the request
                if optimized_contents:
                    llm_request.contents = optimized_contents
                    callback_context._token_optimization["optimization_applied"] = True
                    callback_context._token_optimization["final_content_count"] = len(
                        optimized_contents
                    )
                    callback_context._token_optimization["tokens_saved"] = (
                        assembly_result.total_tokens_used - bridging_result.total_bridge_tokens
                    )
                    callback_context._token_optimization["assembly_result"] = assembly_result
                    callback_context._token_optimization["bridging_result"] = bridging_result

                    logger.info(f"[{agent_name}] Advanced optimization complete:")
                    logger.info(
                        f"  - Content: {len(content_items)} → {len(optimized_contents)} items"
                    )
                    logger.info(
                        f"  - Dependencies: {len(correlation_result.references)} references found"
                    )
                    logger.info(f"  - Bridges: {len(bridging_result.bridges)} created")
                    logger.info(f"  - Strategy: {bridging_strategy.value}")
                    logger.info(
                        f"  - Budget utilization: {assembly_result.budget_utilization:.1f}%"
                    )
                else:
                    logger.warning(f"[{agent_name}] Advanced optimization produced no content")

            elif budget_breakdown["utilization_pct"] > 80.0:
                # Fallback to basic filtering for simple cases
                logger.info(f"[{agent_name}] Using fallback basic filtering")
                utilization_pct = budget_breakdown["utilization_pct"]
                strategy = (
                    FilterStrategy.AGGRESSIVE
                    if utilization_pct > 95
                    else FilterStrategy.MODERATE
                    if utilization_pct > 85
                    else FilterStrategy.CONSERVATIVE
                )

                filtering_policy = FilteringPolicy(strategy=strategy)
                filter_result = conversation_filter.filter_conversation(
                    contents=llm_request.contents,
                    target_token_budget=available_budget,
                    policy=filtering_policy,
                )

                if filter_result.filtering_applied:
                    llm_request.contents = filter_result.filtered_content
                    callback_context._token_optimization["optimization_applied"] = True
                    callback_context._token_optimization["pipeline_used"] = "basic"
                    callback_context._token_optimization["final_content_count"] = len(
                        filter_result.filtered_content
                    )
                    callback_context._token_optimization["tokens_saved"] = (
                        filter_result.tokens_saved
                    )

                    logger.info(f"[{agent_name}] Basic filtering applied: {strategy.value}")
            else:
                logger.info(
                    f"[{agent_name}] No optimization needed "
                    f"(utilization: {budget_breakdown['utilization_pct']:.1f}%)"
                )

        except Exception as e:
            logger.error(f"[{agent_name}] Advanced token optimization error: {e}", exc_info=True)
            # Continue without optimization if there's an error

    @_callback_error_handler(agent_name, "token_optimization_after_model")
    def token_optimization_after_model(
        callback_context: CallbackContext, llm_response: LlmResponse
    ):
        """Track token optimization effectiveness after model response."""

        # Track advanced token optimization effectiveness
        if callback_context and hasattr(callback_context, "_token_optimization"):
            optimization_data = callback_context._token_optimization

            invocation_id = (
                getattr(callback_context, "invocation_id", "unknown")
                if callback_context
                else "unknown"
            )

            # Calculate actual token usage from response
            actual_tokens_used = 0
            input_tokens_used = 0
            output_tokens_used = 0

            if (
                llm_response
                and hasattr(llm_response, "usage_metadata")
                and llm_response.usage_metadata
            ):
                usage = llm_response.usage_metadata
                actual_tokens_used = getattr(usage, "total_token_count", 0)
                input_tokens_used = getattr(usage, "prompt_token_count", 0)
                output_tokens_used = getattr(usage, "candidates_token_count", 0)

            logger.info(f"[{agent_name}] Advanced optimization summary - ID: {invocation_id}")
            logger.info(f"  Pipeline used: {optimization_data.get('pipeline_used', 'unknown')}")
            logger.info(f"  Budget allocated: {optimization_data['available_budget']:,}")
            logger.info(
                f"  Actual tokens used: {actual_tokens_used:,} "
                f"(input: {input_tokens_used:,}, output: {output_tokens_used:,})"
            )
            logger.info(f"  Optimization applied: {optimization_data['optimization_applied']}")

            # Report advanced optimization details
            if (
                optimization_data.get("pipeline_used") == "advanced"
                and optimization_data["optimization_applied"]
            ):
                original_count = optimization_data.get("original_content_count", 0)
                final_count = optimization_data.get("final_content_count", 0)
                steps_completed = optimization_data.get("steps_completed", [])
                dependencies_found = optimization_data.get("dependencies_found", 0)
                bridges_created = optimization_data.get("bridges_created", 0)
                tokens_saved = optimization_data.get("tokens_saved", 0)

                logger.info("  Advanced optimization results:")
                logger.info(f"    - Steps completed: {', '.join(steps_completed)}")
                logger.info(f"    - Content: {original_count} → {final_count} items")
                logger.info(f"    - Dependencies analyzed: {dependencies_found}")
                logger.info(f"    - Context bridges: {bridges_created}")
                logger.info(f"    - Estimated tokens saved: {tokens_saved:,}")

                # Detailed assembly results if available
                assembly_result = optimization_data.get("assembly_result")
                if assembly_result:
                    logger.info("    - Priority distribution:")
                    for priority, count in assembly_result.tokens_by_priority.items():
                        if count > 0:
                            logger.info(f"      {priority}: {count:,} tokens")

                # Detailed bridging results if available
                bridging_result = optimization_data.get("bridging_result")
                if bridging_result:
                    logger.info(f"    - Bridge tokens: {bridging_result.total_bridge_tokens}")
                    logger.info(f"    - Gaps filled: {bridging_result.gaps_filled}")
                    logger.info(f"    - Strategy used: {bridging_result.strategy_used.value}")

            elif (
                optimization_data.get("pipeline_used") == "basic"
                and optimization_data["optimization_applied"]
            ):
                original_count = optimization_data.get("original_content_count", 0)
                final_count = optimization_data.get("final_content_count", 0)
                tokens_saved = optimization_data.get("tokens_saved", 0)

                logger.info("  Basic filtering results:")
                logger.info(f"    - Content: {original_count} → {final_count} items")
                logger.info(f"    - Tokens saved: {tokens_saved:,}")

            # Calculate and report budget utilization
            if actual_tokens_used > 0 and optimization_data["available_budget"] > 0:
                budget_utilization = (
                    actual_tokens_used / optimization_data["available_budget"]
                ) * 100
                logger.info(f"  Final budget utilization: {budget_utilization:.1f}%")

                # Report efficiency metrics
                if input_tokens_used > 0:
                    input_efficiency = (
                        input_tokens_used / optimization_data["available_budget"]
                    ) * 100
                    logger.info(f"  Input token efficiency: {input_efficiency:.1f}% of budget used")

                # Check if optimization was effective
                if optimization_data["optimization_applied"]:
                    tokens_saved = optimization_data.get("tokens_saved", 0)
                    if tokens_saved > 0:
                        savings_pct = (tokens_saved / (actual_tokens_used + tokens_saved)) * 100
                        logger.info(f"  Token savings achieved: {savings_pct:.1f}%")

            # Log warnings for potential issues
            if actual_tokens_used > optimization_data["available_budget"]:
                overage = actual_tokens_used - optimization_data["available_budget"]
                logger.warning(
                    f"[{agent_name}] Token budget exceeded by {overage:,} tokens "
                    f"({(overage / optimization_data['available_budget']) * 100:.1f}%)"
                )

            if (
                not optimization_data["optimization_applied"]
                and optimization_data["available_budget"]
                < optimization_data["budget_breakdown"]["max_limit"] * 0.3
            ):
                logger.warning(
                    f"[{agent_name}] Low token budget with no optimization applied - "
                    f"consider adjusting thresholds or content"
                )

    @_callback_error_handler(agent_name, "token_optimization_before_tool")
    def token_optimization_before_tool(
        callback_context: CallbackContext, tool_context: ToolContext
    ):
        """Monitor tool usage for optimization insights."""
        # Track tool usage patterns for context prioritization
        if callback_context and hasattr(callback_context, "_token_optimization_session"):
            session_data = callback_context._token_optimization_session
            session_data.setdefault("tools_used", [])
            session_data["tools_used"].append(
                {
                    "tool_name": getattr(tool_context.tool, "name", "unknown"),
                    "timestamp": time.time(),
                }
            )

    @_callback_error_handler(agent_name, "token_optimization_after_tool")
    def token_optimization_after_tool(
        callback_context: CallbackContext, _tool_context: ToolContext, tool_response
    ):
        """Track tool execution for context prioritization."""
        # Track tool execution results for optimization
        if callback_context and hasattr(callback_context, "_token_optimization_session"):
            session_data = callback_context._token_optimization_session
            if session_data.get("tools_used"):
                # Update the most recent tool entry with execution status
                session_data["tools_used"][-1]["has_error"] = bool(
                    tool_response and isinstance(tool_response, dict) and tool_response.get("error")
                )

    # Create focused token optimization callback dictionary
    optimization_callbacks = {
        "before_agent": token_optimization_before_agent,
        "after_agent": token_optimization_after_agent,
        "before_model": token_optimization_before_model,
        "after_model": token_optimization_after_model,
        "before_tool": token_optimization_before_tool,
        "after_tool": token_optimization_after_tool,
    }

    logger.info(
        f"[{agent_name}] Token optimization callbacks created for model {resolved_model_name} "
        f"with {resolved_token_limit:,} token limit"
    )
    logger.info(
        f"[{agent_name}] Pipeline components: ContentPrioritizer, ContextCorrelator, "
        f"ContextAssembler, ContextBridgeBuilder"
    )

    return optimization_callbacks


# Backward compatibility alias for tests
def create_token_optimized_callbacks(
    agent_name: str,
    model_name: str,
    max_token_limit: int = 1_000_000,
    enhanced_telemetry: bool = True,  # Keep original parameter name for compatibility
) -> dict[str, Callable]:
    """
    Backward compatibility function for existing tests.

    This function redirects to create_token_optimization_callbacks
    and ignores the enhanced_telemetry parameter since we now use
    single-purpose callbacks that work alongside telemetry callbacks.
    """
    # Ignore enhanced_telemetry parameter (mark as unused with _ in body)
    _ = enhanced_telemetry

    return create_token_optimization_callbacks(
        agent_name=agent_name, model_name=model_name, max_token_limit=max_token_limit
    )


def create_retry_callbacks(
    agent_name: str,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 8.0,
    backoff_multiplier: float = 2.0,
) -> dict[str, Callable]:
    """
    Create retry callbacks with exponential backoff for model request failures.

    This specifically handles the "No message in response" error from LiteLLM
    by implementing automatic retry logic with exponential backoff.

    Args:
        agent_name: Name of the agent for logging
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay between retries (default: 8.0)
        backoff_multiplier: Multiplier for exponential backoff (default: 2.0)

    Returns:
        Dictionary containing retry-enabled callback functions and retry handler
    """
    import asyncio
    import random

    # Validate parameters
    if max_retries < 0:
        raise ValueError(f"max_retries must be non-negative, got {max_retries}")
    if base_delay <= 0:
        raise ValueError(f"base_delay must be positive, got {base_delay}")
    if max_delay <= 0:
        raise ValueError(f"max_delay must be positive, got {max_delay}")
    if backoff_multiplier <= 0:
        raise ValueError(f"backoff_multiplier must be positive, got {backoff_multiplier}")

    logger.info(
        f"[{agent_name}] Creating retry callbacks with max_retries={max_retries}, "
        f"base_delay={base_delay}s, max_delay={max_delay}s"
    )

    @_callback_error_handler(agent_name, "retry_before_model_callback")
    def before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest):
        """Log model request initiation."""
        del callback_context, llm_request  # Unused but required by callback signature
        logger.debug(f"[{agent_name}] Model request initiated (retry system active)")

    @_callback_error_handler(agent_name, "retry_after_model_callback")
    def after_model_callback(callback_context: CallbackContext, llm_response: LlmResponse):
        """Log successful model response."""
        del callback_context, llm_response  # Unused but required by callback signature
        logger.debug(f"[{agent_name}] Model request completed successfully")

    def create_retry_handler():
        """Create a retry handler that can be used by agents to wrap model calls."""

        async def handle_model_request_with_retry(model_call_func, *args, **kwargs):
            """
            Wrapper function that handles model requests with automatic retry logic.

            Args:
                model_call_func: The original model call function to retry
                *args, **kwargs: Arguments to pass to the model call function

            Returns:
                The result of the successful model call

            Raises:
                The last error if all retries are exhausted
            """
            last_error = None

            for attempt in range(max_retries + 1):  # +1 for initial attempt
                try:
                    # Attempt the model call
                    if asyncio.iscoroutinefunction(model_call_func):
                        result = await model_call_func(*args, **kwargs)
                    else:
                        result = model_call_func(*args, **kwargs)

                    if attempt > 0:
                        logger.info(
                            f"[{agent_name}] Model request succeeded on attempt {attempt + 1}"
                        )
                    return result

                except ValueError as e:
                    error_msg = str(e)

                    # Only retry for "No message in response" errors
                    if "No message in response" not in error_msg:
                        logger.debug(f"[{agent_name}] Non-retryable ValueError: {error_msg}")
                        raise

                    last_error = e

                    # Don't retry if we've exhausted attempts
                    if attempt >= max_retries:
                        logger.error(
                            f"[{agent_name}] Model request failed after "
                            f"{max_retries + 1} attempts. Final error: {error_msg}"
                        )
                        break

                    # Calculate delay with exponential backoff and jitter
                    delay = min(base_delay * (backoff_multiplier**attempt), max_delay)
                    # Add jitter to prevent thundering herd
                    jitter_multiplier = 0.8 + (0.4 * random.random())  # Jitter of ±20%
                    total_delay = delay * jitter_multiplier

                    logger.warning(
                        f"[{agent_name}] Model request failed "
                        f"(attempt {attempt + 1}/{max_retries + 1}): {error_msg}. "
                        f"Retrying in {total_delay:.2f}s..."
                    )

                    # Wait before retry
                    await asyncio.sleep(total_delay)

                except Exception as e:
                    # Don't retry for other types of errors
                    logger.debug(
                        f"[{agent_name}] Non-retryable error in model request: "
                        f"{type(e).__name__}: {e}"
                    )
                    raise

            # If we get here, all retries failed
            raise last_error

        return handle_model_request_with_retry

    # Create the retry handler for use by agents
    retry_handler = create_retry_handler()

    return {
        "before_model": before_model_callback,
        "after_model": after_model_callback,
        "retry_handler": retry_handler,
    }
