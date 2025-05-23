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
from google.genai import types as genai_types
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.adk.events.event import Event, EventActions

from .components.planning_manager import PlanningManager
from .components.context_management import (
    TOOL_PROCESSORS,
    get_last_user_content,
)
from .components.context_management.context_manager import (
    ContextManager,
    ConversationTurn,
    CodeSnippet,
    ToolResult
)
from .shared_libraries import ui as ui_utils
from .tools.shell_command import ExecuteVettedShellCommandOutput

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
    _context_manager: Optional[ContextManager] = PrivateAttr(default=None)
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
        # Register the after_agent callback for cleanup
        # NOTE: Temporarily disabled due to noisy cancellation scope errors during shutdown
        # These errors don't prevent proper shutdown but create poor UX. The cleanup function
        # is still available for manual/runner-level cleanup if needed.
        # self.after_agent_callback = self.handle_after_agent

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

        # Initialize ContextManager here
        self._context_manager = ContextManager(
            model_name=self.model or agent_config.DEFAULT_AGENT_MODEL,
            max_llm_token_limit=self._actual_llm_token_limit,
            llm_client=self.llm_client # Pass the initialized llm_client
        )
        logger.info("ContextManager initialized in model_post_init.")

    def _determine_actual_token_limit(self):
        """Determines the actual token limit for the configured model."""
        model_to_check = self.model or agent_config.DEFAULT_AGENT_MODEL
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

            # Modify the user message to be a clear execution instruction instead of just "approve"
            execution_instruction = f"""Please execute the following approved plan step by step. Start with Phase 1 and work through each step systematically, using the specified tools and following the dependencies outlined in the plan.

APPROVED PLAN:
{approved_plan_text}

Begin execution now, starting with the first step."""
            
            # Update the LLM request with the execution instruction
            if hasattr(llm_request, 'contents') and isinstance(llm_request.contents, list):
                # Find and replace ALL user messages with the execution instruction
                from google.genai import types as genai_types
                execution_content = genai_types.Content(
                    role="user",
                    parts=[genai_types.Part(text=execution_instruction)]
                )
                
                # Replace all user messages with the single execution instruction
                new_contents = []
                user_message_replaced = False
                for content in llm_request.contents:
                    if content.role == "user" and not user_message_replaced:
                        # Replace the first user message with execution instruction
                        new_contents.append(execution_content)
                        user_message_replaced = True
                        logger.info("MyDevopsAgent: Replaced user message with plan execution instruction.")
                    elif content.role != "user":
                        # Keep non-user messages (system, assistant, etc.)
                        new_contents.append(content)
                    # Skip any additional user messages to avoid confusion
                
                llm_request.contents = new_contents

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
                            
                            # Log final assembled prompt details for optimization analysis
                            self._log_final_prompt_analysis(llm_request, context_dict, system_context_message)
                            
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
            logger.info(f"Handle function calls here: {processed_response['function_calls']}")
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
            logger.info(f"Detected function calls in LLM response: {extracted_data['function_calls']}")

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
                    # Create a mock tool object with args if available
                    if args:
                        # Create a mock tool object that includes the args
                        class MockTool:
                            def __init__(self, original_tool, args):
                                self.name = original_tool.name
                                self.args = args
                                # Copy other attributes from original tool
                                for attr_name in dir(original_tool):
                                    if not attr_name.startswith('_') and attr_name not in ['name', 'args']:
                                        try:
                                            setattr(self, attr_name, getattr(original_tool, attr_name))
                                        except:
                                            pass  # Skip attributes that can't be copied
                        
                        mock_tool = MockTool(tool, args)
                        TOOL_PROCESSORS[tool.name](tool_context.state, mock_tool, tool_response)
                    else:
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

            # Wrap the super call with retry logic for API errors
            max_retries = 2
            retry_count = 0
            
            while retry_count <= max_retries:
                try:
                    async for event in super()._run_async_impl(ctx):
                        yield event
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    error_message = str(e)
                    should_retry = False
                    
                    # Check for specific API errors that warrant retry with optimization
                    if "429" in error_message and "RESOURCE_EXHAUSTED" in error_message:
                        logger.warning(f"Agent {self.name}: Encountered 429 RESOURCE_EXHAUSTED error (attempt {retry_count + 1}/{max_retries + 1})")
                        should_retry = True
                    elif "500" in error_message and ("INTERNAL" in error_message or "ServerError" in error_message):
                        logger.warning(f"Agent {self.name}: Encountered 500 INTERNAL error (attempt {retry_count + 1}/{max_retries + 1})")
                        should_retry = True
                    
                    if should_retry and retry_count < max_retries:
                        retry_count += 1
                        logger.info(f"Agent {self.name}: Attempting input optimization and retry ({retry_count}/{max_retries})")
                        
                        # Optimize input by reducing context aggressively
                        await self._optimize_input_for_retry(ctx, retry_count)
                        
                        # Add exponential backoff delay
                        import asyncio
                        delay = 2 ** retry_count  # 2, 4, 8 seconds
                        logger.info(f"Agent {self.name}: Waiting {delay} seconds before retry...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Either not a retryable error or max retries exceeded
                        raise e

        except Exception as e:
            self._stop_status()
            error_type = type(e).__name__
            error_message = str(e)
            tb_str = traceback.format_exc()
            
            # Check if this is one of our target API errors
            if ("429" in error_message and "RESOURCE_EXHAUSTED" in error_message) or \
               ("500" in error_message and ("INTERNAL" in error_message or "ServerError" in error_message)):
                logger.error(f"Agent {self.name}: API error after all retry attempts: {error_type}: {error_message}")
                user_facing_error = (
                    f"I encountered API rate limits or server issues. "
                    f"I tried optimizing the request and retrying, but the issue persists. "
                    f"Please try again in a few moments or with a simpler request."
                )
            else:
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
            # Gracefully end the invocation
            ctx.end_invocation = True

    async def _optimize_input_for_retry(self, ctx: InvocationContext, retry_attempt: int):
        """Optimize input for retry by reducing context size and complexity."""
        try:
            logger.info(f"Agent {self.name}: Optimizing input for retry attempt {retry_attempt}")
            
            if hasattr(ctx, 'state') and ctx.state and self._context_manager:
                # Get current state
                state = ctx.state
                
                # Progressive optimization based on retry attempt
                if retry_attempt == 1:
                    # First retry: Reduce context moderately
                    logger.info("Agent optimization level 1: Reducing conversation history and code snippets")
                    
                    # Keep only last 2 conversation turns instead of 5
                    history = state.get('user:conversation_history', [])
                    if len(history) > 2:
                        state['user:conversation_history'] = history[-2:]
                        logger.info(f"Reduced conversation history from {len(history)} to 2 turns")
                    
                    # Keep only top 3 code snippets instead of 7
                    code_snippets = state.get('app:code_snippets', [])
                    if len(code_snippets) > 3:
                        state['app:code_snippets'] = code_snippets[:3]
                        logger.info(f"Reduced code snippets from {len(code_snippets)} to 3")
                        
                elif retry_attempt == 2:
                    # Second retry: Aggressive reduction
                    logger.info("Agent optimization level 2: Aggressive context reduction")
                    
                    # Keep only the last conversation turn
                    history = state.get('user:conversation_history', [])
                    if len(history) > 1:
                        state['user:conversation_history'] = history[-1:]
                        logger.info(f"Reduced conversation history from {len(history)} to 1 turn")
                    
                    # Remove all code snippets
                    if state.get('app:code_snippets'):
                        state['app:code_snippets'] = []
                        logger.info("Removed all code snippets")
                    
                    # Remove tool results from history
                    for turn in state.get('user:conversation_history', []):
                        if 'tool_results' in turn:
                            turn['tool_results'] = []
                            logger.info("Removed tool results from conversation history")
                
                # Also reduce the context manager's target limits
                if self._context_manager:
                    original_turns = self._context_manager.target_recent_turns
                    original_snippets = self._context_manager.target_code_snippets
                    original_results = self._context_manager.target_tool_results
                    
                    if retry_attempt == 1:
                        self._context_manager.target_recent_turns = min(2, original_turns)
                        self._context_manager.target_code_snippets = min(3, original_snippets)
                        self._context_manager.target_tool_results = min(3, original_results)
                    elif retry_attempt == 2:
                        self._context_manager.target_recent_turns = 1
                        self._context_manager.target_code_snippets = 0
                        self._context_manager.target_tool_results = 1
                    
                    logger.info(f"Adjusted context manager limits: turns={self._context_manager.target_recent_turns}, "
                              f"snippets={self._context_manager.target_code_snippets}, results={self._context_manager.target_tool_results}")
                
                logger.info(f"Agent {self.name}: Input optimization for retry attempt {retry_attempt} completed")
            else:
                logger.warning(f"Agent {self.name}: Cannot optimize input - context state not available")
                
        except Exception as e:
            logger.error(f"Agent {self.name}: Error during input optimization: {e}", exc_info=True)

    def _assemble_context_from_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Assembles context dictionary from state for LLM injection, respecting token limits.

        Synchronizes state with ContextManager and delegates assembly.
        """
        if not self._context_manager:
            logger.warning("ContextManager not initialized. Cannot assemble context from state.")
            return {}

        logger.info("CONTEXT ASSEMBLY: Starting enhanced context synchronization...")
        
        # Log current state contents for diagnostics (State object doesn't have .keys())
        try:
            history_count = len(state.get('user:conversation_history', []))
            snippets_count = len(state.get('app:code_snippets', []))
            decisions_count = len(state.get('app:key_decisions', []))
            logger.info(f"State contains: {history_count} conversation turns, {snippets_count} code snippets, {decisions_count} decisions")
        except Exception as e:
            logger.warning(f"Could not access state contents for diagnostics: {e}")
            # Continue with default empty state
            history_count = snippets_count = decisions_count = 0

        # Synchronize conversation history
        history = state.get('user:conversation_history', [])
        # Convert the history format from context.state to the ConversationTurn objects expected by ContextManager
        self._context_manager.conversation_turns = [] # Clear existing turns
        for i, turn_data in enumerate(history):
            turn = ConversationTurn(
                turn_number=i + 1, # Assign turn number based on list index
                user_message=turn_data.get('user_message'),
                agent_message=turn_data.get('agent_message'),
                tool_calls=turn_data.get('tool_calls', []), # Assume tool_calls is a list of dicts
                # Token counts will be calculated by ContextManager
            )
            # Manually count tokens for the synchronized turn data to set initial token counts
            # This is needed because ContextManager's add methods calculate tokens upon addition.
            # If we just copy, the token counts might be zero.
            turn.user_message_tokens = self._context_manager._count_tokens(turn.user_message) if turn.user_message else 0
            turn.agent_message_tokens = self._context_manager._count_tokens(turn.agent_message) if turn.agent_message else 0
            turn.tool_calls_tokens = self._context_manager._count_tokens(json.dumps(turn.tool_calls)) if turn.tool_calls else 0

            self._context_manager.conversation_turns.append(turn)
        self._context_manager.current_turn_number = len(self._context_manager.conversation_turns) # Update current turn number
        logger.info(f"Synchronized {len(self._context_manager.conversation_turns)} conversation turns")

        # Synchronize code snippets with enhanced tracking
        code_snippets_data = state.get('app:code_snippets', [])
        self._context_manager.code_snippets = [] # Clear existing snippets
        total_snippet_chars = 0
        for snippet_data in code_snippets_data:
            snippet = CodeSnippet(
                file_path=snippet_data.get('file_path', ''),
                code=snippet_data.get('code', ''),
                start_line=snippet_data.get('start_line', 0),
                end_line=snippet_data.get('end_line', 0),
                last_accessed=snippet_data.get('last_accessed', self._context_manager.current_turn_number), # Default to current turn
                relevance_score=snippet_data.get('relevance_score', 1.0),
                token_count=self._context_manager._count_tokens(snippet_data.get('code', ''))
            )
            self._context_manager.code_snippets.append(snippet)
            total_snippet_chars += len(snippet_data.get('code', ''))
        logger.info(f"Synchronized {len(self._context_manager.code_snippets)} code snippets, {total_snippet_chars:,} total chars")

        # Synchronize tool results from temp storage
        temp_tool_results = state.get('temp:tool_results_current_turn', [])
        if temp_tool_results:
            # Add these to the context manager's tool results storage
            for tool_result_data in temp_tool_results:
                tool_result = ToolResult(
                    tool_name=tool_result_data['tool_name'],
                    response=tool_result_data['response'],
                    summary=tool_result_data.get('summary', ''),
                    is_error=tool_result_data.get('is_error', False),
                    turn_number=self._context_manager.current_turn_number
                )
                self._context_manager.add_tool_result(tool_result)
            logger.info(f"Transferred {len(temp_tool_results)} tool results from temp storage to context manager")
            
            # Clear temp storage after transfer
            state['temp:tool_results_current_turn'] = []

        # Synchronize ContextState with enhanced logging
        self._context_manager.state.core_goal = state.get('app:core_goal', self._context_manager.state.core_goal)
        self._context_manager.state.current_phase = state.get('app:current_phase', self._context_manager.state.current_phase)
        self._context_manager.state.key_decisions = state.get('app:key_decisions', self._context_manager.state.key_decisions)
        self._context_manager.state.last_modified_files = state.get('app:last_modified_files', self._context_manager.state.last_modified_files)

        # Calculate initial token counts for ContextState elements
        self._context_manager.state.core_goal_tokens = self._context_manager._count_tokens(self._context_manager.state.core_goal)
        self._context_manager.state.current_phase_tokens = self._context_manager._count_tokens(self._context_manager.state.current_phase)

        logger.info(f"Context state: goal={bool(self._context_manager.state.core_goal)}, phase={bool(self._context_manager.state.current_phase)}, decisions={len(self._context_manager.state.key_decisions)}, files={len(self._context_manager.state.last_modified_files)}")

        # Now, use the ContextManager to assemble the context dictionary respecting the token limit
        # Calculate more accurate base prompt tokens (system instructions, tools, etc.)
        base_prompt_tokens = 1000  # Conservative estimate for system instructions and tools
        
        context_dict, total_context_tokens = self._context_manager.assemble_context(base_prompt_tokens)

        # Enhanced utilization logging
        available_capacity = self._context_manager.max_token_limit - total_context_tokens - base_prompt_tokens
        utilization_pct = ((total_context_tokens + base_prompt_tokens) / self._context_manager.max_token_limit) * 100
        
        logger.info(f"CONTEXT ASSEMBLY COMPLETE:")
        logger.info(f"  📊 Total Context Tokens: {total_context_tokens:,}")
        logger.info(f"  📊 Base Prompt Tokens: {base_prompt_tokens:,}")
        logger.info(f"  📊 Total Used: {total_context_tokens + base_prompt_tokens:,} / {self._context_manager.max_token_limit:,}")
        logger.info(f"  📊 Utilization: {utilization_pct:.2f}%")
        logger.info(f"  📊 Available Capacity: {available_capacity:,} tokens")
        
        if utilization_pct < 20:
            logger.warning(f"⚠️  LOW UTILIZATION: Only using {utilization_pct:.1f}% of available capacity!")
            logger.info("Consider adding more context: recent file changes, project structure, additional conversation history")

        return context_dict

    def _count_tokens(self, text: str) -> int:
        """Counts tokens for a given text using the ContextManager's strategy."""
        if self._context_manager:
            return self._context_manager._count_tokens(text) # Delegate to ContextManager
        else:
            logger.warning("ContextManager not initialized. Using fallback token counting.")
            return len(text) // 4 # Original fallback

    def _count_context_tokens(self, context_dict: Dict[str, Any]) -> int:
        """Counts tokens for the assembled context dictionary using the ContextManager's strategy."""
        # Convert context_dict to a string representation for counting
        context_string = json.dumps(context_dict)
        if self._context_manager:
            return self._context_manager._count_tokens(context_string) # Delegate to ContextManager
        else:
            logger.warning("ContextManager not initialized. Using fallback context token counting.")
            return len(context_string) // 4 # Original fallback

    async def handle_after_agent(self, callback_context: CallbackContext | None = None) -> None:
        """
        Handle cleanup operations after the agent session ends.
        
        This method provides a safe place for cleanup logic during agent shutdown,
        specifically for cleaning up MCP toolsets that require proper resource closure.
        
        NOTE: Due to ADK runner behavior during shutdown, this cleanup may encounter
        cancellation scope errors. We handle these gracefully and ensure the agent
        can still shut down properly even if cleanup is incomplete.
        """
        logger.info(f"Agent {self.name}: Starting after-agent cleanup...")
        cleanup_successful = False
        
        try:
            # Import the cleanup function from setup.py
            from .tools.setup import cleanup_mcp_toolsets
            
            # Attempt to cleanup MCP toolsets with timeout protection
            import asyncio
            try:
                # Set a reasonable timeout for cleanup to prevent hanging
                await asyncio.wait_for(cleanup_mcp_toolsets(), timeout=10.0)
                cleanup_successful = True
                logger.info(f"Agent {self.name}: Successfully completed MCP toolset cleanup.")
            except asyncio.TimeoutError:
                logger.warning(f"Agent {self.name}: MCP toolset cleanup timed out after 10 seconds. This may be due to cancellation scope issues during shutdown.")
            except RuntimeError as e:
                if "cancel scope" in str(e).lower():
                    logger.warning(f"Agent {self.name}: MCP toolset cleanup encountered cancellation scope error (expected during shutdown): {e}")
                else:
                    logger.error(f"Agent {self.name}: MCP toolset cleanup encountered unexpected RuntimeError: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Agent {self.name}: Error during MCP toolset cleanup: {e}", exc_info=True)
            
        except ImportError as e:
            logger.warning(f"Agent {self.name}: Could not import cleanup function: {e}")
        except Exception as e:
            logger.error(f"Agent {self.name}: Unexpected error during cleanup setup: {e}", exc_info=True)
        
        # Additional cleanup operations that should always run
        try:
            # Stop any remaining status indicators
            self._stop_status()
            logger.info(f"Agent {self.name}: Stopped status indicators.")
            
        except Exception as e:
            logger.error(f"Agent {self.name}: Error stopping status indicators: {e}", exc_info=True)
        
        # Final status report
        if cleanup_successful:
            logger.info(f"Agent {self.name}: Completed after-agent cleanup successfully.")
        else:
            logger.warning(f"Agent {self.name}: Completed after-agent cleanup with some issues. This is expected due to ADK runner shutdown behavior.")
            logger.info(f"Agent {self.name}: For cleaner shutdown, consider implementing runner-level cleanup as described in the setup.py comments.")

    def _log_final_prompt_analysis(self, llm_request: LlmRequest, context_dict: Dict[str, Any], system_context_message: str):
        """Log comprehensive final prompt analysis for optimization as per OPTIMIZATIONS.md section 4."""
        logger.info("=" * 80)
        logger.info("FINAL ASSEMBLED PROMPT ANALYSIS")
        logger.info("=" * 80)
        
        total_prompt_tokens = 0
        component_tokens = {}
        
        # Analyze each message in the final prompt
        if hasattr(llm_request, 'messages') and isinstance(llm_request.messages, list):
            logger.info(f"FINAL PROMPT STRUCTURE: {len(llm_request.messages)} messages")
            
            for i, message in enumerate(llm_request.messages):
                logger.info(f"\n--- MESSAGE {i+1} ---")
                logger.info(f"Role: {getattr(message, 'role', 'unknown')}")
                
                # Calculate tokens for this message
                message_text = ""
                if hasattr(message, 'parts') and message.parts:
                    text_parts = []
                    function_calls = []
                    for part in message.parts:
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
                        elif hasattr(part, 'function_call') and part.function_call:
                            function_calls.append(part.function_call)
                    
                    if text_parts:
                        message_text = "".join(text_parts)
                        message_tokens = self._count_tokens(message_text)
                        total_prompt_tokens += message_tokens
                        
                        # Identify component type
                        component_name = f"message_{i+1}_{getattr(message, 'role', 'unknown')}"
                        if message_text.startswith("SYSTEM CONTEXT (JSON):"):
                            component_name = "system_context_block"
                            logger.info(f"Content Type: System Context Block")
                            logger.info(f"Tokens: {message_tokens:,}")
                            
                            # Log context block details
                            logger.info("CONTEXT BLOCK COMPONENTS:")
                            for key, value in context_dict.items():
                                component_json = json.dumps({key: value}, indent=2)
                                component_token_count = self._count_tokens(component_json)
                                logger.info(f"  {key}: {component_token_count:,} tokens")
                                
                        else:
                            logger.info(f"Content Type: Text Message")
                            logger.info(f"Tokens: {message_tokens:,}")
                            logger.info(f"Character Count: {len(message_text):,}")
                            logger.info(f"Content Preview: {message_text[:200]}...")
                            
                        component_tokens[component_name] = message_tokens
                        
                    if function_calls:
                        for j, func_call in enumerate(function_calls):
                            func_call_text = str(func_call)
                            func_tokens = self._count_tokens(func_call_text)
                            total_prompt_tokens += func_tokens
                            
                            component_name = f"function_call_{i+1}_{j+1}"
                            component_tokens[component_name] = func_tokens
                            
                            logger.info(f"Function Call {j+1}:")
                            logger.info(f"  Tokens: {func_tokens:,}")
                            logger.info(f"  Call: {func_call_text[:200]}...")
                
                elif hasattr(message, 'text'):
                    message_text = message.text
                    message_tokens = self._count_tokens(message_text)
                    total_prompt_tokens += message_tokens
                    component_tokens[f"message_{i+1}_{getattr(message, 'role', 'unknown')}"] = message_tokens
                    
                    logger.info(f"Content Type: Direct Text")
                    logger.info(f"Tokens: {message_tokens:,}")
                    logger.info(f"Character Count: {len(message_text):,}")
                    logger.info(f"Content Preview: {message_text[:200]}...")
        
        # Log tools definition if available
        if hasattr(llm_request, 'tools') and llm_request.tools:
            tools_text = str(llm_request.tools)
            tools_tokens = self._count_tokens(tools_text)
            total_prompt_tokens += tools_tokens
            component_tokens["tools_definition"] = tools_tokens
            
            logger.info(f"\n--- TOOLS DEFINITION ---")
            logger.info(f"Tool Count: {len(llm_request.tools)}")
            logger.info(f"Tokens: {tools_tokens:,}")
            logger.info(f"Character Count: {len(tools_text):,}")
            
            # Log individual tool definitions
            for i, tool in enumerate(llm_request.tools):
                tool_text = str(tool)
                tool_tokens = self._count_tokens(tool_text)
                tool_name = getattr(tool, 'name', f'tool_{i+1}')
                logger.info(f"  Tool {i+1} ({tool_name}): {tool_tokens:,} tokens")
        
        # Log system instructions if available
        if hasattr(llm_request, 'system_instruction') and llm_request.system_instruction:
            system_text = str(llm_request.system_instruction)
            system_tokens = self._count_tokens(system_text)
            total_prompt_tokens += system_tokens
            component_tokens["system_instruction"] = system_tokens
            
            logger.info(f"\n--- SYSTEM INSTRUCTION ---")
            logger.info(f"Tokens: {system_tokens:,}")
            logger.info(f"Character Count: {len(system_text):,}")
            logger.info(f"Content Preview: {system_text[:200]}...")
        
        # Final summary
        logger.info("\n" + "=" * 60)
        logger.info("FINAL PROMPT TOKEN SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Prompt Tokens: {total_prompt_tokens:,}")
        logger.info(f"Model Token Limit: {self._actual_llm_token_limit:,}")
        logger.info(f"Token Utilization: {(total_prompt_tokens/self._actual_llm_token_limit*100):.1f}%")
        logger.info(f"Remaining Capacity: {self._actual_llm_token_limit - total_prompt_tokens:,} tokens")
        logger.info("")
        logger.info("TOKEN BREAKDOWN BY COMPONENT:")
        
        # Sort components by token count for analysis
        sorted_components = sorted(component_tokens.items(), key=lambda x: x[1], reverse=True)
        for component, tokens in sorted_components:
            percentage = (tokens / total_prompt_tokens * 100) if total_prompt_tokens > 0 else 0
            logger.info(f"  {component}: {tokens:,} tokens ({percentage:.1f}%)")
        
        logger.info("=" * 80)
        
        # Log the raw final prompt for exact inspection (if enabled via config)
        if os.getenv('LOG_FULL_PROMPTS', 'false').lower() == 'true':
            logger.info("\n" + "=" * 80)
            logger.info("RAW FINAL PROMPT STRING (Set LOG_FULL_PROMPTS=false to disable)")
            logger.info("=" * 80)
            
            try:
                # Reconstruct the full prompt string that would be sent to the LLM
                full_prompt_parts = []
                
                if hasattr(llm_request, 'system_instruction') and llm_request.system_instruction:
                    full_prompt_parts.append(f"SYSTEM INSTRUCTION:\n{llm_request.system_instruction}\n")
                
                if hasattr(llm_request, 'messages') and llm_request.messages:
                    for i, message in enumerate(llm_request.messages):
                        role = getattr(message, 'role', 'unknown')
                        full_prompt_parts.append(f"\n[{role.upper()}]:")
                        
                        if hasattr(message, 'parts') and message.parts:
                            for part in message.parts:
                                if hasattr(part, 'text') and part.text:
                                    full_prompt_parts.append(part.text)
                                elif hasattr(part, 'function_call') and part.function_call:
                                    full_prompt_parts.append(f"FUNCTION_CALL: {part.function_call}")
                        elif hasattr(message, 'text'):
                            full_prompt_parts.append(message.text)
                
                if hasattr(llm_request, 'tools') and llm_request.tools:
                    full_prompt_parts.append(f"\n\nTOOLS AVAILABLE:\n{llm_request.tools}")
                
                full_prompt = "\n".join(full_prompt_parts)
                logger.info(full_prompt)
                logger.info("=" * 80)
                
            except Exception as e:
                logger.warning(f"Could not reconstruct full prompt string: {e}")
        else:
            logger.info("ℹ️  Set LOG_FULL_PROMPTS=true to enable raw prompt logging")
