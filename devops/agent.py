"""DevOps Agent Implementation."""

import logging
import openlit
import os
import asyncio

from google import genai

from .devops_agent import MyDevopsAgent
from .tools.setup import load_all_tools_and_toolsets_async
# from .logging_config import set_interactive_mode

from . import config as agent_config
from . import prompts as agent_prompts

logger = logging.getLogger(__name__)

# Configure logging for interactive mode
# This reduces console noise during interactive agent sessions
# interactive_mode = os.getenv('DEVOPS_AGENT_INTERACTIVE', 'true').lower() in ('true', '1', 'yes')
# set_interactive_mode(interactive_mode)

# Enhanced OpenLIT configuration with GPU monitoring
# https://docs.openlit.io/latest/sdk-configuration
# https://docs.openlit.io/latest/features/metrics
# https://docs.openlit.io/latest/features/tracing
openlit_config = {
    "application_name": "DevOps Agent",
    "environment": os.getenv('OPENLIT_ENVIRONMENT', 'Production'),
    # Enable GPU monitoring if available (disabled by default to avoid warnings on non-GPU systems)
    "collect_gpu_stats": os.getenv('OPENLIT_COLLECT_GPU_STATS', 'false').lower() in ('true', '1', 'yes'),
    # Disable metrics if requested (for rate limiting)
    "disable_metrics": os.getenv('OPENLIT_DISABLE_METRICS', 'false').lower() in ('true', '1', 'yes'),
    # Tracing configuration
    "capture_message_content": os.getenv('OPENLIT_CAPTURE_CONTENT', 'true').lower() in ('true', '1', 'yes'),
    "disable_batch": os.getenv('OPENLIT_DISABLE_BATCH', 'false').lower() in ('true', '1', 'yes'),
    # Disable specific instrumentations if needed (disable some that might cause attribute issues)
    "disabled_instrumentors": os.getenv('OPENLIT_DISABLED_INSTRUMENTORS', 'google_generativeai').split(',') if os.getenv('OPENLIT_DISABLED_INSTRUMENTORS') else ['google_generativeai'],
}

# Set custom resource attributes for better trace context
resource_attributes = {
    "service.instance.id": os.getenv('SERVICE_INSTANCE_ID', f"devops-agent-{os.getpid()}"),
    "service.version": os.getenv('SERVICE_VERSION', '1.0.0'),
    "deployment.environment": openlit_config["environment"],
    "agent.type": "devops",
    "agent.capabilities.shell": "true",
    "agent.capabilities.file": "true", 
    "agent.capabilities.rag": "true",
    "agent.capabilities.planning": "true",
    "agent.capabilities.context": "true",
}

# Add Kubernetes attributes if available
# if os.getenv('K8S_POD_NAME'):
#     resource_attributes.update({
#         "k8s.pod.name": os.getenv('K8S_POD_NAME'),
#         "k8s.namespace.name": os.getenv('K8S_NAMESPACE_NAME', 'default'),
#         "k8s.node.name": os.getenv('K8S_NODE_NAME', 'unknown'),
#     })

# Set OTEL_RESOURCE_ATTRIBUTES environment variable
existing_attrs = os.getenv('OTEL_RESOURCE_ATTRIBUTES', '')
new_attrs = ','.join([f"{k}={v}" for k, v in resource_attributes.items()])
combined_attrs = f"{existing_attrs},{new_attrs}" if existing_attrs else new_attrs
os.environ['OTEL_RESOURCE_ATTRIBUTES'] = combined_attrs

# Initialize OpenLIT with enhanced configuration
openlit.init(**openlit_config)

logger.info(f"OpenLIT initialized: {openlit_config}")
logger.info(f"Resource attributes: {resource_attributes}")

# Create LLM client explicitly
try:
    if agent_config.GOOGLE_API_KEY:
        llm_client = genai.Client(api_key=agent_config.GOOGLE_API_KEY)
        logger.info("Created genai client with API key from configuration")
    else:
        llm_client = genai.Client()
        logger.info("Created default genai client (using default credentials)")
except Exception as e:
    llm_client = None
    logger.error(f"Failed to create genai client: {e}")


async def create_agent():
    """Create the agent instance."""
    tools, exit_stack = await load_all_tools_and_toolsets_async()

    # Create agent instance using the MyDevopsAgent abstraction
    devops_agent_instance = MyDevopsAgent(
        model=agent_config.GEMINI_MODEL_NAME,
        name="devops_agent",
        description="Self-sufficient agent specialized in Platform Engineering, DevOps, and SRE practices.",
        instruction=agent_prompts.DEVOPS_AGENT_INSTR,
        generate_content_config=agent_config.MAIN_LLM_GENERATION_CONFIG,
        tools=tools,
        output_key="devops",
        llm_client=llm_client,
    )
    return devops_agent_instance, exit_stack

# For the custom ADK fork, create the agent instance directly
# MCP tools will be loaded asynchronously when the agent first runs
try:
    # Import the synchronous loading function that handles async context detection
    from .tools.setup import load_all_tools_and_toolsets
    
    # Load tools synchronously (MCP tools will be loaded later if in async context)
    tools = load_all_tools_and_toolsets()
    
    # Create agent instance directly for the custom ADK fork
    root_agent = MyDevopsAgent(
        model=agent_config.GEMINI_MODEL_NAME,
        name="devops_agent",
        description="Self-sufficient agent specialized in Platform Engineering, DevOps, and SRE practices.",
        instruction=agent_prompts.DEVOPS_AGENT_INSTR,
        generate_content_config=agent_config.MAIN_LLM_GENERATION_CONFIG,
        tools=tools,
        output_key="devops",
        llm_client=llm_client,
    )
    
    logger.info(f"Created agent instance directly for custom ADK fork: {root_agent.name}")
    
except Exception as e:
    logger.error(f"Failed to create agent instance: {e}")
    # Fallback to a basic agent without tools
    root_agent = MyDevopsAgent(
        model=agent_config.GEMINI_MODEL_NAME,
        name="devops_agent",
        description="Self-sufficient agent specialized in Platform Engineering, DevOps, and SRE practices.",
        instruction=agent_prompts.DEVOPS_AGENT_INSTR,
        generate_content_config=agent_config.MAIN_LLM_GENERATION_CONFIG,
        tools=[],
        output_key="devops",
        llm_client=llm_client,
    )
