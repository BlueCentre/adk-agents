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
from typing import AsyncGenerator # For _run_async_impl return type hint

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

    def __init__(self, **data: any):
        """Initializes the MyDevopsAgent with custom callback handlers."""
        super().__init__(**data)
        # self._console is initialized by PrivateAttr default_factory
        # self._status_indicator is initialized by PrivateAttr default
        self.before_model_callback = self.handle_before_model
        self.after_model_callback = self.handle_after_model
        self.before_tool_callback = self.handle_before_tool
        self.after_tool_callback = self.handle_after_tool

    async def handle_before_model(
        self, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> LlmResponse | None:
        """Handles actions to perform before an LLM model call, showing a thinking indicator."""
        num_parts_info = 'N/A'
        if llm_request.contents:
            last_content_object = llm_request.contents[-1]
            if last_content_object and last_content_object.parts:
                num_parts_info = str(len(last_content_object.parts))
            elif last_content_object:
                num_parts_info = '0 (no parts in last content)'
        logger.debug(f"Agent {self.name}: Before model call. Parts in last content object: {num_parts_info}")
        
        if self._status_indicator: # Stop previous if any (should not happen often)
            self._status_indicator.stop()
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

        extracted_text_for_log = "N/A (extraction failed)"
        try:
            if hasattr(llm_response, 'content') and getattr(llm_response, 'content'):
                content_obj = getattr(llm_response, 'content')
                if isinstance(content_obj, genai_types.Content) and content_obj.parts:
                    parts_texts = [part.text for part in content_obj.parts if hasattr(part, 'text') and part.text is not None]
                    if parts_texts:
                        extracted_text_for_log = "".join(parts_texts)
                    else:
                        logger.debug("llm_response.content.parts was empty or parts had no text.")
                        extracted_text_for_log = "N/A (empty parts or no text in parts)"
                else:
                    logger.debug(f"llm_response.content is not a Content object or has no parts. Type: {type(content_obj)}")
                    extracted_text_for_log = "N/A (content not Content type or no parts)"
            else:
                logger.debug("llm_response does not have a 'content' attribute or it is None.")
                extracted_text_for_log = "N/A (no content attribute)"
        except Exception as e:
            logger.error(f"Error during text extraction from LlmResponse.content in handle_after_model: {e}", exc_info=True)
            extracted_text_for_log = "N/A (exception during extraction)"

        logger.info(f"Agent {self.name}: LLM Response Text (first 100 chars): {extracted_text_for_log[:100]}")
        return None

    async def handle_before_tool(
        self, tool: BaseTool, args: dict, tool_context: ToolContext, callback_context: CallbackContext | None = None
    ) -> dict | None:
        """Handles actions to perform before a tool call, displaying tool information."""
        logger.debug(f"Agent {self.name}: Before tool call: {tool.name}, Args: {args}")
        if self._status_indicator: # Stop thinking spinner if tool call happens
            self._status_indicator.stop()
            self._status_indicator = None

        # Record start time for performance monitoring
        tool_context.start_time = time.time()

        # Escape args for safe display in Rich markup
        escaped_args_str = escape(str(args))
        
        tool_panel_content = Text.from_markup(f"[dim][b]Tool:[/b] {escape(tool.name)} [b]Arguments:[/b] {escaped_args_str[:300]}{'...' if len(escaped_args_str) > 300 else ''}[/dim]")
        tool_panel = Panel(
            tool_panel_content,
            title="[blue]🔧 Executing Tool[/blue]",
            border_style="blue",
            expand=False
        )
        self._console.print(tool_panel)
        return None

    async def handle_after_tool(
        self, tool: BaseTool, tool_response: dict | str, callback_context: CallbackContext | None = None, args: dict | None = None, tool_context: ToolContext | None = None
    ) -> dict | None:
        """Handles actions to perform after a tool call, processing and displaying the tool response."""
        logger.debug(f"Agent {self.name}: After tool call: {tool.name}, Raw Response: {str(tool_response)[:500]}")

        # Log tool execution duration
        if hasattr(tool_context, 'start_time'):
            duration = time.time() - tool_context.start_time
            logger.info(f"Agent {self.name}: Tool '{tool.name}' executed in {duration:.4f} seconds.")

        # BEGIN: MCP CallToolResult Handling
        if mcp_types and isinstance(tool_response, mcp_types.CallToolResult):
            logger.info(f"Handling mcp.types.CallToolResult from tool {tool.name}")
            combined_text_content = []
            if hasattr(tool_response, 'content') and tool_response.content:
                for item in tool_response.content:
                    if hasattr(item, 'text') and item.text:
                        combined_text_content.append(item.text)
            
            message = " ".join(combined_text_content)
            
            if hasattr(tool_response, 'isError') and tool_response.isError:
                logger.warning(f"Tool {tool.name} (MCP CallToolResult) indicated an error. Message: {message}")
                tool_response = {
                    "status": "error",
                    "tool_name": tool.name,
                    "error_summary": f"Tool {tool.name} reported an error.",
                    "full_error_log_for_llm": f"Tool '{tool.name}' (MCP CallToolResult) failed. Message: {message}",
                    "message": message
                }
            else:
                logger.info(f"Tool {tool.name} (MCP CallToolResult) processed successfully. Message: {message}")
                tool_response = {
                    "status": "success",
                    "tool_name": tool.name,
                    "message": message,
                    "output": message # Adding output for consistency
                }
        # END: MCP CallToolResult Handling

        if isinstance(tool_response, str):
            # Keep existing special handling for index_directory_tool
            if tool.name == 'index_directory_tool':
                self._console.print(
                    Panel(
                        Text.from_markup(f"[dim][b]Tool:[/b] {escape(tool.name)}\n[b]Result:[/b] {escape(tool_response)}[/dim]"),
                        title="[green]✅ Tool Finished[/green]",
                        border_style="green",
                        expand=False
                    )
                )
                return None # Explicitly return None as it's handled

            # Attempt to parse as JSON
            parsed_successfully = False
            try:
                potential_json_string = tool_response.strip()
                # Remove markdown code blocks if present
                if potential_json_string.startswith("```json"):
                    potential_json_string = potential_json_string[len("```json"):]
                elif potential_json_string.startswith("```"):
                    potential_json_string = potential_json_string[len("```"):]
                if potential_json_string.endswith("```"):
                    potential_json_string = potential_json_string[:-len("```")]
                potential_json_string = potential_json_string.strip()
                
                parsed_response = json.loads(potential_json_string)
                if isinstance(parsed_response, dict):
                    tool_response = parsed_response 
                    logger.info(f"Successfully parsed string response from tool {tool.name} into a dictionary.")
                    parsed_successfully = True
                else:
                    logger.warning(f"Tool {tool.name} returned a string that was valid JSON, but not a JSON object. Type: {type(parsed_response)}.")
            except json.JSONDecodeError as e:
                logger.warning(f"Tool {tool.name} returned a string that could not be parsed as JSON. Error: {e}. String (first 200 chars): '{tool_response[:200]}...'.")

            if not parsed_successfully:
                # If parsing failed or it wasn't a dict, and the tool is 'observability'
                if tool.name == "observability":
                    logger.warning(f"Observability tool returned a non-JSON string. Wrapping it for user display: '{tool_response[:200]}...'")
                    # Wrap the string response in a dictionary to pass checks and inform the LLM
                    tool_response = {
                        "status": "clarification_needed", # Using a custom status
                        "tool_name": tool.name,
                        "message_from_observability_agent": tool_response,
                        "details": "The observability agent requires more information or could not directly fulfill the request, returning a textual response."
                    }
                    # This wrapped response will now be a dict and pass the subsequent checks.
                    # The LLM can then decide to present this message to the user.
                # else:
                    # For other tools, if not parsed, it will fall through to the `if not isinstance(tool_response, dict):` error handling below
                    # No change needed here for other tools, they will be caught by the existing error handling

        elif isinstance(tool_response, ExecuteVettedShellCommandOutput):
            logger.info(f"Handling ExecuteVettedShellCommandOutput from tool {tool.name}")
            if tool_response.status == "error" or tool_response.return_code != 0:
                error_message_detail = tool_response.stderr if tool_response.stderr else tool_response.message
                command_executed = tool_response.command_executed
                return_code = tool_response.return_code
                stderr_output = tool_response.stderr
                stdout_output = tool_response.stdout

                # Enhance error reporting for shell commands
                error_summary = f"Command '{command_executed.splitlines()[0][:100]}...' failed with return code {return_code}."
                full_error_log_for_llm = (
                    f"Tool '{tool.name}' (shell command) failed.\n"
                    f"Command: {command_executed}\n"
                    f"Return Code: {return_code}\n"
                    f"Stderr: {stderr_output}\n"
                    f"Stdout: {stdout_output}\n"
                    f"Error Detail: {error_message_detail}"
                )
                
                rich_error_summary = f"Command '[dim]{escape(command_executed.splitlines()[0][:100])}[/dim]...' failed [red]({return_code})[/red]."
                rich_details = f"Stderr: [red]{escape(stderr_output[:300])}[/red]{'...' if len(stderr_output) > 300 else ''}"
                if stdout_output:
                     rich_details += f"\nStdout: [yellow]{escape(stdout_output[:300])}[/yellow]{'...' if len(stdout_output) > 300 else ''}"

                logger.warning(f"Agent {self.name}: {full_error_log_for_llm}")
                self._console.print(
                    Panel(
                        Text.from_markup(f"[b]Tool:[/b] {escape(tool.name)}\n[b]Error:[/b] {rich_error_summary}\n{rich_details}"), 
                        title="[red]❌ Command Failed[/red]", 
                        border_style="red", 
                        expand=False
                    )
                )
                return {
                    "status": "error",
                    "tool_name": tool.name,
                    "error_summary": error_summary,
                    "full_error_log_for_llm": full_error_log_for_llm
                }
            else:
                tool_response = {
                    "status": "success",
                    "tool_name": tool.name,
                    "stdout": tool_response.stdout,
                    "stderr": tool_response.stderr,
                    "return_code": tool_response.return_code,
                    "command_executed": tool_response.command_executed,
                    "message": "Command executed successfully."
                }
                logger.info(f"Tool {tool.name} (shell command) executed successfully. Stdout: {tool_response.get('stdout')}")

        if not isinstance(tool_response, dict):
            llm_error_message = f"Tool '{tool.name}' returned an unexpected response type: {str(type(tool_response))}. Expected a dictionary."
            rich_error_message = f"Tool '{escape(tool.name)}' returned an unexpected response type: {escape(str(type(tool_response)))}. Expected a dictionary."
            logger.error(llm_error_message + f" Full response: {str(tool_response)[:500]}")
            self._console.print(
                Panel(
                    Text.from_markup(f"[b]Tool:[/b] {escape(tool.name)}\n[b]Error:[/b] {rich_error_message}"), 
                    title="[red]❌ Tool Error[/red]", 
                    border_style="red", 
                    expand=False
                )
            )
            return {
                "status": "error",
                "tool_name": tool.name,
                "error_summary": "Tool returned an invalid response format.",
                "full_error_log_for_llm": llm_error_message
            }

        if tool_response.get("status") == "error" or tool_response.get("error"):
            error_val = tool_response.get("error", tool_response.get("message", "Unknown error"))
            details = tool_response.get("details", "")
            tool_name = tool_response.get("tool_name", tool.name)

            # Enhance error reporting for dictionary-based errors
            rich_error_summary = f"The tool {escape(tool_name)} failed with: {escape(str(error_val)[:200])}{'...' if len(str(error_val)) > 200 else ''}"
            rich_details = f"Details: [dim]{escape(str(details)[:300])}[/dim]{'...' if len(str(details)) > 300 else ''}"
            
            llm_full_error = f"Tool '{tool_name}' reported an error: {str(error_val)}."
            if details:
                llm_full_error += f" Details: {details}"
            logger.warning(f"Agent {self.name}: {llm_full_error}")
            self._console.print(
                Panel(
                    Text.from_markup(f"[b]Tool:[/b] {escape(tool.name)}\n[b]Error:[/b] {rich_error_summary}\n{rich_details}"), 
                    title="[red]❌ Tool Error[/red]", 
                    border_style="red", 
                    expand=False
                )
            )
            # If the status is 'clarification_needed' from our special handling above, don't return it as a hard error to the LLM.
            # Instead, let it pass through as a non-error dictionary, so the LLM can see the message.
            if tool_response.get("status") == "clarification_needed":
                logger.info(f"Passing clarification_needed response from {tool.name} to LLM.")
                # No specific rich print here, as the LLM will decide how to present it.
                # The 'None' return will allow the agent framework to use the modified tool_response.
            else:
                return {
                    "status": "error",
                    "tool_name": tool.name,
                    "error_summary": f"The tool {tool.name} failed with: {str(error_val)[:100]}{'...' if len(str(error_val)) > 100 else ''}",
                    "full_error_log_for_llm": llm_full_error
                }
        
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
        return None # Return None to indicate the callback has handled the response if necessary, or that the original/modified tool_response should be used.

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Runs the agent's main asynchronous logic, handling exceptions and reporting errors."""
        try:
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
