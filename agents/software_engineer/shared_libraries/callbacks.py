"""Shared callback utilities for Software Engineer Agent."""

import logging
from typing import Any, Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


def create_telemetry_callbacks(agent_name: str):
    """
    Create telemetry and tracing callbacks for an agent.

    Args:
        agent_name: Name of the agent for logging and metrics

    Returns:
        Tuple of (before_model_callback, after_model_callback, before_tool_callback, after_tool_callback)
    """

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
                callback_context._request_start_time = __import__("time").time()

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
                response_time = (
                    __import__("time").time() - callback_context._request_start_time
                )
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

            # Track tool execution timing
            if callback_context and not hasattr(callback_context, "_tool_start_time"):
                callback_context._tool_start_time = __import__("time").time()

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
                execution_time = (
                    __import__("time").time() - callback_context._tool_start_time
                )
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
            else:
                logger.debug(f"[{agent_name}] Tool {tool_name} completed successfully")

            # Optional: Add any SWE-specific post-tool processing here
            # For example, result validation, context updates, error handling, etc.
        except Exception as e:
            logger.warning(f"[{agent_name}] Error in after_tool_callback: {e}")

    return (
        before_model_callback,
        after_model_callback,
        before_tool_callback,
        after_tool_callback,
    )


def create_enhanced_telemetry_callbacks(agent_name: str):
    """
    Create enhanced telemetry callbacks that attempt to use DevOps agent's telemetry if available.

    Args:
        agent_name: Name of the agent for logging and metrics

    Returns:
        Tuple of (before_model_callback, after_model_callback, before_tool_callback, after_tool_callback)
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
                callback_context._request_start_time = __import__("time").time()

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
            response_time = (
                __import__("time").time() - callback_context._request_start_time
            )
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

        # Track tool execution timing
        if callback_context:
            callback_context._tool_start_time = __import__("time").time()

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
            execution_time = (
                __import__("time").time() - callback_context._tool_start_time
            )
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

    return (
        before_model_callback,
        after_model_callback,
        before_tool_callback,
        after_tool_callback,
    )
