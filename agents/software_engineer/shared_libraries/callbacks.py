"""Shared callback utilities for Software Engineer Agent."""

import logging
import os
import time
from typing import Any, Dict, Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


def _load_project_context(
    callback_context: CallbackContext = None,
) -> Optional[Dict[str, Any]]:
    """
    Load project context information for the agent session.

    Args:
        callback_context: The ADK callback context

    Returns:
        Dictionary containing project context information
    """
    try:
        # Get current working directory
        current_dir = os.getcwd()

        # Detect project type
        project_files = os.listdir(current_dir) if os.path.exists(current_dir) else []
        if "pyproject.toml" in project_files:
            project_type = "python"
        elif "package.json" in project_files:
            project_type = "javascript"
        elif "Cargo.toml" in project_files:
            project_type = "rust"
        elif "go.mod" in project_files:
            project_type = "go"
        else:
            project_type = "unknown"

        # Get basic project statistics
        total_files = len(project_files)
        python_files = len([f for f in project_files if f.endswith(".py")])
        js_files = len(
            [f for f in project_files if f.endswith(".js") or f.endswith(".ts")]
        )

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

    except Exception as e:
        logger.error(f"Error loading project context: {e}")
        return None


def create_telemetry_callbacks(agent_name: str):
    """
    Create telemetry and tracing callbacks for an agent.

    Args:
        agent_name: Name of the agent for logging and metrics

    Returns:
        Dictionary containing callback functions with keys:
        - before_model: Callback executed before LLM model request
        - after_model: Callback executed after LLM model response
        - before_tool: Callback executed before tool execution
        - after_tool: Callback executed after tool execution
        - before_agent: Callback executed before agent starts processing
        - after_agent: Callback executed after agent completes processing
    """

    def before_agent_callback(callback_context: CallbackContext = None):
        """Callback executed before agent starts processing."""
        try:
            session_id = (
                getattr(callback_context, "session_id", "unknown")
                if callback_context and hasattr(callback_context, "session_id")
                else "unknown"
            )
            logger.info(
                f"[{agent_name}] Agent session started - Session ID: {session_id}"
            )

            # Track agent session start time
            if callback_context:
                callback_context._agent_session_start_time = time.time()

            # Load project context information
            project_context = _load_project_context(callback_context)
            if project_context:
                logger.info(f"[{agent_name}] Project context loaded: {project_context}")

            # Initialize session-level metrics
            if callback_context:
                callback_context._agent_metrics = {
                    "session_start_time": time.time(),
                    "total_model_calls": 0,
                    "total_tool_calls": 0,
                    "total_tokens_used": 0,
                    "errors_encountered": 0,
                    "project_context": project_context,
                }

            # Track agent lifecycle event
            logger.info(f"[{agent_name}] Agent lifecycle: SESSION_START")

        except Exception as e:
            logger.warning(f"[{agent_name}] Error in before_agent_callback: {e}")

    def after_agent_callback(callback_context: CallbackContext = None):
        """Callback executed after agent completes processing."""
        try:
            session_id = (
                getattr(callback_context, "session_id", "unknown")
                if callback_context and hasattr(callback_context, "session_id")
                else "unknown"
            )
            logger.info(
                f"[{agent_name}] Agent session ended - Session ID: {session_id}"
            )

            # Calculate total session duration
            if callback_context and hasattr(
                callback_context, "_agent_session_start_time"
            ):
                session_duration = (
                    time.time() - callback_context._agent_session_start_time
                )
                logger.info(
                    f"[{agent_name}] Total session duration: {session_duration:.2f}s"
                )

            # Log session summary metrics
            if callback_context and hasattr(callback_context, "_agent_metrics"):
                metrics = callback_context._agent_metrics
                logger.info(f"[{agent_name}] Session summary:")
                logger.info(
                    f"  Total model calls: {metrics.get('total_model_calls', 0)}"
                )
                logger.info(f"  Total tool calls: {metrics.get('total_tool_calls', 0)}")
                logger.info(
                    f"  Total tokens used: {metrics.get('total_tokens_used', 0)}"
                )
                logger.info(
                    f"  Errors encountered: {metrics.get('errors_encountered', 0)}"
                )
                if metrics.get("project_context"):
                    logger.info(
                        f"  Project type: {metrics['project_context'].get('project_type', 'unknown')}"
                    )

            # Perform any cleanup operations
            logger.info(f"[{agent_name}] Session cleanup completed")

            # Track agent lifecycle event
            logger.info(f"[{agent_name}] Agent lifecycle: SESSION_END")

        except Exception as e:
            logger.warning(f"[{agent_name}] Error in after_agent_callback: {e}")

    def before_model_callback(
        callback_context: CallbackContext, llm_request: LlmRequest
    ):
        """Callback executed before LLM model request."""
        try:
            invocation_id = (
                getattr(callback_context, "invocation_id", "unknown")
                if callback_context
                else "unknown"
            )
            logger.debug(f"[{agent_name}] Before model request - ID: {invocation_id}")

            # Update session metrics
            if callback_context and hasattr(callback_context, "_agent_metrics"):
                callback_context._agent_metrics["total_model_calls"] += 1

            # Basic logging of request details
            if (
                llm_request
                and hasattr(llm_request, "contents")
                and llm_request.contents
            ):
                content_preview = (
                    str(llm_request.contents)[:100] + "..."
                    if len(str(llm_request.contents)) > 100
                    else str(llm_request.contents)
                )
                logger.debug(
                    f"[{agent_name}] Request content preview: {content_preview}"
                )

            # Track request timing
            if callback_context and not hasattr(
                callback_context, "_request_start_time"
            ):
                callback_context._request_start_time = time.time()

            # Optional: Add any SWE-specific pre-processing here
            # For example, context filtering, prompt augmentation, etc.
        except Exception as e:
            logger.warning(f"[{agent_name}] Error in before_model_callback: {e}")

    def after_model_callback(
        callback_context: CallbackContext, llm_response: LlmResponse
    ):
        """Callback executed after LLM model response."""
        try:
            invocation_id = (
                getattr(callback_context, "invocation_id", "unknown")
                if callback_context
                else "unknown"
            )
            logger.debug(f"[{agent_name}] After model response - ID: {invocation_id}")

            # Calculate response time
            if callback_context and hasattr(callback_context, "_request_start_time"):
                response_time = time.time() - callback_context._request_start_time
                logger.debug(f"[{agent_name}] Response time: {response_time:.2f}s")

            # Basic logging of response details
            if llm_response and hasattr(llm_response, "text") and llm_response.text:
                response_preview = (
                    llm_response.text[:100] + "..."
                    if len(llm_response.text) > 100
                    else llm_response.text
                )
                logger.debug(f"[{agent_name}] Response preview: {response_preview}")

            # Track token usage if available
            if (
                llm_response
                and hasattr(llm_response, "usage_metadata")
                and llm_response.usage_metadata
            ):
                usage = llm_response.usage_metadata
                if hasattr(usage, "prompt_token_count") and hasattr(
                    usage, "candidates_token_count"
                ):
                    total_tokens = (
                        usage.prompt_token_count + usage.candidates_token_count
                    )
                    logger.info(
                        f"[{agent_name}] Token usage - Prompt: {usage.prompt_token_count}, Response: {usage.candidates_token_count}, Total: {total_tokens}"
                    )

                    # Update session metrics
                    if callback_context and hasattr(callback_context, "_agent_metrics"):
                        callback_context._agent_metrics["total_tokens_used"] += (
                            total_tokens
                        )

            # Optional: Add any SWE-specific post-processing here
            # For example, response validation, state updates, etc.
        except Exception as e:
            logger.warning(f"[{agent_name}] Error in after_model_callback: {e}")

    def before_tool_callback(
        tool: BaseTool,
        args: dict,
        tool_context: ToolContext,
        callback_context: CallbackContext = None,
    ):
        """Callback executed before tool execution."""
        try:
            tool_name = getattr(tool, "name", "unknown") if tool else "unknown"
            invocation_id = (
                getattr(callback_context, "invocation_id", "unknown")
                if callback_context
                else "unknown"
            )
            logger.debug(
                f"[{agent_name}] Before tool execution - Tool: {tool_name}, ID: {invocation_id}"
            )

            # Update session metrics
            if callback_context and hasattr(callback_context, "_agent_metrics"):
                callback_context._agent_metrics["total_tool_calls"] += 1

            # Track tool execution timing
            if callback_context and not hasattr(callback_context, "_tool_start_time"):
                callback_context._tool_start_time = time.time()

            # Log tool input if available
            if args:
                input_preview = (
                    str(args)[:200] + "..." if len(str(args)) > 200 else str(args)
                )
                logger.debug(f"[{agent_name}] Tool input preview: {input_preview}")

            # Optional: Add any SWE-specific pre-tool processing here
            # For example, input validation, context preparation, etc.
        except Exception as e:
            logger.warning(f"[{agent_name}] Error in before_tool_callback: {e}")

    def after_tool_callback(
        tool: BaseTool,
        tool_response: Any,
        callback_context: CallbackContext = None,
        args: dict = None,
        tool_context: ToolContext = None,
    ):
        """Callback executed after tool execution."""
        try:
            tool_name = getattr(tool, "name", "unknown") if tool else "unknown"
            invocation_id = (
                getattr(callback_context, "invocation_id", "unknown")
                if callback_context
                else "unknown"
            )
            logger.debug(
                f"[{agent_name}] After tool execution - Tool: {tool_name}, ID: {invocation_id}"
            )

            # Calculate tool execution time
            if callback_context and hasattr(callback_context, "_tool_start_time"):
                execution_time = time.time() - callback_context._tool_start_time
                logger.debug(
                    f"[{agent_name}] Tool execution time: {execution_time:.2f}s"
                )

            # Log tool result
            if tool_response is not None:
                result_preview = (
                    str(tool_response)[:200] + "..."
                    if len(str(tool_response)) > 200
                    else str(tool_response)
                )
                logger.debug(f"[{agent_name}] Tool result preview: {result_preview}")

            # Track tool success/failure
            if isinstance(tool_response, Exception):
                logger.warning(
                    f"[{agent_name}] Tool {tool_name} failed: {tool_response}"
                )
                # Update error metrics
                if callback_context and hasattr(callback_context, "_agent_metrics"):
                    callback_context._agent_metrics["errors_encountered"] += 1
            else:
                logger.debug(f"[{agent_name}] Tool {tool_name} completed successfully")

            # Optional: Add any SWE-specific post-tool processing here
            # For example, result validation, context updates, error handling, etc.
        except Exception as e:
            logger.warning(f"[{agent_name}] Error in after_tool_callback: {e}")

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
    Create enhanced telemetry callbacks that attempt to use DevOps agent's telemetry if available.

    Args:
        agent_name: Name of the agent for logging and metrics

    Returns:
        Dictionary containing callback functions with keys:
        - before_model: Callback executed before LLM model request
        - after_model: Callback executed after LLM model response
        - before_tool: Callback executed before tool execution
        - after_tool: Callback executed after tool execution
        - before_agent: Callback executed before agent starts processing
        - after_agent: Callback executed after agent completes processing
    """

    # Try to import DevOps telemetry and tracing
    try:
        from ...devops.telemetry import (
            OperationType,
            track_llm_request,
            track_tool_execution,
        )
        from ...devops.tracing import trace_llm_request, trace_tool_execution

        telemetry_available = True
        logger.info(
            f"[{agent_name}] Enhanced telemetry available - using DevOps agent telemetry"
        )
    except ImportError:
        telemetry_available = False
        logger.info(
            f"[{agent_name}] Enhanced telemetry not available - using basic callbacks"
        )
        return create_telemetry_callbacks(agent_name)

    def before_agent_callback(callback_context: CallbackContext = None):
        """Enhanced callback with telemetry before agent starts processing."""
        try:
            session_id = (
                getattr(callback_context, "session_id", "unknown")
                if callback_context and hasattr(callback_context, "session_id")
                else "unknown"
            )
            logger.info(
                f"[{agent_name}] Enhanced agent session started - Session ID: {session_id}"
            )

            # Track agent session start time
            if callback_context:
                callback_context._agent_session_start_time = time.time()

            # Load project context information
            project_context = _load_project_context(callback_context)
            if project_context:
                logger.info(f"[{agent_name}] Project context loaded: {project_context}")

            # Initialize enhanced session-level metrics
            if callback_context:
                callback_context._agent_metrics = {
                    "session_start_time": time.time(),
                    "total_model_calls": 0,
                    "total_tool_calls": 0,
                    "total_tokens_used": 0,
                    "errors_encountered": 0,
                    "project_context": project_context,
                    "agent_name": agent_name,
                    "session_id": session_id,
                }

            # Enhanced telemetry tracking
            if telemetry_available:
                try:
                    # Track agent session start
                    logger.info(
                        f"[{agent_name}] Enhanced telemetry session tracking enabled"
                    )
                except Exception as e:
                    logger.warning(
                        f"[{agent_name}] Failed to track agent session start: {e}"
                    )

            # Track agent lifecycle event
            logger.info(f"[{agent_name}] Agent lifecycle: ENHANCED_SESSION_START")

        except Exception as e:
            logger.warning(
                f"[{agent_name}] Error in enhanced before_agent_callback: {e}"
            )

    def after_agent_callback(callback_context: CallbackContext = None):
        """Enhanced callback with telemetry after agent completes processing."""
        try:
            session_id = (
                getattr(callback_context, "session_id", "unknown")
                if callback_context and hasattr(callback_context, "session_id")
                else "unknown"
            )
            logger.info(
                f"[{agent_name}] Enhanced agent session ended - Session ID: {session_id}"
            )

            # Calculate total session duration
            if callback_context and hasattr(
                callback_context, "_agent_session_start_time"
            ):
                session_duration = (
                    time.time() - callback_context._agent_session_start_time
                )
                logger.info(
                    f"[{agent_name}] Total session duration: {session_duration:.2f}s"
                )

            # Log enhanced session summary metrics
            if callback_context and hasattr(callback_context, "_agent_metrics"):
                metrics = callback_context._agent_metrics
                logger.info(f"[{agent_name}] Enhanced session summary:")
                logger.info(f"  Agent: {metrics.get('agent_name', 'unknown')}")
                logger.info(f"  Session ID: {metrics.get('session_id', 'unknown')}")
                logger.info(
                    f"  Total model calls: {metrics.get('total_model_calls', 0)}"
                )
                logger.info(f"  Total tool calls: {metrics.get('total_tool_calls', 0)}")
                logger.info(
                    f"  Total tokens used: {metrics.get('total_tokens_used', 0)}"
                )
                logger.info(
                    f"  Errors encountered: {metrics.get('errors_encountered', 0)}"
                )
                if metrics.get("project_context"):
                    pc = metrics["project_context"]
                    logger.info(f"  Project type: {pc.get('project_type', 'unknown')}")
                    logger.info(f"  Project files: {pc.get('total_files', 0)}")

            # Enhanced telemetry tracking
            if telemetry_available:
                try:
                    # Track agent session end with metrics
                    logger.info(
                        f"[{agent_name}] Enhanced telemetry session tracking completed"
                    )
                except Exception as e:
                    logger.warning(
                        f"[{agent_name}] Failed to track agent session end: {e}"
                    )

            # Perform any cleanup operations
            logger.info(f"[{agent_name}] Enhanced session cleanup completed")

            # Track agent lifecycle event
            logger.info(f"[{agent_name}] Agent lifecycle: ENHANCED_SESSION_END")

        except Exception as e:
            logger.warning(
                f"[{agent_name}] Error in enhanced after_agent_callback: {e}"
            )

    def before_model_callback(
        callback_context: CallbackContext, llm_request: LlmRequest
    ):
        """Enhanced callback with telemetry before LLM model request."""
        try:
            invocation_id = (
                getattr(callback_context, "invocation_id", "unknown")
                if callback_context
                else "unknown"
            )
            logger.debug(f"[{agent_name}] Before model request - ID: {invocation_id}")

            # Update session metrics
            if callback_context and hasattr(callback_context, "_agent_metrics"):
                callback_context._agent_metrics["total_model_calls"] += 1

            # Basic logging
            if (
                llm_request
                and hasattr(llm_request, "contents")
                and llm_request.contents
            ):
                content_preview = (
                    str(llm_request.contents)[:100] + "..."
                    if len(str(llm_request.contents)) > 100
                    else str(llm_request.contents)
                )
                logger.debug(
                    f"[{agent_name}] Request content preview: {content_preview}"
                )

            # Track request timing
            if callback_context:
                callback_context._request_start_time = time.time()
                callback_context._model_name = getattr(llm_request, "model", "unknown")

            # Enhanced telemetry tracking
            if telemetry_available:
                try:
                    # Note: We'll track the response in after_model_callback since we need response data
                    pass
                except Exception as e:
                    logger.warning(f"[{agent_name}] Failed to track LLM request: {e}")
        except Exception as e:
            logger.warning(
                f"[{agent_name}] Error in enhanced before_model_callback: {e}"
            )

    def after_model_callback(
        callback_context: CallbackContext, llm_response: LlmResponse
    ):
        """Enhanced callback with telemetry after LLM model response."""
        invocation_id = (
            getattr(callback_context, "invocation_id", "unknown")
            if callback_context
            else "unknown"
        )
        logger.debug(f"[{agent_name}] After model response - ID: {invocation_id}")

        # Calculate response time
        response_time = 0.0
        if callback_context and hasattr(callback_context, "_request_start_time"):
            response_time = time.time() - callback_context._request_start_time
            logger.debug(f"[{agent_name}] Response time: {response_time:.2f}s")

        # Basic logging
        if hasattr(llm_response, "text") and llm_response.text:
            response_preview = (
                llm_response.text[:100] + "..."
                if len(llm_response.text) > 100
                else llm_response.text
            )
            logger.debug(f"[{agent_name}] Response preview: {response_preview}")

        # Enhanced telemetry tracking
        if telemetry_available:
            try:
                # Extract token usage
                prompt_tokens = 0
                completion_tokens = 0
                total_tokens = 0

                if (
                    hasattr(llm_response, "usage_metadata")
                    and llm_response.usage_metadata
                ):
                    usage = llm_response.usage_metadata
                    if hasattr(usage, "prompt_token_count"):
                        prompt_tokens = usage.prompt_token_count
                    if hasattr(usage, "candidates_token_count"):
                        completion_tokens = usage.candidates_token_count
                    total_tokens = prompt_tokens + completion_tokens

                # Update session metrics
                if callback_context and hasattr(callback_context, "_agent_metrics"):
                    callback_context._agent_metrics["total_tokens_used"] += total_tokens

                # Track LLM request with telemetry (model name not available in response)
                model_name = getattr(callback_context, "_model_name", "unknown")
                track_llm_request(
                    model=model_name,
                    tokens_used=total_tokens,
                    response_time=response_time,
                    prompt_tokens=prompt_tokens,
                )

                logger.info(
                    f"[{agent_name}] Token usage - Prompt: {prompt_tokens}, Response: {completion_tokens}, Total: {total_tokens}"
                )

            except Exception as e:
                logger.warning(f"[{agent_name}] Failed to track LLM response: {e}")

    def before_tool_callback(
        tool: BaseTool,
        args: dict,
        tool_context: ToolContext,
        callback_context: CallbackContext = None,
    ):
        """Enhanced callback with telemetry before tool execution."""
        tool_name = getattr(tool, "name", "unknown") if tool else "unknown"
        invocation_id = (
            getattr(callback_context, "invocation_id", "unknown")
            if callback_context
            else "unknown"
        )
        logger.debug(
            f"[{agent_name}] Before tool execution - Tool: {tool_name}, ID: {invocation_id}"
        )

        # Update session metrics
        if callback_context and hasattr(callback_context, "_agent_metrics"):
            callback_context._agent_metrics["total_tool_calls"] += 1

        # Track tool execution timing
        if callback_context:
            callback_context._tool_start_time = time.time()

        # Log tool input
        if args:
            input_preview = (
                str(args)[:200] + "..." if len(str(args)) > 200 else str(args)
            )
            logger.debug(f"[{agent_name}] Tool input preview: {input_preview}")

    def after_tool_callback(
        tool: BaseTool,
        tool_response: Any,
        callback_context: CallbackContext = None,
        args: dict = None,
        tool_context: ToolContext = None,
    ):
        """Enhanced callback with telemetry after tool execution."""
        tool_name = getattr(tool, "name", "unknown") if tool else "unknown"
        invocation_id = (
            getattr(callback_context, "invocation_id", "unknown")
            if callback_context
            else "unknown"
        )
        logger.debug(
            f"[{agent_name}] After tool execution - Tool: {tool_name}, ID: {invocation_id}"
        )

        # Calculate tool execution time
        execution_time = 0.0
        if callback_context and hasattr(callback_context, "_tool_start_time"):
            execution_time = time.time() - callback_context._tool_start_time
            logger.debug(f"[{agent_name}] Tool execution time: {execution_time:.2f}s")

        # Log tool result
        if tool_response is not None:
            result_preview = (
                str(tool_response)[:200] + "..."
                if len(str(tool_response)) > 200
                else str(tool_response)
            )
            logger.debug(f"[{agent_name}] Tool result preview: {result_preview}")

        # Track success/failure
        success = not isinstance(tool_response, Exception)
        if not success:
            logger.warning(f"[{agent_name}] Tool {tool_name} failed: {tool_response}")
            # Update error metrics
            if callback_context and hasattr(callback_context, "_agent_metrics"):
                callback_context._agent_metrics["errors_encountered"] += 1
        else:
            logger.debug(f"[{agent_name}] Tool {tool_name} completed successfully")

        # Enhanced telemetry tracking
        if telemetry_available:
            try:
                # Note: The current track_tool_execution is a decorator, so we'll use a simpler approach
                # We could enhance this further by implementing proper tool execution tracking
                pass
            except Exception as e:
                logger.warning(f"[{agent_name}] Failed to track tool execution: {e}")

    return {
        "before_agent": before_agent_callback,
        "after_agent": after_agent_callback,
        "before_model": before_model_callback,
        "after_model": after_model_callback,
        "before_tool": before_tool_callback,
        "after_tool": after_tool_callback,
    }
