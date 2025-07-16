"""Shared callback utilities for Software Engineer Agent."""

import logging
from typing import Any, Optional

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

    def before_model_callback(llm_request: LlmRequest, context: InvocationContext):
        """Callback executed before LLM model request."""
        try:
            invocation_id = (
                getattr(context, "invocation_id", "unknown") if context else "unknown"
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
            if context and not hasattr(context, "_request_start_time"):
                context._request_start_time = __import__("time").time()

            # Optional: Add any SWE-specific pre-processing here
            # For example, context filtering, prompt augmentation, etc.
        except Exception as e:
            logger.warning(f"[{agent_name}] Error in before_model_callback: {e}")

    def after_model_callback(
        llm_request: LlmRequest, llm_response: LlmResponse, context: InvocationContext
    ):
        """Callback executed after LLM model response."""
        try:
            invocation_id = (
                getattr(context, "invocation_id", "unknown") if context else "unknown"
            )
            logger.debug(f"[{agent_name}] After model response - ID: {invocation_id}")

            # Calculate response time
            if context and hasattr(context, "_request_start_time"):
                response_time = __import__("time").time() - context._request_start_time
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

    def before_tool_callback(tool: BaseTool, context: ToolContext):
        """Callback executed before tool execution."""
        try:
            tool_name = getattr(tool, "name", "unknown") if tool else "unknown"
            invocation_id = (
                getattr(context, "invocation_id", "unknown") if context else "unknown"
            )
            logger.debug(
                f"[{agent_name}] Before tool execution - Tool: {tool_name}, ID: {invocation_id}"
            )

            # Track tool execution timing
            if context and not hasattr(context, "_tool_start_time"):
                context._tool_start_time = __import__("time").time()

            # Log tool input if available
            if context and hasattr(context, "tool_input") and context.tool_input:
                input_preview = (
                    str(context.tool_input)[:200] + "..."
                    if len(str(context.tool_input)) > 200
                    else str(context.tool_input)
                )
                logger.debug(f"[{agent_name}] Tool input preview: {input_preview}")

            # Optional: Add any SWE-specific pre-tool processing here
            # For example, input validation, context preparation, etc.
        except Exception as e:
            logger.warning(f"[{agent_name}] Error in before_tool_callback: {e}")

    def after_tool_callback(tool: BaseTool, result: Any, context: ToolContext):
        """Callback executed after tool execution."""
        try:
            tool_name = getattr(tool, "name", "unknown") if tool else "unknown"
            invocation_id = (
                getattr(context, "invocation_id", "unknown") if context else "unknown"
            )
            logger.debug(
                f"[{agent_name}] After tool execution - Tool: {tool_name}, ID: {invocation_id}"
            )

            # Calculate tool execution time
            if context and hasattr(context, "_tool_start_time"):
                execution_time = __import__("time").time() - context._tool_start_time
                logger.debug(
                    f"[{agent_name}] Tool execution time: {execution_time:.2f}s"
                )

            # Log tool result
            if result is not None:
                result_preview = (
                    str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
                )
                logger.debug(f"[{agent_name}] Tool result preview: {result_preview}")

            # Track tool success/failure
            if isinstance(result, Exception):
                logger.warning(f"[{agent_name}] Tool {tool_name} failed: {result}")
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

    def before_model_callback(llm_request: LlmRequest, context: InvocationContext):
        """Enhanced callback with telemetry before LLM model request."""
        try:
            invocation_id = (
                getattr(context, "invocation_id", "unknown") if context else "unknown"
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
            if context:
                context._request_start_time = __import__("time").time()

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
        llm_request: LlmRequest, llm_response: LlmResponse, context: InvocationContext
    ):
        """Enhanced callback with telemetry after LLM model response."""
        logger.debug(
            f"[{agent_name}] After model response - ID: {context.invocation_id}"
        )

        # Calculate response time
        response_time = 0.0
        if hasattr(context, "_request_start_time"):
            response_time = __import__("time").time() - context._request_start_time
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

                # Track LLM request with telemetry
                model_name = getattr(llm_request, "model", "unknown")
                track_llm_request(
                    model=model_name,
                    tokens_used=total_tokens,
                    response_time=response_time,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )

                logger.info(
                    f"[{agent_name}] Token usage - Prompt: {prompt_tokens}, Response: {completion_tokens}, Total: {total_tokens}"
                )

            except Exception as e:
                logger.warning(f"[{agent_name}] Failed to track LLM response: {e}")

    def before_tool_callback(tool: BaseTool, context: ToolContext):
        """Enhanced callback with telemetry before tool execution."""
        logger.debug(
            f"[{agent_name}] Before tool execution - Tool: {tool.name}, ID: {getattr(context, 'invocation_id', 'unknown')}"
        )

        # Track tool execution timing
        context._tool_start_time = __import__("time").time()

        # Log tool input
        if hasattr(context, "tool_input") and context.tool_input:
            input_preview = (
                str(context.tool_input)[:200] + "..."
                if len(str(context.tool_input)) > 200
                else str(context.tool_input)
            )
            logger.debug(f"[{agent_name}] Tool input preview: {input_preview}")

    def after_tool_callback(tool: BaseTool, result: Any, context: ToolContext):
        """Enhanced callback with telemetry after tool execution."""
        logger.debug(
            f"[{agent_name}] After tool execution - Tool: {tool.name}, ID: {getattr(context, 'invocation_id', 'unknown')}"
        )

        # Calculate tool execution time
        execution_time = 0.0
        if hasattr(context, "_tool_start_time"):
            execution_time = __import__("time").time() - context._tool_start_time
            logger.debug(f"[{agent_name}] Tool execution time: {execution_time:.2f}s")

        # Log tool result
        if result is not None:
            result_preview = (
                str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
            )
            logger.debug(f"[{agent_name}] Tool result preview: {result_preview}")

        # Track success/failure
        success = not isinstance(result, Exception)
        if not success:
            logger.warning(f"[{agent_name}] Tool {tool.name} failed: {result}")
        else:
            logger.debug(f"[{agent_name}] Tool {tool.name} completed successfully")

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
