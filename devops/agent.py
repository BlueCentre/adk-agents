"""DevOps Agent Implementation."""

import logging
import traceback # For logging stack traces
import time
import json 
import os

from google.adk.agents.llm_agent import LlmAgent
from google.genai import types as genai_types 
from google import genai # Changed from google.generativeai to google
from typing_extensions import override
from typing import AsyncGenerator, Optional, Any

from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool 
from google.adk.tools.tool_context import ToolContext 
from google.adk.agents.callback_context import CallbackContext
from google.adk.events.event import Event, EventActions 
from google.adk.agents.invocation_context import InvocationContext

from rich.console import Console
from rich.status import Status

from pydantic import PrivateAttr

from . import config as agent_config
from .tools.setup import load_core_tools_and_toolsets
from .components.planning_manager import PlanningManager 
from .components.context_management import (
    ContextManager,
    TOOL_PROCESSORS, 
    get_last_user_content,
    inject_structured_context,
)
from .tools.shell_command import ExecuteVettedShellCommandOutput 
from .utils import ui as ui_utils
from . import prompts as agent_prompts

logger = logging.getLogger(__name__)

try:
    from mcp import types as mcp_types
except ImportError:
    logger.warning("mcp.types not found, Playwright tool responses might not be fully processed if they are CallToolResult.")
    mcp_types = None 

devops_core_tools = load_core_tools_and_toolsets()

class MyDevopsAgent(LlmAgent):
    _console: Console = PrivateAttr(default_factory=lambda: Console(stderr=True))
    _status_indicator: Optional[Status] = PrivateAttr(default=None)
    _context_manager: Optional[ContextManager] = PrivateAttr(default=None)
    _is_new_conversation: bool = PrivateAttr(default=True)
    _planning_manager: Optional[PlanningManager] = PrivateAttr(default=None)
    _actual_llm_token_limit: int = PrivateAttr(default=agent_config.DEFAULT_TOKEN_LIMIT_FALLBACK)
    llm_client: Optional[genai.Client] = None  # Add llm_client as a proper field

    def __init__(self, **data: any):
        super().__init__(**data)
        # Check if llm_client is provided in data
        if 'llm_client' in data:
            self.llm_client = data.pop('llm_client')
            logger.info(f"Using provided llm_client in __init__: {type(self.llm_client).__name__}")
        
        self.before_model_callback = self.handle_before_model
        self.after_model_callback = self.handle_after_model
        self.before_tool_callback = self.handle_before_tool
        self.after_tool_callback = self.handle_after_tool

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        
        # --- Debugging: Print available attributes --- 
        logger.debug("DEBUG: Attributes available in MyDevopsAgent.model_post_init after super().model_post_init:")
        try:
            for attr_name in dir(self):
                if not attr_name.startswith('__'): # Exclude dunder methods for brevity
                    try:
                        attr_value = getattr(self, attr_name)
                        logger.debug(f"  self.{attr_name} (type: {type(attr_value)})")
                        if attr_name == "llm_client" or "client" in attr_name.lower() or "llm" in attr_name.lower():
                            logger.debug(f"    Potential LLM client found: self.{attr_name} = {attr_value}")
                    except Exception as e_getattr:
                        logger.debug(f"  self.{attr_name} (could not getattr: {e_getattr})")
        except Exception as e_dir:
            logger.debug(f"  Error during dir(self): {e_dir}")
        logger.debug("--- End Debugging ---  ")

        # Try to get llm_client from __context if it's available
        if hasattr(__context, 'llm_client') and __context.llm_client:
            logger.info(f"Found llm_client in __context: {type(__context.llm_client).__name__}")
            self.llm_client = __context.llm_client

        # Try to create a default llm_client if needed
        if not hasattr(self, 'llm_client') or self.llm_client is None:
            logger.warning("llm_client not available after model_post_init. Attempting to create a default client.")
            try:
                # Create genai client with API key directly
                if agent_config.GOOGLE_API_KEY:
                    self.llm_client = genai.Client(api_key=agent_config.GOOGLE_API_KEY)
                    logger.info("Created genai client with API key from environment")
                else:
                    self.llm_client = genai.Client()
                    logger.info("Created default genai client without explicit API key")
                logger.info("Created default genai client in model_post_init.")
            except Exception as e:
                logger.error(f"Failed to create default genai client in model_post_init: {e}")
                # Continue with llm_client=None - functionality will be limited

        self._determine_actual_token_limit()
        logger.info(f"Agent {self.name} initialized with token limit: {self._actual_llm_token_limit}")

        # Even if llm_client is None, we proceed with context_manager initialization
        # ContextManager is designed to handle a None llm_client with reduced functionality

        self._context_manager = ContextManager(
            model_name=self.model or agent_config.GEMINI_MODEL_NAME,
            max_llm_token_limit=self._actual_llm_token_limit,
            llm_client=self.llm_client, # Pass the llm_client (might be None)
            target_recent_turns=agent_config.CONTEXT_TARGET_RECENT_TURNS,
            target_code_snippets=agent_config.CONTEXT_TARGET_CODE_SNIPPETS,
            target_tool_results=agent_config.CONTEXT_TARGET_TOOL_RESULTS,
            max_stored_code_snippets=agent_config.CONTEXT_MAX_STORED_CODE_SNIPPETS,
            max_stored_tool_results=agent_config.CONTEXT_MAX_STORED_TOOL_RESULTS
        )
        self._planning_manager = PlanningManager(console_manager=self._console)

    def _determine_actual_token_limit(self):
        """Determines the actual token limit for the configured model."""
        model_to_check = self.model or agent_config.GEMINI_MODEL_NAME
        try:
            # First check if llm_client is available
            if not hasattr(self, 'llm_client') or self.llm_client is None:
                logger.warning("Cannot determine token limit dynamically: llm_client is None. Using fallbacks.")
                raise AttributeError("llm_client is None")

            # Check if llm_client is an instance of the new genai.Client
            if self.llm_client and isinstance(self.llm_client, genai.Client) and hasattr(self.llm_client.models, 'get'):
                # The model name from self.model (ADK LlmAgent's attribute) might be like "gemini-1.5-pro-latest"
                # or the full "models/gemini-1.5-pro-latest".
                # The new genai.Client().models.get() expects "models/gemini-1.5-pro-latest"
                model_name_for_sdk = self.model
                if not model_name_for_sdk.startswith("models/"):
                    model_name_for_sdk = f"models/{model_name_for_sdk}"
                
                model_info = self.llm_client.models.get(name=model_name_for_sdk)
                if model_info and hasattr(model_info, 'input_token_limit'):
                    self._actual_llm_token_limit = model_info.input_token_limit
                    logger.info(f"Dynamically fetched token limit for {model_name_for_sdk}: {self._actual_llm_token_limit}")
                    return
                else:
                    logger.warning(f"Could not find input_token_limit in model_info for {model_name_for_sdk}.")
            else:
                # Fallback if llm_client is not the new genai.Client or doesn't have models.get
                # This might happen if ADK passes something else or if using an older ADK version
                logger.warning("Llm_client is not an instance of google.genai.Client or models.get is unavailable. Attempting legacy genai.get_model if possible.")
                # Try legacy top-level genai.get_model if it exists (assuming 'from google import genai' brings it)
                if hasattr(genai, 'get_model'):
                    cleaned_model_name = model_to_check.split('/')[-1]
                    legacy_model_name = f"models/{cleaned_model_name}"
                    model_info_legacy = genai.get_model(model_name=legacy_model_name) # Use the full path for get_model
                    if model_info_legacy and hasattr(model_info_legacy, 'input_token_limit'):
                        self._actual_llm_token_limit = model_info_legacy.input_token_limit
                        logger.info(f"Dynamically fetched token limit for {legacy_model_name} via legacy genai.get_model: {self._actual_llm_token_limit}")
                        return
                    else:
                        logger.warning(f"Could not find input_token_limit via legacy genai.get_model for {legacy_model_name}.")
                else:
                    logger.warning("Legacy genai.get_model is not available. Cannot dynamically fetch token limit.")

        except Exception as e:
            logger.warning(f"Failed to dynamically fetch token limit for {model_to_check}: {e}. Using fallbacks.")

        # Fallback logic if dynamic fetching fails
        if model_to_check == agent_config.GEMINI_FLASH_MODEL_NAME:
            self._actual_llm_token_limit = agent_config.GEMINI_FLASH_TOKEN_LIMIT_FALLBACK
        elif model_to_check == agent_config.GEMINI_PRO_MODEL_NAME:
            self._actual_llm_token_limit = agent_config.GEMINI_PRO_TOKEN_LIMIT_FALLBACK
        else:
            self._actual_llm_token_limit = agent_config.DEFAULT_TOKEN_LIMIT_FALLBACK
        logger.info(f"Using fallback token limit for {model_to_check}: {self._actual_llm_token_limit}")

    def _start_status(self, message: str):
        ui_utils.stop_status_spinner(self._status_indicator)
        self._status_indicator = ui_utils.start_status_spinner(self._console, message)

    def _stop_status(self):
        ui_utils.stop_status_spinner(self._status_indicator)
        self._status_indicator = None

    async def handle_before_model(
        self, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> LlmResponse | None:
        user_message_content = get_last_user_content(llm_request)
        
        if user_message_content and (not self._context_manager.conversation_turns or \
                                   self._context_manager.conversation_turns[-1].user_message != user_message_content):
            if self._context_manager.current_turn_number == 0 or self._context_manager.conversation_turns[-1].agent_message is not None:
                 logger.debug(f"Starting new turn in CM with user message: {user_message_content[:100]}")
                 self._context_manager.start_new_turn(user_message_content)
            elif self._context_manager.conversation_turns[-1].user_message is None: 
                 logger.debug(f"Updating current turn in CM with user message: {user_message_content[:100]}")
                 self._context_manager.conversation_turns[-1].user_message = user_message_content
                 self._context_manager.conversation_turns[-1].user_message_tokens = self._context_manager._count_tokens(user_message_content)

        planning_response, approved_plan_text = await self._planning_manager.handle_before_model_planning_logic(
            user_message_content, llm_request
        )

        if planning_response:
            self._stop_status()
            return planning_response 

        if approved_plan_text:
            logger.info("MyDevopsAgent: Plan approved. Adding to context manager as system message.")
            self._context_manager.add_system_message(
                f"The user has approved the following plan. Proceed with implementation based on this plan:\n" \
                f"--- APPROVED PLAN ---\n{approved_plan_text}\n--- END APPROVED PLAN ---"
            )
            self._start_status("[bold yellow](Agent is implementing the plan...)")

        is_currently_a_plan_generation_turn = self._planning_manager.is_plan_generation_turn
            
        if not is_currently_a_plan_generation_turn:
            base_prompt_tokens = 0
            if self.instruction: 
                base_prompt_tokens += self._context_manager._count_tokens(self.instruction)
            
            cm_has_current_user_msg = False
            if user_message_content and self._context_manager.conversation_turns:
                last_cm_turn = self._context_manager.conversation_turns[-1]
                if last_cm_turn.user_message == user_message_content and last_cm_turn.turn_number == self._context_manager.current_turn_number:
                    cm_has_current_user_msg = True
            
            if user_message_content and not cm_has_current_user_msg:
                 base_prompt_tokens += self._context_manager._count_tokens(user_message_content)

            context_dict, context_tokens = self._context_manager.assemble_context(base_prompt_tokens)
            logger.info(f"Structured context assembled: {context_tokens} tokens.")
            try:
                if hasattr(llm_request, 'model') and llm_request.model: 
                    modified_request = inject_structured_context(llm_request, context_dict)
                    if hasattr(callback_context, "llm_request"):
                        callback_context.llm_request = modified_request
                    context_block_wrapper_text = f"SYSTEM CONTEXT (JSON):\n```json\n```\nUse this context to inform your response. Do not directly refer to this context block."
                    wrapper_tokens = self._context_manager._count_tokens(context_block_wrapper_text)
                    total_context_block_tokens = wrapper_tokens + context_tokens 
                    logger.info(f"Total tokens for prompt (base + context_block): {base_prompt_tokens + total_context_block_tokens}")
                else:
                    logger.warning("Skipping structured context injection as LlmRequest seems incomplete.")
            except Exception as e:
                logger.error(f"Failed to inject structured context: {e} - LlmRequest: {llm_request}", exc_info=True)
        else:
            logger.info("Plan generation turn: Skipping general context assembly and injection.")

        if is_currently_a_plan_generation_turn:
            self._start_status("[bold yellow](Agent is drafting a plan...)")
        elif not self._status_indicator: 
            if not (hasattr(callback_context, 'tool_calls') and callback_context.tool_calls):
                 self._start_status("[bold yellow](Agent is thinking...)")
        
        return None

    async def handle_after_model(
        self, callback_context: CallbackContext, llm_response: LlmResponse
    ) -> LlmResponse | None:
        self._stop_status()

        planning_intercept_response = await self._planning_manager.handle_after_model_planning_logic(
            llm_response, self._extract_response_text 
        )
        if planning_intercept_response:
            return planning_intercept_response 

        if hasattr(llm_response, 'usage_metadata') and llm_response.usage_metadata:
            usage = llm_response.usage_metadata
            ui_utils.display_model_usage(self._console, 
                getattr(usage, 'prompt_token_count', 'N/A'), 
                getattr(usage, 'candidates_token_count', 'N/A'), 
                getattr(usage, 'total_token_count', 'N/A')
            )

        extracted_text = self._extract_response_text(llm_response)
        if extracted_text and isinstance(extracted_text, str):
            if not self._context_manager.conversation_turns or \
               self._context_manager.conversation_turns[-1].turn_number != self._context_manager.current_turn_number:
                logger.warning("Attempting to update agent response for a turn that doesn't match current_turn_number. This might indicate a turn management issue.")
            self._context_manager.update_agent_response(self._context_manager.current_turn_number, extracted_text)
        
        self._is_new_conversation = False
        return None
        
    def _extract_response_text(self, llm_response: LlmResponse) -> Optional[str]:
        try:
            if llm_response.text:
                return llm_response.text
            if hasattr(llm_response, 'content') and getattr(llm_response, 'content'):
                content_obj = getattr(llm_response, 'content')
                if isinstance(content_obj, genai_types.Content) and content_obj.parts:
                    parts_texts = [part.text for part in content_obj.parts if hasattr(part, 'text') and part.text is not None]
                    if parts_texts:
                        return "".join(parts_texts)
            elif hasattr(llm_response, 'parts') and getattr(llm_response, 'parts'):
                parts = getattr(llm_response, 'parts')
                if isinstance(parts, list):
                     parts_texts = [part.text for part in parts if hasattr(part, 'text') and part.text is not None]
                     if parts_texts:
                        return "".join(parts_texts)
        except Exception as e:
            logger.warning(f"Failed to extract text from LLM response: {e}")
        return None

    async def handle_before_tool(
        self, tool: BaseTool, args: dict, tool_context: ToolContext, callback_context: CallbackContext | None = None
    ) -> dict | None:
        try:
            if callback_context is None:
                logger.warning(f"Agent {self.name}: handle_before_tool called without callback_context")
                return None 
            self._context_manager.add_tool_call(self._context_manager.current_turn_number, tool.name, args)
            
            logger.info(f"Agent {self.name}: Executing tool {tool.name} with args: {args}") 
            ui_utils.display_tool_execution_start(self._console, tool.name, args)
            return None
        except Exception as e:
            logger.error(f"Agent {self.name}: Error in handle_before_tool: {e}", exc_info=True)
            return None

    async def handle_after_tool(
        self, tool: BaseTool, tool_response: dict | str, callback_context: CallbackContext | None = None, args: dict | None = None, tool_context: ToolContext | None = None
    ) -> dict | None:
        start_time = time.time()
        logger.debug(f"Agent {self.name}: Handling tool response from {tool.name}")
        custom_processor_used = False
        if tool.name in TOOL_PROCESSORS:
            try:
                TOOL_PROCESSORS[tool.name](self._context_manager, tool, tool_response, args)
                custom_processor_used = True
            except Exception as e:
                logger.error(f"Error in custom processor for {tool.name}: {e}", exc_info=True)
        
        if not custom_processor_used:
            self._context_manager.add_tool_result(tool.name, tool_response)
        
        duration = time.time() - start_time
        
        if not (mcp_types and isinstance(tool_response, mcp_types.CallToolResult)) and \
           not isinstance(tool_response, ExecuteVettedShellCommandOutput):
            if isinstance(tool_response, dict) and (tool_response.get("status") == "error" or tool_response.get("error")):
                logger.error(f"Tool {tool.name} reported an error: {tool_response}")
            elif isinstance(tool_response, dict):
                 ui_utils.display_tool_finished(self._console, tool.name, tool_response, duration)
                 logger.info(f"Tool {tool.name} executed successfully.")

        return None

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        try:
            if self._is_new_conversation:
                logger.info(f"Agent {self.name}: New conversation detected, resetting context manager and planning state.")
                self._determine_actual_token_limit() # Ensure limit is up-to-date
                logger.info(f"Agent {self.name} re-initialized token limit for new conversation: {self._actual_llm_token_limit}")
               
                # Check if llm_client is available through ctx
                if hasattr(ctx, 'llm_client') and ctx.llm_client:
                    logger.info(f"Found llm_client from context: {type(ctx.llm_client).__name__}")
                    self.llm_client = ctx.llm_client
                
                # If self.llm_client is still None, try to create a generic genai client
                if self.llm_client is None:
                    logger.warning("No llm_client provided. Attempting to create a default genai client.")
                    try:
                        # Create genai client with API key directly
                        if agent_config.GOOGLE_API_KEY:
                            self.llm_client = genai.Client(api_key=agent_config.GOOGLE_API_KEY)
                            logger.info("Created genai client with API key from environment in _run_async_impl")
                        else:
                            self.llm_client = genai.Client()
                            logger.info("Created default genai client without explicit API key in _run_async_impl")
                        logger.info("Created default genai client.")
                    except Exception as e:
                        logger.error(f"Failed to create default genai client: {e}")
                        # Continue without client - ContextManager will work with limited functionality
                
                self._context_manager = ContextManager(
                    model_name=self.model or agent_config.GEMINI_MODEL_NAME,
                    max_llm_token_limit=self._actual_llm_token_limit,
                    llm_client=self.llm_client, # Pass client here
                    target_recent_turns=agent_config.CONTEXT_TARGET_RECENT_TURNS,
                    target_code_snippets=agent_config.CONTEXT_TARGET_CODE_SNIPPETS,
                    target_tool_results=agent_config.CONTEXT_TARGET_TOOL_RESULTS,
                    max_stored_code_snippets=agent_config.CONTEXT_MAX_STORED_CODE_SNIPPETS,
                    max_stored_tool_results=agent_config.CONTEXT_MAX_STORED_TOOL_RESULTS
                )
                self._planning_manager.reset_planning_state() 
            
            async for event in super()._run_async_impl(ctx):
                yield event
                
        except Exception as e:
            self._stop_status()
            error_type = type(e).__name__
            error_message = str(e)
            tb_str = traceback.format_exc()
            logger.error(
                f"Agent {self.name}: Unhandled exception in _run_async_impl: "
                f"{error_type}: {error_message}\n{tb_str}"
            )
            mcp_related_hint = ""
            if isinstance(e, (BrokenPipeError, EOFError)): # type: ignore[misc]
                logger.error(f"This error ({error_type}) often indicates an MCP server communication failure.")
                mcp_related_hint = " (possibly due to an issue with an external MCP tool process)."
            
            ui_utils.display_unhandled_error(self._console, error_type, error_message, mcp_related_hint)

            user_facing_error = (
                f"I encountered an unexpected internal issue{mcp_related_hint}. "
                f"I cannot proceed with this request. Details: {error_type}."
            )
            yield Event(
                author=self.name, 
                content=genai_types.Content(parts=[genai_types.Part(text=user_facing_error)]),
                actions=EventActions()
            )
            ctx.end_invocation = True

devops_agent_instance = MyDevopsAgent(
    model=agent_config.GEMINI_MODEL_NAME,
    name="devops_agent",
    description="Self-sufficient agent specialized in Platform Engineering, DevOps, and SRE practices.",
    instruction=agent_prompts.DEVOPS_AGENT_INSTR,
    tools=devops_core_tools, 
    output_key="devops", 
    generate_content_config=agent_config.MAIN_LLM_GENERATION_CONFIG,
)

root_agent = devops_agent_instance
