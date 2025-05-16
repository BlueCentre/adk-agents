"""DevOps Agent Implementation."""

import logging
import traceback # For logging stack traces
import time

from google.adk.agents.llm_agent import LlmAgent
from google.genai import types as genai_types 
from typing_extensions import override
from typing import AsyncGenerator, Optional 

from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool 
from google.adk.tools.tool_context import ToolContext 
from google.adk.agents.callback_context import CallbackContext
from google.adk.events.event import Event, EventActions 
from google.adk.agents.invocation_context import InvocationContext

from rich.console import Console # Still needed for the instance
from rich.status import Status # Still needed for type hint of _status_indicator

from pydantic import PrivateAttr

from . import config as agent_config
from .tools.setup import load_core_tools_and_toolsets
from .components.planning_manager import PlanningManager 
from .components.context_management import (
    ContextManager,
    TOOL_PROCESSORS, 
    process_user_message,
    get_last_user_content,
    inject_structured_context,
)
from .tools.shell_command import ExecuteVettedShellCommandOutput 
from .utils import ui as ui_utils
from . import prompts as agent_prompts # Updated import for prompts

logger = logging.getLogger(__name__)

try:
    from mcp import types as mcp_types
except ImportError:
    logger.warning("mcp.types not found, Playwright tool responses might not be fully processed if they are CallToolResult.")
    mcp_types = None 

devops_core_tools = load_core_tools_and_toolsets() # This will use agent_prompts internally via tool_loader

class MyDevopsAgent(LlmAgent):
    """A DevOps agent implementation with custom callbacks for tool execution and model interaction."""
    _console: Console = PrivateAttr(default_factory=lambda: Console(stderr=True))
    _status_indicator: Optional[Status] = PrivateAttr(default=None) # Type hint for clarity
    _context_manager: ContextManager = PrivateAttr()
    _is_new_conversation: bool = PrivateAttr(default=True)
    _planning_manager: PlanningManager = PrivateAttr()

    def __init__(self, **data: any):
        super().__init__(**data)
        self._context_manager = ContextManager(
            max_token_limit=90000, 
            recent_turns_to_keep=5,
            max_code_snippets=10,
            max_tool_results=20
        )
        # Pass agent_prompts to PlanningManager if it directly uses them, or ensure it imports them itself.
        # PlanningManager already imports 'from . import prompts as agent_prompt' which will become 'from .. import prompts as agent_prompts'
        self._planning_manager = PlanningManager(console_manager=self._console) 
        self.before_model_callback = self.handle_before_model
        self.after_model_callback = self.handle_after_model
        self.before_tool_callback = self.handle_before_tool
        self.after_tool_callback = self.handle_after_tool

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
        
        planning_response, approved_plan_text = await self._planning_manager.handle_before_model_planning_logic(
            user_message_content, llm_request
        )

        if planning_response:
            self._stop_status()
            return planning_response 

        if approved_plan_text:
            logger.info("MyDevopsAgent: Plan approved. Adding to context manager.")
            self._context_manager.add_system_message(
                f"The user has approved the following plan. Proceed with implementation based on this plan:\n" 
                f"--- APPROVED PLAN ---\n{approved_plan_text}\n--- END APPROVED PLAN ---"
            )
            self._start_status("[bold yellow](Agent is implementing the plan...)")

        is_currently_a_plan_generation_turn = self._planning_manager.is_plan_generation_turn

        if user_message_content and not is_currently_a_plan_generation_turn and not self._planning_manager.is_awaiting_plan_approval:
            process_user_message(self._context_manager, user_message_content)
            
        if not is_currently_a_plan_generation_turn:
            context_dict, estimated_tokens = self._context_manager.assemble_context()
            try:
                if hasattr(llm_request, 'model') and llm_request.model: 
                    modified_request = inject_structured_context(llm_request, context_dict)
                    if hasattr(callback_context, "llm_request"):
                        callback_context.llm_request = modified_request
                    logger.info(f"Estimated token count for structured context: {estimated_tokens}")
                else:
                    logger.warning("Skipping structured context injection as LlmRequest seems incomplete.")
            except Exception as e:
                logger.error(f"Failed to inject structured context: {e} - LlmRequest: {llm_request}") 
        else:
            logger.info("Plan generation turn: Skipping general context assembly and injection.")

        num_parts_info = 'N/A'
        if llm_request.contents and llm_request.contents[-1] and llm_request.contents[-1].parts:
            num_parts_info = str(len(llm_request.contents[-1].parts))
        logger.debug(f"Agent {self.name}: Before model call. Parts in last content object: {num_parts_info}")

        if is_currently_a_plan_generation_turn:
            self._start_status("[bold yellow](Agent is drafting a plan...)")
        elif not self._status_indicator: 
            original_tool_calls = callback_context.tool_calls if hasattr(callback_context, 'tool_calls') else []
            if not original_tool_calls:
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
            current_turn = self._context_manager.current_turn_number
            self._context_manager.update_agent_response(current_turn, extracted_text)
        
        self._is_new_conversation = False
        return None
        
    def _extract_response_text(self, llm_response: LlmResponse) -> Optional[str]:
        try:
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
            current_turn = self._context_manager.current_turn_number
            self._context_manager.add_tool_call(current_turn, tool.name, args)
            
            logger.info(f"Agent {self.name}: Executing tool {tool.name} with args: {args}") 
            ui_utils.display_tool_execution_start(self._console, tool.name, args)
            return None
        except Exception as e:
            logger.error(f"Agent {self.name}: Error in handle_before_tool: {e}")
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
                logger.error(f"Error in custom processor for {tool.name}: {e}")
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
                self._context_manager = ContextManager(
                    max_token_limit=90000,
                    recent_turns_to_keep=5,
                    max_code_snippets=10,
                    max_tool_results=20
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
    instruction=agent_prompts.DEVOPS_AGENT_INSTR, # Use agent_prompts
    tools=devops_core_tools, 
    output_key="devops", 
    generate_content_config=agent_config.MAIN_LLM_GENERATION_CONFIG,
)

root_agent = devops_agent_instance
