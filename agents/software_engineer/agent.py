"""Software Engineer Agent Implementation using Ollama and Llama 3.2."""

import logging

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import load_memory
import litellm

from . import config as agent_config, prompt
from .shared_libraries.callbacks import create_enhanced_telemetry_callbacks
from .sub_agents.code_quality.agent import code_quality_agent
from .sub_agents.code_review.agent import code_review_agent
from .sub_agents.debugging.agent import debugging_agent
from .sub_agents.design_pattern.agent import design_pattern_agent
from .sub_agents.devops.agent import devops_agent
from .sub_agents.documentation.agent import documentation_agent
from .sub_agents.ollama.agent import ollama_agent
from .sub_agents.testing.agent import testing_agent
from .tools.setup import load_all_tools_and_toolsets

# litellm.turn_off_message_logging()

logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Load tools synchronously (MCP tools will be loaded later if in async context)
tools = load_all_tools_and_toolsets()

# Create telemetry callbacks for observability
callbacks = create_enhanced_telemetry_callbacks("software_engineer")

# REF: https://google.github.io/adk-docs/agents/models/#ollama-integration
# Create the agent using LiteLlm wrapper for Ollama integration
root_agent = Agent(
    # model=LiteLlm(model="ollama_chat/llama3.2"),  # Use ollama_chat provider with LiteLlm
    model=LiteLlm(
        model=f"gemini/{agent_config.DEFAULT_AGENT_MODEL}",
        generate_content_config=agent_config.MAIN_LLM_GENERATION_CONFIG,
    ),  # Use ollama_chat provider with LiteLlm
    # model="gemini-2.5-flash-preview-05-20",  # Changed from Ollama to Gemini to match sub-agents
    name="software_engineer",
    description="An AI software engineer assistant that helps with various software development tasks",
    instruction=prompt.SOFTWARE_ENGINEER_INSTR,
    sub_agents=[
        # Ordered by typical workflow dependencies
        design_pattern_agent,  # 1. Architecture and design decisions
        code_review_agent,  # 2. Code analysis and implementation guidance
        code_quality_agent,  # 3. Quality validation and improvement suggestions
        testing_agent,  # 4. Test strategy and implementation
        debugging_agent,  # 5. Issue identification and resolution
        documentation_agent,  # 6. Documentation after code stabilization
        devops_agent,  # 7. Deployment and operational considerations
        ollama_agent,  # 8. Local model sandbox environment
    ],
    tools=tools,
    # Add telemetry callbacks for observability
    before_agent_callback=callbacks["before_agent"],
    after_agent_callback=callbacks["after_agent"],
    before_model_callback=callbacks["before_model"],
    after_model_callback=callbacks["after_model"],
    before_tool_callback=callbacks["before_tool"],
    after_tool_callback=callbacks["after_tool"],
    # before_agent_callback=load_project_context,
    output_key="software_engineer",
)
