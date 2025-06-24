"""DevOps Agent Implementation - Class Definition."""

import logging
import traceback
import time
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum

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

# Telemetry and observability imports
from .telemetry import (
    telemetry, 
    track_llm_request, 
    track_context_operation, 
    OperationType
)
from .tracing import (
    trace_agent_lifecycle,
    trace_llm_request,
    trace_tool_execution,
    trace_context_operation,
    trace_tool_operation,
    agent_tracer
)
# from .logging_config import (
#     agent_logger, 
#     set_user_context, 
#     log_operation, 
#     log_performance_metrics,
#     log_business_event
# )
# from .tools.disabled.analytics import tool_analytics

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
    logger.warning("mcp.types not found, MCP tool responses might not be fully processed if they are CallToolResult.")
    mcp_types = None


class StateValidationError(Exception):
    """Raised when state validation fails."""
    pass


class TurnPhase(Enum):
    """Represents the current phase of a conversation turn."""
    INITIALIZING = "initializing"
    PROCESSING_USER_INPUT = "processing_user_input"
    CALLING_LLM = "calling_llm"
    PROCESSING_LLM_RESPONSE = "processing_llm_response"
    EXECUTING_TOOLS = "executing_tools"
    FINALIZING = "finalizing"
    COMPLETED = "completed"


@dataclass
class TurnState:
    """Represents the state of a single conversation turn."""
    turn_number: int
    phase: TurnPhase = TurnPhase.INITIALIZING
    user_message: Optional[str] = None
    agent_message: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    system_messages: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def mark_completed(self):
        """Mark the turn as completed."""
        self.phase = TurnPhase.COMPLETED
        self.completed_at = time.time()

    def add_error(self, error: str):
        """Add an error to this turn."""
        self.errors.append(error)
        logger.warning(f"Turn {self.turn_number} error: {error}")

    def validate(self) -> bool:
        """Validate the turn state for consistency."""
        if self.turn_number < 1:
            raise StateValidationError(f"Invalid turn number: {self.turn_number}")
        
        if self.phase == TurnPhase.COMPLETED and self.completed_at is None:
            raise StateValidationError(f"Turn {self.turn_number} marked completed but no completion time")
        
        return True


class StateManager:
    """Manages conversation state with robust error handling and validation."""
    
    def __init__(self):
        self.conversation_history: List[TurnState] = []
        self.current_turn: Optional[TurnState] = None
        self.is_new_conversation: bool = True
        self.app_state: Dict[str, Any] = {
            'code_snippets': [],
            'core_goal': '',
            'current_phase': '',
            'key_decisions': [],
            'last_modified_files': []
        }
        self._lock = False  # Simple lock to prevent concurrent modifications
        
    def _acquire_lock(self):
        """Acquire a simple lock for state modifications."""
        if self._lock:
            raise StateValidationError("State is currently locked for modification")
        self._lock = True
        
    def _release_lock(self):
        """Release the state lock."""
        self._lock = False
        
    def start_new_turn(self, user_message: Optional[str] = None) -> TurnState:
        """Start a new conversation turn with proper state management."""
        self._acquire_lock()
        try:
            # Complete the previous turn if it exists and isn't completed
            if self.current_turn and self.current_turn.phase != TurnPhase.COMPLETED:
                logger.warning(f"Previous turn {self.current_turn.turn_number} was not properly completed. Completing now.")
                self.current_turn.mark_completed()
                self.conversation_history.append(self.current_turn)
            
            # Create new turn
            turn_number = len(self.conversation_history) + 1
            self.current_turn = TurnState(
                turn_number=turn_number,
                user_message=user_message,
                phase=TurnPhase.PROCESSING_USER_INPUT
            )
            
            self.is_new_conversation = False
            logger.info(f"Started new turn {turn_number}")
            return self.current_turn
            
        finally:
            self._release_lock()
    
    def update_current_turn(self, **kwargs) -> None:
        """Update the current turn with new data."""
        if not self.current_turn:
            raise StateValidationError("No current turn to update")
            
        self._acquire_lock()
        try:
            for key, value in kwargs.items():
                if hasattr(self.current_turn, key):
                    setattr(self.current_turn, key, value)
                else:
                    logger.warning(f"Attempted to set unknown attribute '{key}' on turn state")
        finally:
            self._release_lock()
    
    def add_tool_call(self, tool_name: str, args: Dict[str, Any]) -> None:
        """Add a tool call to the current turn."""
        if not self.current_turn:
            raise StateValidationError("No current turn to add tool call to")
            
        tool_call = {
            'tool_name': tool_name,
            'args': args,
            'timestamp': time.time()
        }
        self.current_turn.tool_calls.append(tool_call)
        logger.debug(f"Added tool call {tool_name} to turn {self.current_turn.turn_number}")
    
    def add_tool_result(self, tool_name: str, result: Any) -> None:
        """Add a tool result to the current turn."""
        if not self.current_turn:
            raise StateValidationError("No current turn to add tool result to")
            
        tool_result = {
            'tool_name': tool_name,
            'result': result,
            'timestamp': time.time()
        }
        self.current_turn.tool_results.append(tool_result)
        logger.debug(f"Added tool result for {tool_name} to turn {self.current_turn.turn_number}")
    
    def complete_current_turn(self) -> None:
        """Complete the current turn and add it to history."""
        if not self.current_turn:
            logger.warning("No current turn to complete")
            return
            
        self._acquire_lock()
        try:
            self.current_turn.mark_completed()
            self.current_turn.validate()
            self.conversation_history.append(self.current_turn)
            logger.info(f"Completed turn {self.current_turn.turn_number}")
            self.current_turn = None
        finally:
            self._release_lock()
    
    def get_state_for_context(self) -> Dict[str, Any]:
        """Get state in format expected by legacy context management."""
        # Convert to legacy format for compatibility
        legacy_history = []
        for turn in self.conversation_history:
            legacy_turn = {
                'user_message': turn.user_message,
                'agent_message': turn.agent_message,
                'tool_calls': turn.tool_calls,
                'tool_results': turn.tool_results
            }
            # Add system messages if any
            if turn.system_messages:
                legacy_turn['system_messages'] = turn.system_messages
            legacy_history.append(legacy_turn)
        
        # Add current turn if it exists
        if self.current_turn:
            current_legacy = {
                'user_message': self.current_turn.user_message,
                'agent_message': self.current_turn.agent_message,
                'tool_calls': self.current_turn.tool_calls,
                'tool_results': self.current_turn.tool_results
            }
            if self.current_turn.system_messages:
                current_legacy['system_messages'] = self.current_turn.system_messages
            legacy_history.append(current_legacy)
        
        return {
            'user:conversation_history': legacy_history,
            'temp:is_new_conversation': self.is_new_conversation,
            'temp:current_turn': self.current_turn.__dict__ if self.current_turn else {},
            'temp:tool_calls_current_turn': self.current_turn.tool_calls if self.current_turn else [],
            'temp:tool_results_current_turn': self.current_turn.tool_results if self.current_turn else [],
            **{f'app:{k}': v for k, v in self.app_state.items()}
        }
    
    def sync_from_legacy_state(self, state: Dict[str, Any]) -> None:
        """Sync state from legacy callback_context.state format."""
        try:
            # Extract conversation history
            history = state.get('user:conversation_history', [])
            
            # Clear current state
            self.conversation_history = []
            self.current_turn = None
            
            # Rebuild from legacy format
            for i, turn_data in enumerate(history):
                turn = TurnState(
                    turn_number=i + 1,
                    user_message=turn_data.get('user_message'),
                    agent_message=turn_data.get('agent_message'),
                    tool_calls=turn_data.get('tool_calls', []),
                    tool_results=turn_data.get('tool_results', []),
                    system_messages=turn_data.get('system_messages', []),
                    phase=TurnPhase.COMPLETED
                )
                turn.completed_at = time.time()  # Mark as completed since it's in history
                self.conversation_history.append(turn)
            
            # Handle current turn data
            current_turn_data = state.get('temp:current_turn', {})
            if current_turn_data and isinstance(current_turn_data, dict):
                self.current_turn = TurnState(
                    turn_number=len(self.conversation_history) + 1,
                    user_message=current_turn_data.get('user_message'),
                    agent_message=current_turn_data.get('agent_message'),
                    tool_calls=current_turn_data.get('tool_calls', []),
                    tool_results=current_turn_data.get('tool_results', []),
                    system_messages=current_turn_data.get('system_messages', []),
                    phase=TurnPhase.PROCESSING_USER_INPUT
                )
            
            # Sync app state
            for key in self.app_state.keys():
                app_key = f'app:{key}'
                if app_key in state:
                    self.app_state[key] = state[app_key]
            
            self.is_new_conversation = state.get('temp:is_new_conversation', True)
            
            logger.debug(f"Synced state: {len(self.conversation_history)} turns in history, current_turn: {self.current_turn is not None}")
            
        except Exception as e:
            logger.error(f"Error syncing from legacy state: {e}", exc_info=True)
            raise StateValidationError(f"Failed to sync from legacy state: {e}")


class MyDevopsAgent(LlmAgent):
    """
    This is a custom agent that uses the ADK to manage the state of the conversation.

    https://google.github.io/adk-docs/agents/custom-agents/
    """
    _console: Console = PrivateAttr(default_factory=lambda: Console(stderr=True))
    _status_indicator: Optional[Status] = PrivateAttr(default=None)
    _actual_llm_token_limit: int = PrivateAttr(default=agent_config.DEFAULT_TOKEN_LIMIT_FALLBACK)
    _state_manager: StateManager = PrivateAttr(default_factory=StateManager)
    _planning_manager: Optional[PlanningManager] = PrivateAttr(default=None)
    _context_manager: Optional[ContextManager] = PrivateAttr(default=None)
    llm_client: Optional[genai.Client] = None

    # 1. Initialization and Configuration

    def __init__(self, **data: any):
        super().__init__(**data)
        if 'llm_client' in data:
            self.llm_client = data.pop('llm_client')
            logger.info(f"Using provided llm_client in __init__: {type(self.llm_client).__name__}")
        self.before_model_callback = self.handle_before_model
        self.after_model_callback = self.handle_after_model
        self.before_tool_callback = self.handle_before_tool
        self.after_tool_callback = self.handle_after_tool
        # Remove after_agent callback since ADK handles MCP cleanup automatically
        # self.after_agent_callback = self.handle_after_agent
        
        # Track whether MCP tools have been loaded asynchronously
        self._mcp_tools_loaded = False
        self._mcp_loading_lock = False

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

        # Check thinking configuration and provide warnings if needed
        self._validate_thinking_configuration()

        self._planning_manager = PlanningManager(console_manager=self._console)

        # Initialize ContextManager here
        self._context_manager = ContextManager(
            model_name=self.model or agent_config.DEFAULT_AGENT_MODEL,
            max_llm_token_limit=self._actual_llm_token_limit,
            llm_client=self.llm_client # Pass the initialized llm_client
        )
        logger.info("ContextManager initialized in model_post_init.")

        # Note: MCP toolsets are now loaded asynchronously in the tools property
        # This follows the ADK documentation pattern for proper async lifecycle management

    def _determine_actual_token_limit(self):
        """Determines the actual token limit for the configured model."""
        model_to_check = self.model or agent_config.DEFAULT_AGENT_MODEL
        
        # Use fallback values directly to avoid API issues
        if model_to_check == agent_config.GEMINI_FLASH_MODEL_NAME:
            self._actual_llm_token_limit = agent_config.GEMINI_FLASH_TOKEN_LIMIT_FALLBACK
        elif model_to_check == agent_config.GEMINI_PRO_MODEL_NAME:
            self._actual_llm_token_limit = agent_config.GEMINI_PRO_TOKEN_LIMIT_FALLBACK
        else:
            self._actual_llm_token_limit = agent_config.DEFAULT_TOKEN_LIMIT_FALLBACK
        
        logger.info(f"Using token limit for {model_to_check}: {self._actual_llm_token_limit}")

    def _validate_thinking_configuration(self):
        """Validate thinking configuration and provide helpful warnings."""
        model_name = self.model or agent_config.DEFAULT_AGENT_MODEL
        
        if agent_config.GEMINI_THINKING_ENABLE:
            if agent_config.is_thinking_supported(model_name):
                logger.info(f"✅ Gemini thinking enabled for supported model: {model_name}")
                logger.info(f"   Include thoughts: {agent_config.GEMINI_THINKING_INCLUDE_THOUGHTS}")
                logger.info(f"   Thinking budget: {agent_config.GEMINI_THINKING_BUDGET:,} tokens")
            else:
                logger.warning(f"⚠️  Gemini thinking enabled but model '{model_name}' does not support thinking!")
                logger.warning(f"   Supported models: {', '.join(agent_config.THINKING_SUPPORTED_MODELS)}")
                logger.warning(f"   Thinking configuration will be ignored for this model.")
                logger.warning(f"   Consider setting AGENT_MODEL to a supported 2.5 series model:")
                for supported_model in agent_config.THINKING_SUPPORTED_MODELS:
                    logger.warning(f"     export AGENT_MODEL={supported_model}")
        else:
            if agent_config.is_thinking_supported(model_name):
                logger.info(f"ℹ️  Model '{model_name}' supports thinking, but it's disabled.")
                logger.info(f"   To enable: export GEMINI_THINKING_ENABLE=true")
            else:
                logger.debug(f"Thinking not enabled and model '{model_name}' doesn't support it.")

    async def _ensure_mcp_tools_loaded(self):
        """Ensure MCP tools are loaded asynchronously if not already loaded.
        
        This method handles the case where the agent was initialized in an async context
        and MCP tools need to be loaded when the agent actually runs.
        """
        if self._mcp_tools_loaded or self._mcp_loading_lock:
            return
            
        self._mcp_loading_lock = True
        try:
            logger.info("Loading MCP tools asynchronously...")
            
            # Import the async loading function
            from .tools.setup import load_user_tools_and_toolsets_async
            
            # Load MCP tools asynchronously using the best available pattern
            mcp_tools, exit_stack = await load_user_tools_and_toolsets_async()
            
            if mcp_tools:
                # Add MCP tools to the agent's tools list
                if hasattr(self, 'tools') and self.tools is not None:
                    # Convert to list if it's not already
                    if not isinstance(self.tools, list):
                        self.tools = list(self.tools)
                    self.tools.extend(mcp_tools)
                else:
                    self.tools = mcp_tools
                
                logger.info(f"Successfully loaded {len(mcp_tools)} MCP tools asynchronously.")
                
                # Log which pattern was used
                if exit_stack is not None:
                    logger.info("MCP tools loaded using async pattern with exit stack management.")
                else:
                    logger.info("MCP tools loaded using simple pattern.")
                    
                self._mcp_tools_loaded = True
            else:
                logger.info("No MCP tools to load.")
                self._mcp_tools_loaded = True
                
        except Exception as e:
            logger.error(f"Failed to load MCP tools asynchronously: {e}", exc_info=True)
            # Mark as loaded to prevent repeated attempts
            self._mcp_tools_loaded = True
        finally:
            self._mcp_loading_lock = False

    # 2. Status Indicator

    def _start_status(self, message: str):
        """
        Starts the status spinner.

        We call ui_utils.stop_status_spinner to stop the status spinner if it is already running.
        This is to avoid the status spinner from being displayed twice.
        We then call ui_utils.start_status_spinner to start the status spinner with the new message.
        We then set the _status_indicator to the new status indicator.
        """
        ui_utils.stop_status_spinner(self._status_indicator)
        self._status_indicator = ui_utils.start_status_spinner(self._console, message)

    def _stop_status(self):
        ui_utils.stop_status_spinner(self._status_indicator)
        self._status_indicator = None

    # 3. ADK Callback Handlers

    @telemetry.track_operation(OperationType.LLM_REQUEST, "before_model")
    async def handle_before_model(
        self, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> LlmResponse | None:
        
        # Ensure MCP tools are loaded before processing the request
        await self._ensure_mcp_tools_loaded()
        
        user_message_content = get_last_user_content(llm_request)
        
        # Track context size for telemetry
        if llm_request and hasattr(llm_request, 'messages'):
            context_tokens = self._count_tokens(str(llm_request.messages))
            telemetry.track_context_usage(context_tokens, "llm_request")
        
        # Use robust state management
        try:
            if callback_context and hasattr(callback_context, 'state') and callback_context.state is not None:
                # Sync state manager with callback context state
                self._state_manager.sync_from_legacy_state(callback_context.state)
                
                # Handle new user message
                if user_message_content:
                    if not self._state_manager.current_turn:
                        # Start a new turn
                        self._state_manager.start_new_turn(user_message_content)
                    else:
                        # Update existing turn with user message
                        if self._state_manager.current_turn.user_message:
                            # Append to existing message
                            combined_message = self._state_manager.current_turn.user_message + "\n" + user_message_content
                            self._state_manager.update_current_turn(user_message=combined_message)
                        else:
                            # Set the user message
                            self._state_manager.update_current_turn(user_message=user_message_content)
                
                # Update callback context state with managed state
                callback_context.state.update(self._state_manager.get_state_for_context())
                
                logger.debug(f"State management: Turn {self._state_manager.current_turn.turn_number if self._state_manager.current_turn else 'None'}, "
                           f"History: {len(self._state_manager.conversation_history)} turns")
                
            else:
                logger.warning("callback_context or callback_context.state is not available in handle_before_model. Using internal state management only.")
                # Use internal state management only
                if user_message_content:
                    if not self._state_manager.current_turn:
                        self._state_manager.start_new_turn(user_message_content)
                    else:
                        self._state_manager.update_current_turn(user_message=user_message_content)
                        
        except StateValidationError as e:
            logger.error(f"State validation error in handle_before_model: {e}")
            # Reset state manager and start fresh
            self._state_manager = StateManager()
            if user_message_content:
                self._state_manager.start_new_turn(user_message_content)
        except Exception as e:
            logger.error(f"Unexpected error in state management: {e}", exc_info=True)
            # Continue with degraded functionality

        # Apply thinking configuration if supported and enabled
        thinking_config = self._create_thinking_config()
        if thinking_config and hasattr(llm_request, 'config'):
            # Apply thinking config to the existing request config
            if hasattr(llm_request.config, 'thinking_config'):
                llm_request.config.thinking_config = thinking_config
                logger.info("Applied thinking configuration to LLM request")
            else:
                logger.warning("LLM request config does not support thinking_config attribute")
        elif thinking_config:
            logger.warning("LLM request does not have config attribute to apply thinking configuration")

        planning_response, approved_plan_text = await self._planning_manager.handle_before_model_planning_logic(
            user_message_content, llm_request
        )

        if planning_response:
            self._stop_status()
            return planning_response

        if approved_plan_text:
            logger.info("MyDevopsAgent: Plan approved. Adding to context.state as system message.")
            current_turn = callback_context.state.get('temp:current_turn', {})
            if current_turn is None:
                current_turn = {}
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

            self._start_status("[bold yellow](Agent is implementing the plan...)[/bold yellow]")

        is_currently_a_plan_generation_turn = self._planning_manager.is_plan_generation_turn

        if not is_currently_a_plan_generation_turn:
            # Add enhanced status indicator showing thinking mode
            thinking_config = self._create_thinking_config()
            if thinking_config:
                self._start_status("[bold cyan]🧠 (Agent is thinking deeply...)[/bold cyan]")
                logger.info("🧠 Enhanced thinking mode enabled - using advanced reasoning capabilities")
            else:
                self._start_status("[bold blue](Agent is thinking...)[/bold blue]")
            logger.info("Assembling context from context.state (user:conversation_history, temp:tool_results, etc.)")
            
            # Calculate accurate base prompt tokens BEFORE assembling context
            # This is critical to prevent token limit exceeded errors
            base_prompt_tokens = 0
            
            # Count user message tokens
            if user_message_content:
                user_tokens = self._count_tokens(user_message_content)
                base_prompt_tokens += user_tokens
                logger.info(f"User message tokens: {user_tokens:,}")
            
            # Count system instruction tokens
            if hasattr(llm_request, 'system_instruction') and llm_request.system_instruction:
                system_tokens = self._count_tokens(str(llm_request.system_instruction))
                base_prompt_tokens += system_tokens
                logger.info(f"System instruction tokens: {system_tokens:,}")
            
            # Count tool definition tokens (this is often the largest component)
            if hasattr(llm_request, 'tools') and llm_request.tools:
                tools_tokens = self._count_tokens(str(llm_request.tools))
                base_prompt_tokens += tools_tokens
                logger.info(f"Tools definition tokens: {tools_tokens:,}")
            
            # CRITICAL FIX: Do NOT count existing conversation history as "base prompt"
            # Conversation history should be managed by the context manager, not included
            # in base prompt calculation. This was causing massive token growth between turns.
            # 
            # The ADK framework automatically includes conversation history in the request,
            # but we want our context manager to handle that intelligently with optimization.
            #
            # Previous buggy code was:
            # if hasattr(llm_request, 'messages') and isinstance(llm_request.messages, list):
            #     for message in llm_request.messages:
            #         ...count all existing messages as "base prompt"...
            #
            # This caused:
            # - Turn 1: base = 2,011 tokens  
            # - Turn 2: base = 2,001 + previous_conversation = 7,859 tokens (242% increase!)
            logger.info("🔧 OPTIMIZATION: Excluding conversation history from base prompt calculation")
            logger.info("   Conversation history will be managed by context manager with smart optimization")
            
            # ADVANCED OPTIMIZATION: Apply smart conversation history filtering
            # This preserves tool execution flows while optimizing token usage
            logger.info("🔧 APPLYING SMART CONVERSATION FILTERING...")
            self._apply_smart_conversation_filtering(llm_request, user_message_content)
            
            # Recalculate base tokens after smart filtering
            if hasattr(llm_request, 'contents') and isinstance(llm_request.contents, list):
                logger.info(f"🔧 RECALCULATING tokens after smart filtering...")
                
                # Reset and recalculate from filtered contents
                filtered_content_tokens = 0
                for content in llm_request.contents:
                    if hasattr(content, 'parts') and content.parts:
                        for part in content.parts:
                            if hasattr(part, 'text') and part.text:
                                # Don't count context injections we'll add later
                                if not part.text.startswith("SYSTEM CONTEXT (JSON):"):
                                    content_tokens = self._count_tokens(part.text)
                                    filtered_content_tokens += content_tokens
                
                # Update base_prompt_tokens with filtered content
                base_prompt_tokens = filtered_content_tokens
                
                # Add back the core components
                if user_message_content:
                    user_tokens = self._count_tokens(user_message_content) 
                    # Only add if not already counted in filtered contents
                    current_user_in_contents = any(
                        hasattr(content, 'parts') and content.parts and
                        any(hasattr(part, 'text') and part.text == user_message_content 
                            for part in content.parts if hasattr(part, 'text'))
                        for content in llm_request.contents if content.role == "user"
                    )
                    if not current_user_in_contents:
                        base_prompt_tokens += user_tokens
                        logger.info(f"  Added user message tokens: {user_tokens:,}")
                
                if hasattr(llm_request, 'system_instruction') and llm_request.system_instruction:
                    system_tokens = self._count_tokens(str(llm_request.system_instruction))
                    base_prompt_tokens += system_tokens
                    logger.info(f"  Added system instruction tokens: {system_tokens:,}")
                
                if hasattr(llm_request, 'tools') and llm_request.tools:
                    tools_tokens = self._count_tokens(str(llm_request.tools))
                    base_prompt_tokens += tools_tokens
                    logger.info(f"  Added tools tokens: {tools_tokens:,}")
                
                logger.info(f"🔧 SMART FILTERING TOKEN IMPACT:")
                logger.info(f"  Filtered content tokens: {filtered_content_tokens:,}")
                logger.info(f"  Total base prompt tokens: {base_prompt_tokens:,}")
            
            # Add safety margin for JSON structure overhead and response generation
            safety_margin = 2000
            base_prompt_tokens += safety_margin
            
            logger.info(f"ACCURATE BASE PROMPT CALCULATION:")
            logger.info(f"  Total Base Prompt Tokens: {base_prompt_tokens:,}")
            logger.info(f"  Safety Margin: {safety_margin:,}")
            logger.info(f"  Available for Context: {self._context_manager.max_token_limit - base_prompt_tokens:,}")
            
            # Ensure we don't exceed the token limit even before adding context
            if base_prompt_tokens >= self._context_manager.max_token_limit:
                logger.error(f"Base prompt ({base_prompt_tokens:,} tokens) already exceeds token limit ({self._context_manager.max_token_limit:,})!")
                logger.error("This indicates the tools definition or system instructions are too large.")
                # Use minimal context in this case
                context_dict = {}
            else:
                # Temporarily store the accurate base prompt tokens for context assembly
                original_base_tokens = getattr(self, '_temp_base_prompt_tokens', None)
                self._temp_base_prompt_tokens = base_prompt_tokens
                
                context_dict = self._assemble_context_from_state(callback_context.state)
                
                # Restore original value
                if original_base_tokens is not None:
                    self._temp_base_prompt_tokens = original_base_tokens
                else:
                    delattr(self, '_temp_base_prompt_tokens')
            
            context_tokens = self._count_context_tokens(context_dict)

            try:
                if hasattr(llm_request, 'model') and llm_request.model:
                    system_context_message = f"SYSTEM CONTEXT (JSON):\n```json\n{json.dumps(context_dict, indent=2)}\n```\nUse this context to inform your response. Do not directly refer to this context block unless asked."

                    # CRITICAL FIX PART 3: Inject context into the filtered contents, not messages
                    # We need to inject our optimized context into the filtered contents that we created
                    if hasattr(llm_request, 'contents') and isinstance(llm_request.contents, list):
                        try:
                            from google.genai import types as genai_types
                            
                            # Create our context injection
                            system_message_part = genai_types.Part(text=system_context_message)
                            system_content = genai_types.Content(role='user', parts=[system_message_part])
                            
                            # Insert context at the beginning of filtered contents (before current user message)
                            # Our filtered contents should be: [system_messages, context_injection, current_user_message]
                            insert_position = 0
                            
                            # Find position after any system messages
                            for i, content in enumerate(llm_request.contents):
                                if content.role == "system":
                                    insert_position = i + 1
                                else:
                                    break
                            
                            # Insert our context after system messages but before user messages
                            llm_request.contents.insert(insert_position, system_content)
                            logger.info(f"🔧 INJECTED optimized context into filtered contents at position {insert_position}")
                            
                            # Log final assembled prompt details for optimization analysis
                            self._log_final_prompt_analysis(llm_request, context_dict, system_context_message)
                            
                        except Exception as e:
                            logger.warning(f"Could not inject structured context into llm_request contents: {e}")
                    
                    # DEPRECATED: Remove old messages injection that was causing double-counting
                    # This was the old approach that added context to messages even though we already filtered contents
                    # if hasattr(llm_request, 'messages') and isinstance(llm_request.messages, list):
                    #     llm_request.messages.insert(0, system_content)

                    total_context_block_tokens = self._count_tokens(system_context_message)
                    logger.info(f"Total tokens for prompt (base + context_block): {base_prompt_tokens + total_context_block_tokens}")
                    
                    # Final validation: ensure we don't exceed token limit
                    final_prompt_tokens = base_prompt_tokens + total_context_block_tokens
                    if final_prompt_tokens > self._context_manager.max_token_limit:
                        logger.error(f"CRITICAL: Final prompt ({final_prompt_tokens:,} tokens) exceeds token limit ({self._context_manager.max_token_limit:,})!")
                        logger.error("This should not happen if context manager is working correctly.")
                        logger.error("The request will likely fail with a token limit error.")
                    else:
                        utilization_pct = (final_prompt_tokens / self._context_manager.max_token_limit) * 100
                        logger.info(f"Final prompt validation: {final_prompt_tokens:,}/{self._context_manager.max_token_limit:,} tokens ({utilization_pct:.1f}%)")

                else:
                    logger.warning("Skipping structured context injection as LlmRequest seems incomplete.")
            except Exception as e:
                logger.error(f"Failed to inject structured context: {e} - LlmRequest: {llm_request}", exc_info=True)
        else:
            logger.info("Plan generation turn: Skipping general context assembly and injection.")

        return None

    # BUG: trace_agent_lifecycle causes 'RecursionError: maximum recursion depth exceeded'
    # @trace_agent_lifecycle("llm_response_processing")
    @telemetry.track_operation(OperationType.LLM_REQUEST, "after_model")
    async def handle_after_model(
        self, callback_context: CallbackContext, llm_response: LlmResponse
    ) -> LlmResponse | None:
        # Track LLM response metrics including thinking tokens
        if hasattr(llm_response, 'usage_metadata') and llm_response.usage_metadata:
            usage = llm_response.usage_metadata
            prompt_tokens = getattr(usage, 'prompt_token_count', 0)
            completion_tokens = getattr(usage, 'candidates_token_count', 0)
            total_tokens = getattr(usage, 'total_token_count', 0)
            thinking_tokens = getattr(usage, 'thoughts_token_count', 0) or 0
            
            # Log thinking token usage if present
            if thinking_tokens > 0:
                logger.info(f"Thinking tokens used: {thinking_tokens:,}")
                logger.info(f"Output tokens: {completion_tokens:,}")
                logger.info(f"Total response tokens (thinking + output): {thinking_tokens + completion_tokens:,}")
            
            # Track LLM usage in telemetry
            telemetry.track_llm_request(
                model=self.model or agent_config.DEFAULT_AGENT_MODEL,
                tokens_used=total_tokens,
                response_time=0,  # We don't have timing here, will be tracked by decorator
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            )
            
            # LLM usage tracking is handled by the telemetry decorator
            pass
        
        self._stop_status()

        planning_intercept_response = await self._planning_manager.handle_after_model_planning_logic(
            llm_response, self._extract_response_text
        )
        if planning_intercept_response:
            return planning_intercept_response

        if hasattr(llm_response, 'usage_metadata') and llm_response.usage_metadata:
            usage = llm_response.usage_metadata
            thinking_tokens = getattr(usage, 'thoughts_token_count', 0) or 0
            
            # Display enhanced usage info including thinking tokens if present
            if thinking_tokens > 0:
                ui_utils.display_model_usage_with_thinking(self._console,
                    getattr(usage, 'prompt_token_count', 'N/A'),
                    getattr(usage, 'candidates_token_count', 'N/A'),
                    thinking_tokens,
                    getattr(usage, 'total_token_count', 'N/A')
                )
            else:
                ui_utils.display_model_usage(self._console,
                    getattr(usage, 'prompt_token_count', 'N/A'),
                    getattr(usage, 'candidates_token_count', 'N/A'),
                    getattr(usage, 'total_token_count', 'N/A')
                )

        processed_response = self._process_llm_response(llm_response)

        # Display agent thought summaries if present
        if processed_response["thought_summaries"]:
            logger.info(f"Displaying {len(processed_response['thought_summaries'])} thought summaries in rich panel")
            ui_utils.display_agent_thought(self._console, processed_response["thought_summaries"])

        # Use robust state management for response processing
        try:
            if processed_response["text_parts"]:
                extracted_text = "".join(processed_response["text_parts"])
                if extracted_text and self._state_manager.current_turn:
                    # Update agent message in current turn
                    if self._state_manager.current_turn.agent_message:
                        # Append to existing agent message
                        combined_message = self._state_manager.current_turn.agent_message + "\n" + extracted_text
                        self._state_manager.update_current_turn(agent_message=combined_message)
                    else:
                        # Set the agent message
                        self._state_manager.update_current_turn(agent_message=extracted_text)
                    
                    logger.debug(f"Updated agent response in turn {self._state_manager.current_turn.turn_number}: {extracted_text[:100]}")

            if processed_response["function_calls"]:
                logger.info(f"Handle function calls here: {processed_response['function_calls']}")
                if self._state_manager.current_turn:
                    # Add function calls to current turn (they are already serialized from _process_llm_response)
                    for func_call in processed_response["function_calls"]:
                        self._state_manager.current_turn.tool_calls.append({
                            'function_call': func_call,  # func_call is now a serializable dict
                            'timestamp': time.time()
                        })

            # Update callback context state if available
            if callback_context and hasattr(callback_context, 'state') and callback_context.state is not None:
                callback_context.state.update(self._state_manager.get_state_for_context())
                logger.debug("Updated callback context state with managed state")
            
        except StateValidationError as e:
            logger.error(f"State validation error in handle_after_model: {e}")
            # Continue with degraded functionality
        except Exception as e:
            logger.error(f"Unexpected error in response state management: {e}", exc_info=True)
            # Continue with degraded functionality

        # Complete the current turn if we have one
        try:
            if self._state_manager.current_turn and self._state_manager.current_turn.phase != TurnPhase.COMPLETED:
                self._state_manager.complete_current_turn()
        except StateValidationError as e:
            logger.error(f"Error completing turn in handle_after_model: {e}")
        except Exception as e:
            logger.error(f"Unexpected error completing turn: {e}", exc_info=True)

        # If thought summaries were displayed separately and there are NO function calls, 
        # create a filtered response to avoid duplication. Don't filter if there are function calls
        # to preserve the function call/response cycle.
        if processed_response["thought_summaries"] and not processed_response["function_calls"]:
            logger.info("Creating filtered response to avoid thought summary duplication (no function calls present)")
            return self._create_filtered_response(llm_response, processed_response)

        # Return the original response so it gets displayed to the user
        # Only return None if we want to suppress the response entirely
        return llm_response

    @telemetry.track_operation(OperationType.TOOL_EXECUTION, "before_tool")
    async def handle_before_tool(
        self, tool: BaseTool, args: dict, tool_context: ToolContext, callback_context: CallbackContext | None = None
    ) -> dict | None:
        # Use context manager for tracing instead of decorator
        with trace_tool_execution(tool.name, operation="preprocessing", args=args):
            try:
                # Use robust state management for tool calls
                try:
                    self._state_manager.add_tool_call(tool.name, args)
                    
                    # Update tool context state if available
                    if tool_context and hasattr(tool_context, 'state') and tool_context.state is not None:
                        tool_context.state.update(self._state_manager.get_state_for_context())
                        logger.debug(f"Updated tool context state with tool call: {tool.name}")
                    
                except StateValidationError as e:
                    logger.error(f"State validation error in handle_before_tool: {e}")
                    # Continue with tool execution even if state management fails
                except Exception as e:
                    logger.error(f"Error in tool call state management: {e}", exc_info=True)
                    # Continue with tool execution

                logger.info(f"Agent {self.name}: Executing tool {tool.name} with args: {args}")
                ui_utils.display_tool_execution_start(self._console, tool.name, args)
                return None
            except Exception as e:
                logger.error(f"Agent {self.name}: Error in handle_before_tool: {e}", exc_info=True)
                return None

    @telemetry.track_operation(OperationType.TOOL_EXECUTION, "after_tool")
    async def handle_after_tool(
        self, tool: BaseTool, tool_response: dict | str, callback_context: CallbackContext | None = None, args: dict | None = None, tool_context: ToolContext | None = None
    ) -> dict | None:
        start_time = time.time()
        logger.debug(f"Agent {self.name}: Handling tool response from {tool.name}")
        custom_processor_used = False
        
        # Enhanced error handling for shell commands
        if tool.name == "execute_vetted_shell_command" and isinstance(tool_response, dict):
            if tool_response.get("status") == "error":
                error_message = tool_response.get("message", "")
                
                # Check for specific error patterns that can be retried
                if any(pattern in error_message.lower() for pattern in ["quotation", "parsing", "shlex"]):
                    logger.warning(f"Shell command failed with parsing error: {error_message}")
                    
                    # Add helpful guidance to the tool response
                    enhanced_message = (
                        f"{error_message}\n\n"
                        f"💡 This appears to be a command parsing issue. Consider:\n"
                        f"1. Using the 'execute_vetted_shell_command_with_retry' tool for automatic retry with alternative formats\n"
                        f"2. Simplifying complex commit messages by breaking them into multiple commands\n"
                        f"3. Using 'git commit' without -m to open an editor for complex messages"
                    )
                    tool_response["message"] = enhanced_message
                    tool_response["retry_suggested"] = True
                
                elif "command not found" in error_message.lower():
                    logger.warning(f"Shell command failed - command not found: {error_message}")
                    enhanced_message = (
                        f"{error_message}\n\n"
                        f"💡 Command not found. Consider:\n"
                        f"1. Trying to find the command using common paths\n"
                        f"2. Verifying the correct spelling and path\n"
                        f"3. Installing the required package if missing"
                    )
                    tool_response["message"] = enhanced_message
                
                elif "timeout" in error_message.lower():
                    logger.warning(f"Shell command timed out: {error_message}")
                    enhanced_message = (
                        f"{error_message}\n\n"
                        f"💡 Command timed out. Consider:\n"
                        f"1. Increasing the timeout parameter\n"
                        f"2. Breaking the operation into smaller steps\n"
                        f"3. Running the command in the background if appropriate"
                    )
                    tool_response["message"] = enhanced_message
        
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
            # Use robust state management for tool results
            try:
                self._state_manager.add_tool_result(tool.name, tool_response)
                
                # Update tool context state if available
                if tool_context and hasattr(tool_context, 'state') and tool_context.state is not None:
                    tool_context.state.update(self._state_manager.get_state_for_context())
                    logger.debug(f"Updated tool context state with tool result: {tool.name}")
                
            except StateValidationError as e:
                logger.error(f"State validation error in handle_after_tool: {e}")
                # Continue with tool processing even if state management fails
            except Exception as e:
                logger.error(f"Error in tool result state management: {e}", exc_info=True)
                # Continue with tool processing

        duration = time.time() - start_time

        if not (mcp_types and isinstance(tool_response, mcp_types.CallToolResult)) and \
            not isinstance(tool_response, ExecuteVettedShellCommandOutput):
            if isinstance(tool_response, dict) and (tool_response.get("status") == "error" or tool_response.get("error")):
                logger.error(f"Tool {tool.name} reported an error: {tool_response}")
                
                # Display enhanced error information to user
                if tool_response.get("retry_suggested"):
                    ui_utils.display_tool_error_with_suggestions(self._console, tool.name, tool_response, duration)
                else:
                    ui_utils.display_tool_error(self._console, tool.name, tool_response, duration)
            elif isinstance(tool_response, dict):
                ui_utils.display_tool_finished(self._console, tool.name, tool_response, duration)
                logger.info(f"Tool {tool.name} executed successfully.")

        return None

    # 4. Internal Response and Tool Processing Helpers

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
        """Processes the LLM response to extract text, function calls, and thought summaries."""
        extracted_data: Dict[str, Any] = {
            "text_parts": [],
            "function_calls": [],
            "thought_summaries": []
        }

        logger.debug(f"Processing LLM response - has content: {hasattr(llm_response, 'content')}, has parts: {hasattr(llm_response, 'parts')}")

        if hasattr(llm_response, 'content') and getattr(llm_response, 'content'):
            content_obj = getattr(llm_response, 'content')
            if isinstance(content_obj, genai_types.Content) and content_obj.parts:
                logger.debug(f"Processing {len(content_obj.parts)} parts from content object")
                for i, part in enumerate(content_obj.parts):
                    if hasattr(part, 'text') and part.text is not None:
                        # Check if this is a thought summary
                        if hasattr(part, 'thought') and part.thought:
                            extracted_data["thought_summaries"].append(part.text)
                            logger.debug(f"Part {i}: Extracted as thought summary (length: {len(part.text)})")
                        else:
                            extracted_data["text_parts"].append(part.text)
                            logger.debug(f"Part {i}: Extracted as regular text (length: {len(part.text)})")
                    elif hasattr(part, 'function_call') and part.function_call is not None:
                        # Convert function_call to serializable dictionary
                        func_call_dict = self._serialize_function_call(part.function_call)
                        extracted_data["function_calls"].append(func_call_dict)
                        logger.debug(f"Part {i}: Extracted as function call: {func_call_dict.get('name', 'unknown')}")

        elif hasattr(llm_response, 'parts') and getattr(llm_response, 'parts'):
            parts = getattr(llm_response, 'parts')
            if isinstance(parts, list):
                logger.debug(f"Processing {len(parts)} parts from direct parts attribute")
                for i, part in enumerate(parts):
                    if hasattr(part, 'text') and part.text is not None:
                        # Check if this is a thought summary
                        if hasattr(part, 'thought') and part.thought:
                            extracted_data["thought_summaries"].append(part.text)
                            logger.debug(f"Part {i}: Extracted as thought summary (length: {len(part.text)})")
                        else:
                            extracted_data["text_parts"].append(part.text)
                            logger.debug(f"Part {i}: Extracted as regular text (length: {len(part.text)})")
                    elif hasattr(part, 'function_call') and part.function_call is not None:
                        # Convert function_call to serializable dictionary
                        func_call_dict = self._serialize_function_call(part.function_call)
                        extracted_data["function_calls"].append(func_call_dict)
                        logger.debug(f"Part {i}: Extracted as function call: {func_call_dict.get('name', 'unknown')}")

        direct_text = getattr(llm_response, 'text', None)
        if direct_text and not extracted_data["text_parts"] and not extracted_data["function_calls"]:
            logger.debug(f"Using direct text fallback (length: {len(direct_text)})")
            # Check if the direct text contains thought patterns
            if self._is_thought_content(direct_text):
                extracted_data["thought_summaries"].append(direct_text)
                logger.debug("Direct text identified as thought content")
            else:
                extracted_data["text_parts"].append(direct_text)

        # Fallback: Check if any text_parts contain thought markers/patterns and move them
        text_parts_to_remove = []
        for i, text_part in enumerate(extracted_data["text_parts"]):
            if self._is_thought_content(text_part):
                extracted_data["thought_summaries"].append(text_part)
                text_parts_to_remove.append(i)
                logger.debug(f"Moved text part {i} to thought summaries based on content pattern")
        
        # Remove text parts that were moved to thought summaries (in reverse order to maintain indices)
        for i in reversed(text_parts_to_remove):
            extracted_data["text_parts"].pop(i)

        if extracted_data["function_calls"]:
            logger.info(f"Detected function calls in LLM response: {extracted_data['function_calls']}")

        if extracted_data["thought_summaries"]:
            logger.info(f"Detected {len(extracted_data['thought_summaries'])} thought summaries in LLM response")
        
        # Debug: Log summary of what was extracted
        logger.debug(f"Extraction summary - Text parts: {len(extracted_data['text_parts'])}, Function calls: {len(extracted_data['function_calls'])}, Thought summaries: {len(extracted_data['thought_summaries'])}")

        return extracted_data

    def _is_thought_content(self, text: str) -> bool:
        """Detect if text content appears to be agent thinking/reasoning."""
        if not text or not text.strip():
            return False
            
        text_lower = text.lower().strip()
        
        # Common thought patterns
        thought_patterns = [
            # Direct thinking indicators
            "**thinking through",
            "**my analytical process",
            "**determining the current",
            "**navigating the",
            "**finding the current",
            "**current time is already known",
            "**providing the requested information",
            
            # Reasoning patterns
            "okay, so the user wants",
            "let me think about",
            "i need to",
            "my best bet is to",
            "let's see",
            "first step is to",
            "good practice, always",
            "it's important to",
            "essentially,",
            "the logic is straightforward",
            
            # Planning/analysis patterns  
            "given my understanding",
            "i recognize that",
            "i'll just",
            "no need to",
            "i remember that",
            "i already",
            "therefore,",
        ]
        
        # Check for thought patterns at the beginning of text
        for pattern in thought_patterns:
            if text_lower.startswith(pattern):
                return True
                
        # Check for markdown bold thinking headers
        if text.startswith("**") and "**" in text[2:]:
            first_line = text.split('\n')[0]
            if any(word in first_line.lower() for word in ["thinking", "analytical", "process", "determining", "navigating", "finding"]):
                return True
        
        # Check if text is entirely reasoning/explanation without direct commands or responses
        direct_response_indicators = [
            "the current time is",
            "i have a set of tools",
            "these tools allow me",
            "here are the",
            "the following",
        ]
        
        # If it starts with direct response indicators, it's not thought content
        for indicator in direct_response_indicators:
            if text_lower.startswith(indicator):
                return False
                
        return False

    def _create_filtered_response(self, original_response: LlmResponse, processed_response: Dict[str, Any]) -> LlmResponse:
        """Creates a filtered response that excludes thought summaries to avoid duplication."""
        try:
            # Create new parts list excluding thought summaries
            filtered_parts = []
            
            # Add text parts (non-thought content)
            for text_part in processed_response["text_parts"]:
                if text_part.strip():  # Only add non-empty text
                    filtered_parts.append(genai_types.Part(text=text_part))
            
            # Add function calls
            for func_call in processed_response["function_calls"]:
                # Convert back from serialized dict to function call object if needed
                # For now, we'll preserve function calls as they are important
                if hasattr(original_response, 'content') and original_response.content and original_response.content.parts:
                    for part in original_response.content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            filtered_parts.append(part)
            
            # If we have filtered parts, create a new response
            if filtered_parts:
                filtered_content = genai_types.Content(parts=filtered_parts)
                filtered_response = LlmResponse(
                    content=filtered_content,
                    usage_metadata=getattr(original_response, 'usage_metadata', None)
                )
                logger.info(f"Created filtered response with {len(filtered_parts)} parts (thought summaries excluded)")
                return filtered_response
            else:
                # If no filtered parts, return None to suppress the response entirely
                logger.info("No non-thought content found, suppressing response to avoid empty display")
                return None
                
        except Exception as e:
            logger.error(f"Error creating filtered response: {e}", exc_info=True)
            # Fallback to original response if filtering fails
            return original_response

    def _serialize_function_call(self, function_call) -> Dict[str, Any]:
        """Convert a function_call object to a JSON-serializable dictionary."""
        try:
            # Try to extract common attributes from function_call objects
            func_call_dict = {}
            
            # Common attributes that function calls typically have
            if hasattr(function_call, 'name'):
                func_call_dict['name'] = function_call.name
            if hasattr(function_call, 'args'):
                func_call_dict['args'] = function_call.args
            if hasattr(function_call, 'id'):
                func_call_dict['id'] = function_call.id
                
            # If the object has a dict representation, use it
            if hasattr(function_call, '__dict__'):
                for key, value in function_call.__dict__.items():
                    if not key.startswith('_'):  # Skip private attributes
                        try:
                            # Test if the value is JSON serializable
                            json.dumps(value)
                            func_call_dict[key] = value
                        except (TypeError, ValueError):
                            # If not serializable, convert to string
                            func_call_dict[key] = str(value)
            
            # If we couldn't extract anything meaningful, convert the whole object to string
            if not func_call_dict:
                func_call_dict = {
                    'name': getattr(function_call, 'name', 'unknown'),
                    'args': getattr(function_call, 'args', {}),
                    'raw_str': str(function_call)
                }
                
            return func_call_dict
            
        except Exception as e:
            logger.warning(f"Failed to serialize function_call object: {e}")
            # Fallback: return a basic dictionary with string representation
            return {
                'name': 'unknown',
                'args': {},
                'error': f"Serialization failed: {e}",
                'raw_str': str(function_call)
            }

    def _message_has_tool_calls(self, message) -> bool:
        """Check if a message contains tool/function calls."""
        if hasattr(message, 'parts') and message.parts:
            for part in message.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    return True
        return False

    # 5. Context and State Management Helpers

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
            
            # Safe JSON serialization for tool_calls
            if turn.tool_calls:
                try:
                    tool_calls_json = json.dumps(turn.tool_calls)
                    turn.tool_calls_tokens = self._context_manager._count_tokens(tool_calls_json)
                except (TypeError, ValueError) as e:
                    logger.warning(f"Failed to JSON serialize tool_calls for token counting: {e}")
                    try:
                        tool_calls_json = json.dumps(turn.tool_calls, default=str)
                        turn.tool_calls_tokens = self._context_manager._count_tokens(tool_calls_json)
                    except Exception as e2:
                        logger.error(f"Failed to serialize tool_calls even with default=str: {e2}")
                        turn.tool_calls_tokens = self._context_manager._count_tokens(str(turn.tool_calls))
            else:
                turn.tool_calls_tokens = 0

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
        # Use accurate base prompt tokens if available, otherwise fall back to conservative estimate
        if hasattr(self, '_temp_base_prompt_tokens'):
            base_prompt_tokens = self._temp_base_prompt_tokens
            logger.info(f"Using accurate base prompt tokens: {base_prompt_tokens:,}")
        else:
            base_prompt_tokens = 1000  # Conservative estimate for system instructions and tools
            logger.warning(f"Using conservative base prompt token estimate: {base_prompt_tokens:,}")
        
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
        try:
            context_string = json.dumps(context_dict)
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to JSON serialize context_dict for token counting: {e}")
            # Fallback: try to serialize with a custom encoder that handles non-serializable objects
            try:
                context_string = json.dumps(context_dict, default=str)
            except Exception as e2:
                logger.error(f"Failed to serialize context_dict even with default=str: {e2}")
                # Ultimate fallback: convert the whole dict to string
                context_string = str(context_dict)
        
        if self._context_manager:
            return self._context_manager._count_tokens(context_string) # Delegate to ContextManager
        else:
            logger.warning("ContextManager not initialized. Using fallback context token counting.")
            return len(context_string) // 4 # Original fallback

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
        if agent_config.LOG_FULL_PROMPTS:
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

    def _analyze_conversation_structure(self, contents: List) -> Dict[str, Any]:
        """
        Analyze the conversation structure to identify tool execution flows and conversation boundaries.
        
        Returns a dictionary with:
        - current_tool_chains: Active/incomplete tool execution flows 
        - completed_conversations: Finished conversation segments
        - current_user_message: The current user request
        - system_messages: System-level messages to preserve
        """
        analysis = {
            'current_tool_chains': [],
            'completed_conversations': [],
            'current_user_message': None,
            'system_messages': [],
            'context_injections': []
        }
        
        i = 0
        while i < len(contents):
            content = contents[i]
            
            if content.role == "system":
                analysis['system_messages'].append(content)
                
            elif content.role == "user":
                # Check if this is our context injection
                if (content.parts and len(content.parts) == 1 and 
                    hasattr(content.parts[0], 'text') and content.parts[0].text and
                    content.parts[0].text.startswith("SYSTEM CONTEXT (JSON):")):
                    analysis['context_injections'].append(content)
                else:
                    # This could be current user message or conversation history
                    # Look ahead to see if there's a tool execution flow
                    tool_chain = self._extract_tool_chain_from_position(contents, i)
                    if tool_chain['is_current_or_active']:
                        analysis['current_user_message'] = content
                        analysis['current_tool_chains'].extend(tool_chain['chain'])
                        i += len(tool_chain['chain'])  # Skip processed items
                    else:
                        # This is historical conversation
                        conversation_segment = self._extract_conversation_segment(contents, i)
                        analysis['completed_conversations'].append(conversation_segment)
                        i += len(conversation_segment) - 1  # Skip processed items
                        
            elif content.role == "assistant":
                # Assistant messages are usually part of tool chains or responses
                # They should be handled by the tool chain analysis above
                # If we encounter a standalone assistant message, it's likely historical
                analysis['completed_conversations'].append([content])
                
            i += 1
            
        return analysis
    
    def _extract_tool_chain_from_position(self, contents: List, start_pos: int) -> Dict[str, Any]:
        """
        Extract a complete tool execution chain starting from a user message.
        
        Pattern: user_message -> assistant_with_tool_calls -> tool_results -> assistant_response
        """
        chain = []
        is_current_or_active = False
        i = start_pos
        
        # Start with the user message
        if i < len(contents):
            chain.append(contents[i])
            i += 1
        
        # Look for assistant responses with tool calls
        while i < len(contents) and contents[i].role == "assistant":
            assistant_msg = contents[i]
            chain.append(assistant_msg)
            
            # Check if this assistant message contains function calls (indicates active tool usage)
            has_function_calls = False
            if hasattr(assistant_msg, 'parts') and assistant_msg.parts:
                for part in assistant_msg.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        has_function_calls = True
                        is_current_or_active = True
                        break
            
            # If this is at the end of the conversation, it's likely current
            if i == len(contents) - 1:
                is_current_or_active = True
                
            i += 1
        
        # Check if chain is incomplete (no final assistant response), indicating active flow
        if len(chain) > 1 and not is_current_or_active:
            # Look for patterns that suggest this is an active conversation
            last_message = chain[-1]
            if (hasattr(last_message, 'parts') and last_message.parts and
                any(hasattr(part, 'function_call') for part in last_message.parts if hasattr(part, 'function_call'))):
                is_current_or_active = True
        
        return {
            'chain': chain,
            'is_current_or_active': is_current_or_active,
            'has_tool_calls': any(self._message_has_tool_calls(msg) for msg in chain)
        }
    
    def _extract_conversation_segment(self, contents: List, start_pos: int) -> List:
        """Extract a complete conversation segment (user + assistant response(s))."""
        segment = []
        i = start_pos
        
        # Add the user message
        if i < len(contents) and contents[i].role == "user":
            segment.append(contents[i])
            i += 1
            
        # Add following assistant responses until we hit another user message or end
        while i < len(contents) and contents[i].role == "assistant":
            segment.append(contents[i])
            i += 1
            
        return segment
    
    def _apply_smart_conversation_filtering(self, llm_request: LlmRequest, user_message_content: str) -> None:
        """
        Apply sophisticated conversation history filtering that preserves tool flows.
        """
        if not hasattr(llm_request, 'contents') or not isinstance(llm_request.contents, list):
            logger.info("🔧 No contents to filter")
            return
            
        original_count = len(llm_request.contents)
        logger.info(f"🔧 SMART FILTERING: Analyzing {original_count} conversation contents...")
        
        # Analyze conversation structure
        analysis = self._analyze_conversation_structure(llm_request.contents)
        
        logger.info(f"🔧 ANALYSIS RESULTS:")
        logger.info(f"  📋 System messages: {len(analysis['system_messages'])}")
        logger.info(f"  🧩 Context injections: {len(analysis['context_injections'])}")
        logger.info(f"  🔧 Current tool chains: {len(analysis['current_tool_chains'])}")
        logger.info(f"  📚 Completed conversations: {len(analysis['completed_conversations'])}")
        logger.info(f"  👤 Current user message: {'Yes' if analysis['current_user_message'] else 'No'}")
        
        # Build filtered contents list
        filtered_contents = []
        
        # 1. Always keep system messages
        filtered_contents.extend(analysis['system_messages'])
        logger.info(f"🔧 PRESERVED: {len(analysis['system_messages'])} system messages")
        
        # 2. Keep context injections
        filtered_contents.extend(analysis['context_injections'])
        logger.info(f"🔧 PRESERVED: {len(analysis['context_injections'])} context injections")
        
        # 3. Keep current tool chains (active tool execution flows)
        active_chain_count = 0
        for chain in analysis['current_tool_chains']:
            if isinstance(chain, list):
                filtered_contents.extend(chain)
                active_chain_count += len(chain)
            else:
                filtered_contents.append(chain)
                active_chain_count += 1
        logger.info(f"🔧 PRESERVED: {active_chain_count} messages from active tool chains")
        
        # 4. Keep current user message if not already included
        if analysis['current_user_message'] and analysis['current_user_message'] not in filtered_contents:
            filtered_contents.append(analysis['current_user_message'])
            logger.info(f"🔧 PRESERVED: Current user message")
        
        # 5. Selectively keep recent completed conversations based on token budget
        conversation_limit = 2  # Keep last 2 completed conversation segments
        kept_conversations = 0
        total_conversation_messages = 0
        
        # Keep most recent completed conversations
        for conversation in reversed(analysis['completed_conversations'][-conversation_limit:]):
            if isinstance(conversation, list):
                # Check if this conversation has tool calls (higher priority)
                has_tools = any(self._message_has_tool_calls(msg) for msg in conversation)
                if has_tools or kept_conversations < 1:  # Always keep at least 1, prioritize tool conversations
                    filtered_contents.extend(conversation)
                    total_conversation_messages += len(conversation)
                    kept_conversations += 1
                    logger.info(f"🔧 PRESERVED: Recent conversation segment with {len(conversation)} messages (has_tools: {has_tools})")
                else:
                    logger.info(f"🔧 FILTERED: Older conversation segment with {len(conversation)} messages")
            else:
                # Single message conversation
                filtered_contents.append(conversation)
                total_conversation_messages += 1
                logger.info(f"🔧 PRESERVED: Single conversation message")
        
        # Apply the filtered contents
        llm_request.contents = filtered_contents
        new_count = len(filtered_contents)
        
        # Log filtering results
        logger.info(f"🔧 SMART FILTERING COMPLETE:")
        logger.info(f"  📊 Original contents: {original_count}")
        logger.info(f"  📊 Filtered contents: {new_count}")
        reduction_count = original_count - new_count
        reduction_pct = (reduction_count / original_count * 100) if original_count > 0 else 0.0
        logger.info(f"  📊 Reduction: {reduction_count} messages ({reduction_pct:.1f}%)")
        logger.info(f"  ✅ Tool flows preserved: Active chains maintained")
        logger.info(f"  ✅ Recent context preserved: {kept_conversations} conversation segments")
        
        return

    # 6. Retry and Error Handling Helpers

    def _is_retryable_error(self, error_message: str, error_type: str) -> bool:
        """
        Determine if an error is retryable based on error message and type.
        
        Args:
            error_message: The error message string
            error_type: The error type name
            
        Returns:
            True if the error should be retried, False otherwise
        """
        error_message_lower = error_message.lower()
        
        # API rate limiting and quota errors
        if any(pattern in error_message for pattern in ["429", "RESOURCE_EXHAUSTED", "quota", "rate limit"]):
            return True
            
        # Temporary server errors
        if any(pattern in error_message for pattern in ["500", "502", "503", "504", "INTERNAL", "ServerError", "timeout"]):
            return True
            
        # Network and connection errors
        if any(pattern in error_message_lower for pattern in ["connection", "network", "timeout", "unreachable"]):
            return True
            
        # JSON parsing errors (often due to malformed responses)
        if "json" in error_type.lower() or "json" in error_message_lower:
            return True
            
        # Token limit errors (can be resolved with context optimization)
        if any(pattern in error_message_lower for pattern in ["token", "context length", "too long", "maximum context"]):
            return True
            
        # Specific Google API errors that are retryable
        if any(pattern in error_message for pattern in ["DEADLINE_EXCEEDED", "UNAVAILABLE", "ABORTED"]):
            return True
            
        # Non-retryable errors
        non_retryable_patterns = [
            "PERMISSION_DENIED", "UNAUTHENTICATED", "INVALID_ARGUMENT", 
            "NOT_FOUND", "ALREADY_EXISTS", "FAILED_PRECONDITION",
            "authentication", "authorization", "invalid api key",
            "model not found", "unsupported"
        ]
        
        if any(pattern in error_message_lower for pattern in non_retryable_patterns):
            return False
            
        # Default to non-retryable for unknown errors to prevent infinite loops
        logger.warning(f"Unknown error type '{error_type}' with message '{error_message}' - treating as non-retryable")
        return False

    async def _optimize_input_for_retry(self, ctx: InvocationContext, retry_attempt: int) -> bool:
        """
        Optimize input for retry by reducing context size and complexity.
        
        Args:
            ctx: The invocation context
            retry_attempt: The current retry attempt number (1-based)
            
        Returns:
            True if optimization was successful, False otherwise
        """
        try:
            logger.info(f"Agent {self.name}: Optimizing input for retry attempt {retry_attempt}")
            
            # Use state manager for optimization
            if not self._state_manager:
                logger.warning("State manager not available for optimization")
                return False
            
            # Get current state for optimization
            if hasattr(ctx, 'state') and ctx.state:
                # Sync state manager with context
                self._state_manager.sync_from_legacy_state(ctx.state)
            
            # Progressive optimization based on retry attempt
            optimization_applied = False
            
            if retry_attempt == 1:
                # First retry: Reduce context moderately
                logger.info("Agent optimization level 1: Reducing conversation history and code snippets")
                
                # Reduce conversation history using state manager
                if len(self._state_manager.conversation_history) > 2:
                    original_count = len(self._state_manager.conversation_history)
                    self._state_manager.conversation_history = self._state_manager.conversation_history[-2:]
                    logger.info(f"Reduced conversation history from {original_count} to 2 turns")
                    optimization_applied = True
                
                # Reduce code snippets
                if len(self._state_manager.app_state['code_snippets']) > 3:
                    original_count = len(self._state_manager.app_state['code_snippets'])
                    self._state_manager.app_state['code_snippets'] = self._state_manager.app_state['code_snippets'][:3]
                    logger.info(f"Reduced code snippets from {original_count} to 3")
                    optimization_applied = True
                        
            elif retry_attempt == 2:
                # Second retry: Aggressive reduction
                logger.info("Agent optimization level 2: Aggressive context reduction")
                
                # Keep only the last conversation turn
                if len(self._state_manager.conversation_history) > 1:
                    original_count = len(self._state_manager.conversation_history)
                    self._state_manager.conversation_history = self._state_manager.conversation_history[-1:]
                    logger.info(f"Reduced conversation history from {original_count} to 1 turn")
                    optimization_applied = True
                
                # Remove all code snippets
                if self._state_manager.app_state['code_snippets']:
                    self._state_manager.app_state['code_snippets'] = []
                    logger.info("Removed all code snippets")
                    optimization_applied = True
                
                # Remove tool results from current turn
                if self._state_manager.current_turn and self._state_manager.current_turn.tool_results:
                    self._state_manager.current_turn.tool_results = []
                    logger.info("Removed tool results from current turn")
                    optimization_applied = True
                    
            elif retry_attempt >= 3:
                # Third+ retry: Minimal context
                logger.info("Agent optimization level 3+: Minimal context")
                
                # Keep only current turn
                self._state_manager.conversation_history = []
                if self._state_manager.current_turn:
                    # Keep only user message, remove everything else
                    user_msg = self._state_manager.current_turn.user_message
                    self._state_manager.current_turn = TurnState(
                        turn_number=1,
                        user_message=user_msg,
                        phase=TurnPhase.PROCESSING_USER_INPUT
                    )
                
                # Clear all app state
                self._state_manager.app_state = {
                    'code_snippets': [],
                    'core_goal': '',
                    'current_phase': '',
                    'key_decisions': [],
                    'last_modified_files': []
                }
                logger.info("Applied minimal context optimization")
                optimization_applied = True
            
            # Also reduce the context manager's target limits if available
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
                elif retry_attempt >= 3:
                    self._context_manager.target_recent_turns = 1
                    self._context_manager.target_code_snippets = 0
                    self._context_manager.target_tool_results = 0
                
                logger.info(f"Adjusted context manager limits: turns={self._context_manager.target_recent_turns}, "
                          f"snippets={self._context_manager.target_code_snippets}, results={self._context_manager.target_tool_results}")
                optimization_applied = True
            
            # Update context state if available
            if hasattr(ctx, 'state') and ctx.state:
                ctx.state.update(self._state_manager.get_state_for_context())
                logger.debug("Updated context state after optimization")
            
            logger.info(f"Agent {self.name}: Input optimization for retry attempt {retry_attempt} completed, applied: {optimization_applied}")
            return optimization_applied
                
        except Exception as e:
            logger.error(f"Agent {self.name}: Error during input optimization: {e}", exc_info=True)
            return False

    # 7. Main Execution Logic

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """
        Robust implementation of the agent loop with proper error handling,
        circuit breakers, and retry mechanisms.

        https://google.github.io/adk-docs/agents/custom-agents/#part-2-defining-the-custom-execution-logic
        """
        # Initialize circuit breaker parameters
        max_events_per_attempt = 50  # Increased from 20 to allow for complex operations
        max_retries = 3  # Increased from 2 for better resilience
        max_consecutive_errors = 5  # New: prevent error loops

        retry_count = 0
        consecutive_errors = 0

        try:
            while retry_count <= max_retries:
                event_count = 0
                attempt_start_time = time.time()

                try:
                    logger.info(f"Agent {self.name}: Starting attempt {retry_count + 1}/{max_retries + 1}")

                    # Reset consecutive error counter on successful attempt start
                    consecutive_errors = 0

                    # Process events with circuit breaker
                    async for event in super()._run_async_impl(ctx):
                        event_count += 1

                        # Circuit breaker: prevent infinite event generation
                        if event_count > max_events_per_attempt:
                            logger.error(f"Agent {self.name}: Circuit breaker triggered - too many events ({event_count})")
                            yield Event(
                                author=self.name,
                                content=genai_types.Content(parts=[genai_types.Part(
                                    text="I encountered an internal issue with response generation. The request may be too complex. Please try breaking it into smaller parts."
                                )]),
                                actions=EventActions()
                            )
                            ctx.end_invocation = True
                            return

                        # Check for timeout (prevent hanging)
                        elapsed_time = time.time() - attempt_start_time
                        if elapsed_time > 300:  # 5 minutes timeout per attempt
                            logger.error(f"Agent {self.name}: Attempt timeout after {elapsed_time:.1f} seconds")
                            yield Event(
                                author=self.name,
                                content=genai_types.Content(parts=[genai_types.Part(
                                    text="The request is taking too long to process. Please try a simpler request or break it into smaller parts."
                                )]),
                                actions=EventActions()
                            )
                            ctx.end_invocation = True
                            return

                        yield event

                    # Success - exit retry loop
                    logger.info(f"Agent {self.name}: Successfully completed after {retry_count + 1} attempts")
                    break

                except Exception as e:
                    consecutive_errors += 1
                    error_message = str(e)
                    error_type = type(e).__name__

                    # Check if we've hit too many consecutive errors
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error(f"Agent {self.name}: Too many consecutive errors ({consecutive_errors}), aborting")
                        raise e

                    # Determine if this error is retryable
                    should_retry = self._is_retryable_error(error_message, error_type)

                    if should_retry and retry_count < max_retries:
                        retry_count += 1
                        logger.warning(f"Agent {self.name}: Retryable error on attempt {retry_count}/{max_retries + 1}: {error_type}: {error_message}")

                        # Optimize input for retry
                        optimization_success = await self._optimize_input_for_retry(ctx, retry_count)
                        if not optimization_success:
                            logger.warning(f"Agent {self.name}: Input optimization failed, continuing with retry anyway")

                        # Exponential backoff with jitter
                        import asyncio
                        import random
                        base_delay = min(2 ** retry_count, 30)  # Cap at 30 seconds
                        jitter = random.uniform(0.1, 0.5)  # Add randomness to prevent thundering herd
                        delay = base_delay + jitter
                        
                        logger.info(f"Agent {self.name}: Waiting {delay:.1f} seconds before retry...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Either not retryable or max retries exceeded
                        logger.error(f"Agent {self.name}: Non-retryable error or max retries exceeded: {error_type}: {error_message}")
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
            elif "JSONDecodeError" in error_type or "JSON" in error_message:
                logger.error(f"Agent {self.name}: JSON parsing error after all retry attempts: {error_type}: {error_message}")
                user_facing_error = (
                    f"I encountered a communication issue with the AI service. "
                    f"This appears to be a temporary issue. Please try your request again."
                )
            elif "TypeError" in error_type and ("format" in error_message or "__format__" in error_message):
                logger.error(f"Agent {self.name}: Format string error after all retry attempts: {error_type}: {error_message}")
                user_facing_error = (
                    f"I encountered an internal formatting error while processing your request. "
                    f"This might be due to missing or invalid data in the planning system. "
                    f"Please try rephrasing your request or try again. "
                    f"Details: {error_type}: {error_message}"
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

                # For specific error types, provide more detailed messages
                if "format" in error_message.lower() or "__format__" in error_message:
                    user_facing_error = (
                        f"I encountered a formatting error while processing your request. "
                        f"This typically occurs when the planning system receives unexpected input. "
                        f"Details: {error_type}: {error_message}. Please try rephrasing your request."
                    )
                elif "retryable error" in error_message.lower():
                    user_facing_error = (
                        f"I encountered an issue that couldn't be resolved after multiple attempts. "
                        f"Details: {error_type}: {error_message}. "
                        f"This might be a temporary issue - please try again."
                    )
                else:
                    user_facing_error = (
                        f"I encountered an unexpected internal issue{mcp_related_hint}. "
                        f"Details: {error_type}: {error_message}. "
                        f"I cannot proceed with this request."
                    )

            yield Event(
                author=self.name,
                content=genai_types.Content(parts=[genai_types.Part(text=user_facing_error)]),
                actions=EventActions()
            )
            # Gracefully end the invocation
            ctx.end_invocation = True

    def _create_thinking_config(self) -> Optional[genai_types.ThinkingConfig]:
        """Create thinking configuration if thinking is enabled and supported for the current model."""
        model_name = self.model or agent_config.DEFAULT_AGENT_MODEL

        if not agent_config.should_enable_thinking(model_name):
            return None

        logger.info(f"Creating thinking configuration for model {model_name}")
        logger.info(f"  Include thoughts: {agent_config.GEMINI_THINKING_INCLUDE_THOUGHTS}")
        logger.info(f"  Thinking budget: {agent_config.GEMINI_THINKING_BUDGET}")

        return genai_types.ThinkingConfig(
            include_thoughts=agent_config.GEMINI_THINKING_INCLUDE_THOUGHTS,
            thinking_budget=agent_config.GEMINI_THINKING_BUDGET
        )
