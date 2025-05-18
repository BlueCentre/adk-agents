"""DevOps Agent Implementation - Class Definition."""

import logging
import traceback
import time
import json
import os

from pydantic import PrivateAttr
from rich.console import Console
from rich.status import Status
from typing_extensions import override
from typing import AsyncGenerator, Optional, Any, Dict, List, Tuple, Callable

from google import genai
from google.adk.agents.llm_agent import LlmAgent
from google.genai import types as genai_types

from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.events.event import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext

from .components.planning_manager import PlanningManager
from .components.context_management import (
    TOOL_PROCESSORS,
    get_last_user_content,
)
from .tools.shell_command import ExecuteVettedShellCommandOutput
from .shared_libraries import ui as ui_utils

# Assuming these relative imports become sibling imports or need adjustment based on final structure
# If devops_agent.py is in devops/, then these should be from devops.*
from . import config as agent_config

logger = logging.getLogger(__name__)

try:
    from mcp import types as mcp_types
except ImportError:
    logger.warning("mcp.types not found, Playwright tool responses might not be fully processed if they are CallToolResult.")
    mcp_types = None

class MyDevopsAgent(LlmAgent):
    _console: Console = PrivateAttr(default_factory=lambda: Console(stderr=True))
    _status_indicator: Optional[Status] = PrivateAttr(default=None)
    _actual_llm_token_limit: int = PrivateAttr(default=agent_config.DEFAULT_TOKEN_LIMIT_FALLBACK)
    _is_new_conversation: bool = PrivateAttr(default=True)
    _planning_manager: Optional[PlanningManager] = PrivateAttr(default=None)
    llm_client: Optional[genai.Client] = None

    def __init__(self, **data: any):
        super().__init__(**data)
        if 'llm_client' in data:
            self.llm_client = data.pop('llm_client')
            logger.info(f"Using provided llm_client in __init__: {type(self.llm_client).__name__}")
        self.before_model_callback = self.handle_before_model
        self.after_model_callback = self.handle_after_model
        self.before_tool_callback = self.handle_before_tool
        self.after_tool_callback = self.handle_after_tool

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        # logger.debug("DEBUG: Attributes available in MyDevopsAgent.model_post_init after super().model_post_init:")
        # try:
        #     for attr_name in dir(self):
        #         if not attr_name.startswith('__'):
        #             try:
        #                 attr_value = getattr(self, attr_name)
        #                 logger.debug(f"  self.{attr_name} (type: {type(attr_value)})")
        #                 if attr_name == "llm_client" or "client" in attr_name.lower() or "llm" in attr_name.lower():
        #                     logger.debug(f"    Potential LLM client found: self.{attr_name} = {attr_value}")
        #             except Exception as e_getattr:
        #                 logger.debug(f"  self.{attr_name} (could not getattr: {e_getattr})")
        # except Exception as e_dir:
        #     logger.debug(f"  Error during dir(self): {e_dir}")
        # logger.debug("--- End Debugging ---  ")

        if hasattr(__context, 'llm_client') and __context.llm_client:
            logger.info(f"Found llm_client in __context: {type(__context.llm_client).__name__}")
            self.llm_client = __context.llm_client

        if not hasattr(self, 'llm_client') or self.llm_client is None:
            logger.warning("llm_client not available after model_post_init.")
            # try:
            #     logger.info("Attempting to creating default genai client in model_post_init.")
            #     if agent_config.GOOGLE_API_KEY:
            #         self.llm_client = genai.Client(api_key=agent_config.GOOGLE_API_KEY)
            #         logger.info("Created genai client with API key from environment")
            #     else:
            #         self.llm_client = genai.Client()
            #         logger.info("Created default genai client without explicit API key")
            #     logger.info("Created default genai client in model_post_init.")
            # except Exception as e:
            #     logger.error(f"Failed to create default genai client in model_post_init: {e}")

        self._determine_actual_token_limit()
        logger.info(f"Agent {self.name} initialized with token limit: {self._actual_llm_token_limit}")

        self._planning_manager = PlanningManager(console_manager=self._console)

    def _determine_actual_token_limit(self):
        """Determines the actual token limit for the configured model."""
        model_to_check = self.model or agent_config.GEMINI_MODEL_NAME
        try:
            if not hasattr(self, 'llm_client') or self.llm_client is None:
                logger.warning("Cannot determine token limit dynamically: llm_client is None. Using fallbacks.")
                raise AttributeError("llm_client is None")

            if self.llm_client and isinstance(self.llm_client, genai.Client) and hasattr(self.llm_client, 'get_model'):
                model_name_for_sdk = self.model
                if not model_name_for_sdk.startswith("models/"):
                    model_name_for_sdk = f"models/{model_name_for_sdk}"

                model_info = self.llm_client.get_model(model_name_for_sdk)
                if model_info and hasattr(model_info, 'input_token_limit'):
                    self._actual_llm_token_limit = model_info.input_token_limit
                    logger.info(f"Dynamically fetched token limit for {model_name_for_sdk}: {self._actual_llm_token_limit}")
                    return
                else:
                    logger.warning(f"Could not find input_token_limit in model_info for {model_name_for_sdk}.")
            else:
                logger.warning("Llm_client is not an instance of google.genai.Client or models.get is unavailable. Attempting legacy genai.get_model if possible.")
                if hasattr(genai, 'get_model'):
                    cleaned_model_name = model_to_check.split('/')[-1]
                    legacy_model_name = f"models/{cleaned_model_name}"
                    model_info_legacy = genai.get_model(model_name=legacy_model_name)
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
        if callback_context and hasattr(callback_context, 'state') and callback_context.state is not None:
            conversation_history = callback_context.state.get('user:conversation_history', [])
            current_turn = callback_context.state.get('temp:current_turn', {})

            if user_message_content:
                 if not conversation_history or conversation_history[-1].get('agent_message') is not None:
                      logger.debug(f"Starting new turn in context.state with user message: {user_message_content[:100]}")
                      current_turn = {'user_message': user_message_content}
                      conversation_history.append(current_turn)
                 elif conversation_history[-1].get('user_message') is None:
                      logger.debug(f"Updating current turn in context.state with user message: {user_message_content[:100]}")
                      conversation_history[-1]['user_message'] = user_message_content
                      current_turn = conversation_history[-1]
                 else:
                       logger.debug(f"Appending to last user message in context.state: {user_message_content[:100]}")
                       last_user_msg = conversation_history[-1].get('user_message', '')
                       conversation_history[-1]['user_message'] = last_user_msg + "\n" + user_message_content
                       current_turn = conversation_history[-1]

            callback_context.state['user:conversation_history'] = conversation_history
            callback_context.state['temp:current_turn'] = current_turn

            # New logic using context.state to determine if it's a new conversation and initialize state
            is_new_conversation = callback_context.state.get('temp:is_new_conversation', True)
            if is_new_conversation:
                logger.info(f"Agent {self.name}: New conversation detected (based on context.state), initializing state.")
                callback_context.state['user:conversation_history'] = [] # Initialize conversation history
                callback_context.state['app:code_snippets'] = [] # Initialize code snippets history if needed
                callback_context.state['temp:is_new_conversation'] = False # Mark as not a new conversation for subsequent calls

            # Ensure current turn temporary state is cleared at the start of a new turn processing
            # This assumes each call to handle_before_model corresponds to processing a new turn input.
            # Replacing .pop() with .get() and setting to None/empty
            tool_calls_current_turn = callback_context.state.get('temp:tool_calls_current_turn', None)
            if tool_calls_current_turn is not None:
                logger.debug("Clearing temp:tool_calls_current_turn state.")
                callback_context.state['temp:tool_calls_current_turn'] = None

            tool_results_current_turn = callback_context.state.get('temp:tool_results_current_turn', None)
            if tool_results_current_turn is not None:
                 logger.debug("Clearing temp:tool_results_current_turn state.")
                 callback_context.state['temp:tool_results_current_turn'] = None
            # Note: 'temp:current_turn' is managed above where user message is added.
        else:
             logger.warning("callback_context or callback_context.state is not available in handle_before_model. State will not be managed.")

        planning_response, approved_plan_text = await self._planning_manager.handle_before_model_planning_logic(
            user_message_content, llm_request
        )

        if planning_response:
            self._stop_status()
            return planning_response

        if approved_plan_text:
            logger.info("MyDevopsAgent: Plan approved. Adding to context.state as system message.")
            current_turn = callback_context.state.get('temp:current_turn', {})
            system_message = f"SYSTEM: The user has approved the following plan. Proceed with implementation:\n{approved_plan_text}"
            current_turn['system_message_plan'] = system_message
            callback_context.state['temp:current_turn'] = current_turn
            conversation_history = callback_context.state.get('user:conversation_history', [])
            conversation_history.append({'system_message': system_message})
            callback_context.state['user:conversation_history'] = conversation_history

            self._start_status("[bold yellow](Agent is implementing the plan...)")

        is_currently_a_plan_generation_turn = self._planning_manager.is_plan_generation_turn

        if not is_currently_a_plan_generation_turn:
            logger.info("Assembling context from context.state (user:conversation_history, temp:tool_results, etc.)")
            context_dict = self._assemble_context_from_state(callback_context.state)
            context_tokens = self._count_context_tokens(context_dict)

            try:
                if hasattr(llm_request, 'model') and llm_request.model:
                    system_context_message = f"SYSTEM CONTEXT (JSON):\n```json\n{json.dumps(context_dict, indent=2)}\n```\nUse this context to inform your response. Do not directly refer to this context block unless asked."

                    if hasattr(llm_request, 'messages') and isinstance(llm_request.messages, list):
                        try:
                            from google.genai import types as genai_types
                            system_message_part = genai_types.Part(text=system_context_message)
                            system_content = genai_types.Content(role='system', parts=[system_message_part])
                            llm_request.messages.insert(0, system_content)
                            logger.info("Injected structured context into llm_request messages.")
                        except Exception as e:
                             logger.warning(f"Could not inject structured context into llm_request messages: {e}")

                    total_context_block_tokens = self._count_tokens(system_context_message)
                    logger.info(f"Total tokens for prompt (base + context_block): {self._count_tokens(get_last_user_content(llm_request)) + total_context_block_tokens}")

                else:
                    logger.warning("Skipping structured context injection as LlmRequest seems incomplete.")
            except Exception as e:
                logger.error(f"Failed to inject structured context: {e} - LlmRequest: {llm_request}", exc_info=True)
        else:
            logger.info("Plan generation turn: Skipping general context assembly and injection.")

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

        processed_response = self._process_llm_response(llm_response)

        if processed_response["text_parts"]:
            extracted_text = "".join(processed_response["text_parts"])
            if extracted_text:
                conversation_history = callback_context.state.get('user:conversation_history', [])
                if conversation_history:
                    last_turn = conversation_history[-1]
                    if last_turn.get('agent_message') is None:
                        last_turn['agent_message'] = extracted_text
                        callback_context.state['user:conversation_history'] = conversation_history
                    else:
                         last_turn['agent_message'] += "\n" + extracted_text
                         callback_context.state['user:conversation_history'] = conversation_history
                    logger.debug(f"Updated agent response in context.state for last turn: {extracted_text[:100]}")
                else:
                    logger.warning("Attempting to update agent response in context.state but no conversation history found.")

        if processed_response["function_calls"]:
            logger.info(f"Handle function calls here: {processed_response["function_calls"]}")
            current_turn = callback_context.state.get('temp:current_turn', {})
            current_turn['function_calls'] = processed_response["function_calls"]
            callback_context.state['temp:current_turn'] = current_turn

        callback_context.state['temp:is_new_conversation'] = False # Use state instead of attribute

        # After processing the model response, integrate tool calls and results from temp state into history
        if callback_context and hasattr(callback_context, 'state') and callback_context.state is not None:
            # Replacing .pop() with .get() and setting to None/empty
            current_turn_tool_calls = callback_context.state.get('temp:tool_calls_current_turn', [])
            if current_turn_tool_calls is None:
                 current_turn_tool_calls = [] # Ensure it's a list if None

            current_turn_tool_results = callback_context.state.get('temp:tool_results_current_turn', [])
            if current_turn_tool_results is None:
                 current_turn_tool_results = [] # Ensure it's a list if None

            current_turn_data = callback_context.state.get('temp:current_turn', {})
            if current_turn_data is None:
                 current_turn_data = {} # Ensure it's a dict if None
            # Clear the temporary current turn data after retrieving
            callback_context.state['temp:current_turn'] = None

            # Integrate tool calls and results into the last turn in conversation history
            conversation_history = callback_context.state.get('user:conversation_history', [])
            if conversation_history:
                last_turn = conversation_history[-1]
                # Add tool calls and results to the last turn
                if current_turn_tool_calls:
                    last_turn['tool_calls'] = last_turn.get('tool_calls', []) + current_turn_tool_calls
                if current_turn_tool_results:
                    last_turn['tool_results'] = last_turn.get('tool_results', []) + current_turn_tool_results
                # Potentially add other current_turn_data if needed, e.g., system_message_plan
                last_turn.update({k: v for k, v in current_turn_data.items() if k not in ['user_message', 'agent_message', 'tool_calls', 'tool_results']})
                callback_context.state['user:conversation_history'] = conversation_history # Ensure state is updated
                logger.debug("Integrated tool calls and results into conversation history.")
        else:
            logger.warning("callback_context or callback_context.state is not available in handle_after_model. Tool data not integrated into history.")

        return None

    def _extract_response_text(self, llm_response: LlmResponse) -> Optional[str]:
        try:
            extracted_text = getattr(llm_response, 'text', None)
            if extracted_text:
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
            logger.warning(f"Failed to extract text from LLM response: {e}. "
                           f"LLM response type: {type(llm_response)}. "
                           f"LLM response attributes: {dir(llm_response)}")
        return None

    def _process_llm_response(self, llm_response: LlmResponse) -> Dict[str, Any]:
        """Processes the LLM response to extract text and function calls."""
        extracted_data: Dict[str, Any] = {
            "text_parts": [],
            "function_calls": []
        }

        if hasattr(llm_response, 'content') and getattr(llm_response, 'content'):
            content_obj = getattr(llm_response, 'content')
            if isinstance(content_obj, genai_types.Content) and content_obj.parts:
                for part in content_obj.parts:
                    if hasattr(part, 'text') and part.text is not None:
                        extracted_data["text_parts"].append(part.text)
                    elif hasattr(part, 'function_call') and part.function_call is not None:
                         extracted_data["function_calls"].append(part.function_call)

        elif hasattr(llm_response, 'parts') and getattr(llm_response, 'parts'):
            parts = getattr(llm_response, 'parts')
            if isinstance(parts, list):
                 for part in parts:
                    if hasattr(part, 'text') and part.text is not None:
                         extracted_data["text_parts"].append(part.text)
                    elif hasattr(part, 'function_call') and part.function_call is not None:
                         extracted_data["function_calls"].append(part.function_call)

        direct_text = getattr(llm_response, 'text', None)
        if direct_text and not extracted_data["text_parts"] and not extracted_data["function_calls"]:
             extracted_data["text_parts"].append(direct_text)

        if extracted_data["function_calls"]:
            logger.info(f"Detected function calls in LLM response: {extracted_data["function_calls"]}")

        return extracted_data

    async def handle_before_tool(
        self, tool: BaseTool, args: dict, tool_context: ToolContext, callback_context: CallbackContext | None = None
    ) -> dict | None:
        try:
            if tool_context and hasattr(tool_context, 'state') and tool_context.state is not None:
                # Initialize or get the list of tool calls for the current turn
                tool_calls = tool_context.state.get('temp:tool_calls_current_turn', [])
                if tool_calls is None: # Ensure tool_calls is a list even if state had None
                    tool_calls = []
                tool_calls.append({'tool_name': tool.name, 'args': args})
                tool_context.state['temp:tool_calls_current_turn'] = tool_calls
                logger.info(f"Added tool call to context.state: {tool.name} with args: {args}")
            else:
                logger.warning("tool_context or tool_context.state is not available in handle_before_tool. Tool call not logged to state.")

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
                # Pass state to custom processors only if available
                if tool_context and hasattr(tool_context, 'state') and tool_context.state is not None:
                    TOOL_PROCESSORS[tool.name](tool_context.state, tool, tool_response)
                else:
                     logger.warning(f"tool_context or tool_context.state is not available for custom processor {tool.name}. State not passed.")
                     TOOL_PROCESSORS[tool.name](None, tool, tool_response) # Pass None for state if not available
                custom_processor_used = True
            except Exception as e:
                logger.error(f"Error in custom processor for {tool.name}: {e}", exc_info=True)

        if not custom_processor_used:
            # New logic using context.state
            if tool_context and hasattr(tool_context, 'state') and tool_context.state is not None:
                # Initialize or get the list of tool results for the current turn
                tool_results = tool_context.state.get('temp:tool_results_current_turn', [])
                if tool_results is None: # Ensure tool_results is a list even if state had None
                    tool_results = []
                tool_results.append({'tool_name': tool.name, 'response': tool_response})
                tool_context.state['temp:tool_results_current_turn'] = tool_results
                logger.info(f"Added tool result to context.state for tool {tool.name}.")
            else:
                logger.warning(f"tool_context or tool_context.state is not available in handle_after_tool. Tool result not logged to state.")

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
            # Need to add placeholder methods for context assembly and token counting that operate on state
            # For simplicity, add them at the end of the class
            if not hasattr(self, '_assemble_context_from_state'):
                self._assemble_context_from_state = self._placeholder_assemble_context
            if not hasattr(self, '_count_context_tokens'):
                self._count_context_tokens = self._placeholder_count_tokens_for_context
            if not hasattr(self, '_count_tokens'):
                self._count_tokens = self._placeholder_count_tokens # Use a placeholder for now

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
            if isinstance(e, (BrokenPipeError, EOFError)):
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

    def _assemble_context_from_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Placeholder: Assembles context dictionary from state for LLM injection."""
        context_dict = {}

        history = state.get('user:conversation_history', [])
        recent_history = history[-agent_config.CONTEXT_TARGET_RECENT_TURNS:]

        formatted_history = []
        for turn in recent_history:
            if turn.get('user_message'):
                formatted_history.append({'role': 'user', 'content': turn['user_message']})
            if turn.get('agent_message'):
                formatted_history.append({'role': 'agent', 'content': turn['agent_message']})
            if turn.get('system_message'):
                 formatted_history.append({'role': 'system', 'content': turn['system_message']})
            if turn.get('tool_calls'):
                 formatted_history.append({'role': 'tool_code', 'content': json.dumps(turn['tool_calls'], indent=2)})
            if turn.get('tool_results'):
                 formatted_history.append({'role': 'tool_result', 'content': json.dumps(turn['tool_results'], indent=2)})

        context_dict['conversation_history'] = formatted_history

        code_snippets = state.get('app:code_snippets', [])
        context_dict['code_snippets'] = code_snippets[-agent_config.CONTEXT_TARGET_CODE_SNIPPETS:]

        return context_dict

    def _count_tokens(self, text: str) -> int:
        """Placeholder: Counts tokens for a given text using the LLM client."""
        logger.warning("Using placeholder token counting. Replace with actual LLM client token counter.")
        return len(text) // 4

    def _count_context_tokens(self, context_dict: Dict[str, Any]) -> int:
        """Placeholder: Counts tokens for the assembled context dictionary."""
        logger.warning("Using placeholder context token counting. Replace with actual LLM client token counter.")
        return len(json.dumps(context_dict)) // 4
