"""DevOps Agent Implementation."""

import logging
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
# interactive_mode = agent_config.DEVOPS_AGENT_INTERACTIVE
# set_interactive_mode(interactive_mode)

# Initialize OpenLIT only if observability is enabled
OBSERVABILITY_ENABLED = agent_config.should_enable_observability()

if OBSERVABILITY_ENABLED:
    import openlit
    
    # Enhanced OpenLIT configuration with GPU monitoring
    # https://docs.openlit.io/latest/sdk-configuration
    # https://docs.openlit.io/latest/features/metrics
    # https://docs.openlit.io/latest/features/tracing
    openlit_config = {
        "application_name": "DevOps Agent",
        "environment": agent_config.OPENLIT_ENVIRONMENT,
        # Enable GPU monitoring if available (disabled by default to avoid warnings on non-GPU systems)
        "collect_gpu_stats": agent_config.OPENLIT_COLLECT_GPU_STATS,
        # Disable metrics if requested (for rate limiting)
        "disable_metrics": agent_config.OPENLIT_DISABLE_METRICS,
        # Tracing configuration
        "capture_message_content": agent_config.OPENLIT_CAPTURE_CONTENT,
        "disable_batch": agent_config.OPENLIT_DISABLE_BATCH,
        # Disable specific instrumentations if needed (disable some that might cause attribute issues)
        # "disabled_instrumentors": agent_config.OPENLIT_DISABLED_INSTRUMENTORS.split(',') if agent_config.OPENLIT_DISABLED_INSTRUMENTORS else ['google_generativeai'],
    }

    # Set custom resource attributes for better trace context
    resource_attributes = {
        "service.instance.id": agent_config.SERVICE_INSTANCE_ID,
        "service.version": agent_config.SERVICE_VERSION,
        "deployment.environment": openlit_config["environment"],
        "agent.type": "devops",
        "agent.capabilities.shell": "true",
        "agent.capabilities.file": "true", 
        "agent.capabilities.rag": "true",
        "agent.capabilities.planning": "true",
        "agent.capabilities.context": "true",
    }

    # Add Kubernetes attributes if available
    # if agent_config.K8S_POD_NAME:
    #     resource_attributes.update({
    #         "k8s.pod.name": agent_config.K8S_POD_NAME,
    #         "k8s.namespace.name": agent_config.K8S_NAMESPACE_NAME,
    #         "k8s.node.name": agent_config.K8S_NODE_NAME,
    #     })

    # Set OTEL_RESOURCE_ATTRIBUTES environment variable
    import os
    existing_attrs = agent_config.OTEL_RESOURCE_ATTRIBUTES
    new_attrs = ','.join([f"{k}={v}" for k, v in resource_attributes.items()])
    combined_attrs = f"{existing_attrs},{new_attrs}" if existing_attrs else new_attrs
    os.environ['OTEL_RESOURCE_ATTRIBUTES'] = combined_attrs

    # Initialize OpenLIT with enhanced configuration
    openlit.init(**openlit_config)

    logger.info(f"✅ OpenLIT observability enabled: {openlit_config}")
    logger.info(f"📊 Resource attributes: {resource_attributes}")
else:
    logger.info("🚫 Observability disabled - skipping OpenLIT initialization")
    logger.info("💡 To enable observability, set DEVOPS_AGENT_OBSERVABILITY_ENABLE=true")

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
        # planner=BuiltInPlanner(
        #     thinking_config=types.ThinkingConfig(
        #         include_thoughts=True,
        #     ),
        # ),
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
