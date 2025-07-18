"""Debugging Agent Implementation."""

from google.adk.agents import LlmAgent
from google.genai.types import GenerateContentConfig

from ... import config as agent_config
from ...shared_libraries.callbacks import create_telemetry_callbacks
from ...tools import load_tools_for_sub_agent
from . import prompt

# Load tools using profile-based loading with per-sub-agent MCP configuration
# This demonstrates the new per-sub-agent MCP tool loading system
base_config = {
    "include_mcp_tools": True,
    "mcp_server_filter": ["filesystem", "debugger", "profiler", "monitoring"],
    "include_global_servers": True,
    "excluded_servers": ["production-db", "external-api"],
    "server_overrides": {
        "debugger": {"env": {"DEBUG_MODE": "1", "VERBOSE": "1"}},
        "profiler": {"args": ["--memory-profiling", "--cpu-profiling"]},
    },
}

# Add additional tools based on environment or configuration
if (
    hasattr(agent_config, "ENABLE_ADVANCED_DEBUGGING")
    and agent_config.ENABLE_ADVANCED_DEBUGGING
):
    base_config["included_tools"] = ["profiler_tool", "trace_analyzer_tool"]
    base_config["mcp_server_filter"].extend(["trace-analyzer", "heap-analyzer"])

# Load tools with per-sub-agent MCP configuration
tools = load_tools_for_sub_agent(
    "debugging", base_config, sub_agent_name="debugging_agent"
)

# Create telemetry callbacks for observability
callbacks = create_telemetry_callbacks("debugging_agent")

debugging_agent = LlmAgent(
    model=agent_config.DEFAULT_SUB_AGENT_MODEL,
    name="debugging_agent",
    description="Agent specialized in debugging and troubleshooting code issues",
    instruction=prompt.DEBUGGING_AGENT_INSTR,
    generate_content_config=GenerateContentConfig(
        temperature=0.2,
        top_p=0.95,
        max_output_tokens=4096,
    ),
    tools=tools,
    # Add telemetry callbacks for observability
    before_agent_callback=callbacks["before_agent"],
    after_agent_callback=callbacks["after_agent"],
    before_model_callback=callbacks["before_model"],
    after_model_callback=callbacks["after_model"],
    before_tool_callback=callbacks["before_tool"],
    after_tool_callback=callbacks["after_tool"],
    output_key="debugging",
)
