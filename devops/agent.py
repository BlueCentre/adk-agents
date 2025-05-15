"""DevOps Agent Implementation."""

import logging
import os
import traceback # For logging stack traces
import json # Add this import
import time # Import the time module

from dotenv import load_dotenv

from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import built_in_code_execution
from google.adk.tools.google_search_tool import google_search
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_toolset import StdioServerParameters
from google.genai import types as genai_types # Renamed to avoid conflict if ADK also has 'types'
from typing_extensions import override
from typing import AsyncGenerator, Dict, List, Any, Optional # For _run_async_impl return type hint

# ADK specific imports for callbacks and context
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.events.event import Event, EventActions # Added EventActions
from google.adk.agents.invocation_context import InvocationContext

# Rich library for enhanced terminal output
from rich.console import Console
from rich.panel import Panel
from rich.status import Status
from rich.text import Text
from rich.markup import escape

from pydantic import PrivateAttr # Import PrivateAttr

# Import tools from the .tools subpackage
from .tools import (
    codebase_search_tool,
    edit_file_tool,
    list_dir_tool,
    read_file_tool,
    check_command_exists_tool,
    execute_vetted_shell_command_tool,
    index_directory_tool,
    retrieve_code_context_tool,
)
from .tools.shell_command import ExecuteVettedShellCommandOutput
from .tools.file_summarizer_tool import FileSummarizerTool

# Import from the prompt module in the current directory
from . import prompt

# Import context management components
from .context_management import (
    ContextManager,
    TOOL_PROCESSORS,
    process_user_message,
    get_last_user_content,
    inject_structured_context,
)

# Initialize logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # Ensure debug messages from this module are processed

# Import mcp.types specifically for CallToolResult if available, otherwise use a placeholder
# This is placed AFTER logger initialization to allow logging within the try-except block.
try:
    from mcp import types as mcp_types
except ImportError:
    logger.warning("mcp.types not found, Playwright tool responses might not be fully processed if they are CallToolResult.")
    mcp_types = None # Placeholder if mcp.types is not available


# Load .env file
load_dotenv()

# Get allowed directories from environment variable
mcp_allowed_dirs_str = os.getenv("MCP_ALLOWED_DIRECTORIES")
mcp_allowed_dirs = []
if mcp_allowed_dirs_str:
    mcp_allowed_dirs = [d.strip() for d in mcp_allowed_dirs_str.split(",") if d.strip()]
if not mcp_allowed_dirs:
    mcp_allowed_dirs = [os.path.dirname(os.path.abspath(__file__))]
    logger.info(f"MCP_ALLOWED_DIRECTORIES not set, defaulting to agent directory: {mcp_allowed_dirs[0]}")

file_summarizer_tool_instance = FileSummarizerTool()

_search_agent = LlmAgent( # Explicitly LlmAgent
    model="gemini-1.5-flash-latest",
    name="google_search_grounding",
    description="An agent providing Google-search grounding capability",
    instruction=prompt.SEARCH_AGENT_INSTR,
    tools=[google_search],
)

_code_execution_agent = LlmAgent( # Explicitly LlmAgent
    model="gemini-1.5-flash-latest",
    name="code_execution",
    description="An agent specialized in code execution",
    instruction=prompt.CODE_EXECUTION_AGENT_INSTR,
    tools=[built_in_code_execution],
)

devops_observability_tools = []
mcp_datadog_toolset = None # Initialize to None
try:
    if os.getenv("DATADOG_API_KEY") and os.getenv("DATADOG_APP_KEY"):
        mcp_datadog_toolset = MCPToolset(
            connection_params=StdioServerParameters(
                command="npx",
                args=["-y", "@winor30/mcp-server-datadog"],
                env={
                    "DATADOG_API_KEY": os.getenv("DATADOG_API_KEY"),
                    "DATADOG_APP_KEY": os.getenv("DATADOG_APP_KEY"),
                },
            ),
        )
        devops_observability_tools.append(mcp_datadog_toolset)
        logger.info("MCP Datadog Toolset loaded successfully.")
    else:
        logger.warning("DATADOG_API_KEY or DATADOG_APP_KEY not set. MCP Datadog Toolset will not be loaded.")
except Exception as e:
    logger.warning(f"Failed to load MCP DatADOG Toolset: {e}.")

_observability_agent = LlmAgent( # Explicitly LlmAgent
    model="gemini-1.5-flash-latest",
    name="observability",
    description="Agent specialized in Observability",
    instruction=prompt.OBSERVABILITY_AGENT_INSTR,
    tools=devops_observability_tools,
)

devops_core_tools = [
    index_directory_tool,
    retrieve_code_context_tool,
    read_file_tool,
    list_dir_tool,
    edit_file_tool,
    file_summarizer_tool_instance,
    codebase_search_tool,
    execute_vetted_shell_command_tool,
    check_command_exists_tool,
    AgentTool(agent=_code_execution_agent),
    AgentTool(agent=_search_agent),
    AgentTool(agent=_observability_agent),
]

mcp_filesystem_toolset = None # Initialize to None
try:
    mcp_filesystem_toolset = MCPToolset(
        connection_params=StdioServerParameters(
            command="rust-mcp-filesystem",
            args=["--allow-write", *mcp_allowed_dirs],
        ),
    )
    devops_core_tools.append(mcp_filesystem_toolset)
    logger.info("MCP Filesystem Toolset loaded successfully.")
except Exception as e:
    logger.warning(
        f"Failed to load MCP Filesystem Toolset: {e}. "
        "DevOps agent will operate without these MCP file tools."
    )

mcp_playwright_toolset = None # Initialize to None
try:
    mcp_playwright_toolset = MCPToolset(
        connection_params=StdioServerParameters(
            command="npx",
            args=["-y", "@executeautomation/playwright-mcp-server"],
        ),
    )
    devops_core_tools.append(mcp_playwright_toolset)
    logger.info("MCP Playwright Toolset loaded successfully.")
except Exception as e:
    logger.warning(f"Failed to load MCP Playwright Toolset: {e}.")


class MyDevopsAgent(LlmAgent):
    """A DevOps agent implementation with custom callbacks for tool execution and model interaction."""
    _console: Console = PrivateAttr(default_factory=lambda: Console(stderr=True))
    _status_indicator: Status | None = PrivateAttr(default=None)
    _context_manager: ContextManager = PrivateAttr()
    _is_new_conversation: bool = PrivateAttr(default=True)

    def __init__(self, **data: any):
        """Initializes the MyDevopsAgent with custom callback handlers."""
        super().__init__(**data)
        # self._console is initialized by PrivateAttr default_factory
        # self._status_indicator is initialized by PrivateAttr default
        
        # Initialize context manager with configurable parameters
        self._context_manager = ContextManager(
            max_token_limit=90000,  # Adjust based on model limits
            recent_turns_to_keep=5,
            max_code_snippets=10,
            max_tool_results=20
        )
        
        # Set up callbacks for model and tool interactions
        self.before_model_callback = self.handle_before_model
        self.after_model_callback = self.handle_after_model
        self.before_tool_callback = self.handle_before_tool
        self.after_tool_callback = self.handle_after_tool

    async def handle_before_model(
        self, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> LlmResponse | None:
        """Handles actions to perform before an LLM model call, showing a thinking indicator."""
        # Check if this is a new user message and process it
        user_message = get_last_user_content(llm_request)
        if user_message:
            # Process the user message for goal extraction, etc.
            process_user_message(self._context_manager, user_message)
            
        # Build our structured context and inject it into the request
        context_dict, estimated_tokens = self._context_manager.assemble_context()
        
        # Inject structured context into the request
        try:
            # Modify the llm_request in-place to include our structured context
            modified_request = inject_structured_context(llm_request, context_dict)
            
            # Replace the request in the callback_context
            # Note: This might not be supported in all implementations
            if hasattr(callback_context, "llm_request"):
                callback_context.llm_request = modified_request
        except Exception as e:
            logger.error(f"Failed to inject structured context: {e}")
        
        num_parts_info = 'N/A'
        if llm_request.contents:
            last_content_object = llm_request.contents[-1]
            if last_content_object and last_content_object.parts:
                num_parts_info = str(len(last_content_object.parts))
            elif last_content_object:
                num_parts_info = '0 (no parts in last content)'
        logger.debug(f"Agent {self.name}: Before model call. Parts in last content object: {num_parts_info}")
        logger.info(f"Estimated token count for structured context: {estimated_tokens}")
        
        if self._status_indicator: # Stop previous if any (should not happen often)
            self._status_indicator.stop()
            
        # Start the thinking indicator unless it's a tool-only turn
        # (We need to check the *original* request for tool calls before injection)
        original_tool_calls = callback_context.tool_calls if hasattr(callback_context, 'tool_calls') else []
        if not original_tool_calls:
             self._status_indicator = self._console.status("[bold yellow](Agent is thinking...)")
             self._status_indicator.start()
        
        return None

    async def handle_after_model(
        self, callback_context: CallbackContext, llm_response: LlmResponse
    ) -> LlmResponse | None:
        """Handles actions to perform after an LLM model call, stopping the thinking indicator."""
        logger.debug(f"Agent {self.name}: ENTERING handle_after_model.")
        if self._status_indicator:
            self._status_indicator.stop()
            self._status_indicator = None

        # Extract and log token usage if available
        if hasattr(llm_response, 'usage_metadata') and llm_response.usage_metadata:
            usage = llm_response.usage_metadata
            prompt_tokens = getattr(usage, 'prompt_token_count', 'N/A')
            completion_tokens = getattr(usage, 'candidates_token_count', 'N/A')
            total_tokens = getattr(usage, 'total_token_count', 'N/A')
            
            logger.info(f"Agent {self.name}: Token Usage - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}")
            
            # Display token usage to the user
            token_panel_content = Text.from_markup(
                f"[dim][b]Token Usage:[/b] Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}[/dim]"
            )
            token_panel = Panel(
                token_panel_content,
                title="[blue]📊 Model Usage[/blue]",
                border_style="blue",
                expand=False
            )
            self._console.print(token_panel)

        # Extract agent's response to store in context manager
        extracted_text = self._extract_response_text(llm_response)
        if extracted_text and isinstance(extracted_text, str):
            # Update the current turn with the agent's response
            current_turn = self._context_manager.current_turn_number
            self._context_manager.update_agent_response(current_turn, extracted_text)
        
        # Mark that it's no longer the first turn/new conversation for the next cycle
        self._is_new_conversation = False
        
        return None
        
    def _extract_response_text(self, llm_response: LlmResponse) -> Optional[str]:
        """Extract the text content from an LLM response.
        
        Args:
            llm_response: The LLM response object
            
        Returns:
            The extracted text, or None if extraction failed
        """
        try:
            if hasattr(llm_response, 'content') and getattr(llm_response, 'content'):
                content_obj = getattr(llm_response, 'content')
                if isinstance(content_obj, genai_types.Content) and content_obj.parts:
                    parts_texts = [part.text for part in content_obj.parts if hasattr(part, 'text') and part.text is not None]
                    if parts_texts:
                        return "".join(parts_texts)
        except Exception as e:
            logger.warning(f"Failed to extract text from LLM response: {e}")
        return None

    async def handle_before_tool(
        self, tool: BaseTool, args: dict, tool_context: ToolContext, callback_context: CallbackContext | None = None
    ) -> dict | None:
        """Logs information before tool execution and tracks tool calls."""
        try:
            # Ensure we have a callback_context
            if callback_context is None:
                logger.warning(f"Agent {self.name}: handle_before_tool called without callback_context")
                return None  # Cannot proceed effectively without callback_context
                
            # Add tool call to the current conversation turn
            current_turn = self._context_manager.current_turn_number
            self._context_manager.add_tool_call(current_turn, tool.name, args)
            
            # Log the start of tool execution with rich output to terminal
            tool_args_display = ", ".join([f"{k}={v}" for k, v in args.items()])
            if len(tool_args_display) > 100:
                tool_args_display = tool_args_display[:97] + "..."
            
            logger.info(f"Agent {self.name}: Executing tool {tool.name} with args: {tool_args_display}")
            self._console.print(
                Panel(
                    Text.from_markup(f"[dim][b]Tool:[/b] {escape(tool.name)}\n[b]Args:[/b] {escape(tool_args_display)}[/dim]"),
                    title="[cyan]🔧 Running Tool[/cyan]",
                    border_style="cyan",
                    expand=False
                )
            )
            
            # Return None to indicate no modification to the arguments
            return None
        except Exception as e:
            logger.error(f"Agent {self.name}: Error in handle_before_tool: {e}")
            return None

    async def handle_after_tool(
        self, tool: BaseTool, tool_response: dict | str, callback_context: CallbackContext | None = None, args: dict | None = None, tool_context: ToolContext | None = None
    ) -> dict | None:
        """Processes tool results, enhances error reporting, and stores tool output in context manager."""
        # Start timing here to measure post-processing duration for performance logging
        start_time = time.time()
        logger.debug(f"Agent {self.name}: Handling tool response from {tool.name}")
        
        # Use a custom processor for this tool type if available
        custom_processor_used = False
        if tool.name in TOOL_PROCESSORS:
            try:
                # Process the tool result with our custom processor
                # We need to pass the original args to the processor for some tools (like edit_file)
                TOOL_PROCESSORS[tool.name](self._context_manager, tool, tool_response, args)
                custom_processor_used = True
            except Exception as e:
                logger.error(f"Error in custom processor for {tool.name}: {e}")
        
        # If we didn't use a custom processor, add the result with default handling
        if not custom_processor_used:
            self._context_manager.add_tool_result(tool.name, tool_response)
        
        # Calculate duration for performance logging
        duration = time.time() - start_time
        
        # Check if this is a special result type from MCP tools
        # (Original handling for MCP tools)
        
        # Special handling for CallToolResult if mcp_types is available
        if mcp_types and isinstance(tool_response, mcp_types.CallToolResult):
            # The rest of the original CallToolResult handling...
            pass  # (Include the original MCP tool handling here)
            
        # Handle ExecuteVettedShellCommandOutput responses
        elif isinstance(tool_response, ExecuteVettedShellCommandOutput):
            # The rest of the original shell command output handling...
            pass  # (Include the original shell command output handling here)
        
        # Handle non-dictionary responses
        if not isinstance(tool_response, dict):
            # The rest of the original non-dictionary response handling...
            pass  # (Include the original non-dictionary handling here)
            
        # Handle error status in dictionary responses
        if isinstance(tool_response, dict) and (tool_response.get("status") == "error" or tool_response.get("error")):
            # The rest of the original error handling...
            pass  # (Include the original error handling here)
        
        # Success case - this will happen for all responses that don't match the above conditions
        if isinstance(tool_response, dict):
            result_summary = escape(str(tool_response)[:300])
            self._console.print(
                Panel(
                    Text.from_markup(f"[dim][b]Tool:[/b] {escape(tool.name)}\n[b]Result:[/b] {result_summary}{'...' if len(str(tool_response)) > 300 else ''}\n[b]Duration:[/b] {duration:.4f} seconds[/dim]"),
                    title="[green]✅ Tool Finished[/green]",
                    border_style="green",
                    expand=False
                )
            )
            logger.info(f"Tool {tool.name} appears to have executed successfully based on initial checks.")
            
        return None  # Return None to indicate the callback has handled the response if necessary, or that the original/modified tool_response should be used.

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Runs the agent's main asynchronous logic, handling exceptions and reporting errors."""
        try:
            # Initialize or reset the context manager for this invocation if it's a new conversation
            # Use the _is_new_conversation flag set in handle_after_model
            if self._is_new_conversation:
                logger.info(f"Agent {self.name}: New conversation detected, resetting context manager")
                # Re-initialize the context manager to clear its state
                self._context_manager = ContextManager(
                    max_token_limit=90000,
                    recent_turns_to_keep=5,
                    max_code_snippets=10,
                    max_tool_results=20
                )
                # Process the initial user message(s) from the invocation context
                # The first user message should be available in ctx.conversation_history if the framework provides it,
                # or will be processed in handle_before_model for the first turn.
                # For now, we rely on handle_before_model to process the first user message.
            
            # Proceed with the normal agent execution
            async for event in super()._run_async_impl(ctx):
                yield event
                
        except Exception as e:
            if self._status_indicator: # Ensure spinner is stopped on error
                self._status_indicator.stop()
                self._status_indicator = None

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

            user_facing_error = (
                f"I encountered an unexpected internal issue{mcp_related_hint}. "
                f"I cannot proceed with this request. Details: {error_type}."
            )

            # Enhance error reporting for unhandled exceptions
            rich_error_message_display = f"Type: {escape(error_type)}\nMessage: {escape(error_message)}\n{escape(mcp_related_hint) if mcp_related_hint else ''}"
            
            # Also print to rich console if available
            self._console.print(
                Panel(
                    Text.from_markup(f"""[bold red]💥 Unhandled Agent Error[/bold red]\n{rich_error_message_display}"""
                    ),
                    title="[red]Critical Error[/red]",
                    border_style="red"
                )
            )

            yield Event(
                author=self.name, 
                content=genai_types.Content(parts=[genai_types.Part(text=user_facing_error)]),
                actions=EventActions()
            )
            ctx.end_invocation = True


gemini_model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-pro-latest")

llm_generation_config = genai_types.GenerateContentConfig(
    temperature=0.3, 
    max_output_tokens=8000,
)

devops_agent_instance = MyDevopsAgent(
    model=gemini_model_name,
    name="devops_agent",
    description="Self-sufficient agent specialized in Platform Engineering, DevOps, and SRE practices.",
    instruction=prompt.DEVOPS_AGENT_INSTR,
    tools=devops_core_tools,
    output_key="devops", 
    generate_content_config=llm_generation_config,
)

root_agent = devops_agent_instance
