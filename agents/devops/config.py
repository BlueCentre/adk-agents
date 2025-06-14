"""
This file is used to load the configuration for the devops agent.
"""

import os
import logging

from dotenv import load_dotenv

from google.genai import types as genai_types

# Load .env file from the current directory
# dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
# load_dotenv(dotenv_path=dotenv_path)
load_dotenv()

logger = logging.getLogger(__name__)

# --- LLM Configuration ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_FLASH_MODEL_NAME = os.getenv("GEMINI_FLASH_MODEL", "gemini-1.5-flash")
GEMINI_PRO_MODEL_NAME = os.getenv("GEMINI_PRO_MODEL", "gemini-1.5-pro")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", GEMINI_FLASH_MODEL_NAME) # Default to Pro

# Gemini 2.5 series models with thinking support
GEMINI_2_5_FLASH_MODEL_NAME = "gemini-2.5-flash-preview-05-20"
GEMINI_2_5_PRO_MODEL_NAME = "gemini-2.5-pro-preview-06-05"

DEFAULT_AGENT_MODEL = os.getenv("AGENT_MODEL", GEMINI_MODEL_NAME)
DEFAULT_SUB_AGENT_MODEL = os.getenv("SUB_AGENT_MODEL", GEMINI_FLASH_MODEL_NAME)
DEFAULT_CODE_EXECUTION_MODEL = os.getenv("CODE_EXECUTION_MODEL", GEMINI_FLASH_MODEL_NAME)
DEFAULT_SEARCH_MODEL = os.getenv("GOOGLE_SEARCH_MODEL", GEMINI_FLASH_MODEL_NAME)
DEFAULT_SUMMARIZER_MODEL = os.getenv("SUMMARIZER_MODEL", GEMINI_FLASH_MODEL_NAME)

# --- Gemini Thinking Configuration ---
GEMINI_THINKING_ENABLE_STR = os.getenv("GEMINI_THINKING_ENABLE", "false")
GEMINI_THINKING_ENABLE = GEMINI_THINKING_ENABLE_STR.lower() == "true"

GEMINI_THINKING_INCLUDE_THOUGHTS_STR = os.getenv("GEMINI_THINKING_INCLUDE_THOUGHTS", "true")
GEMINI_THINKING_INCLUDE_THOUGHTS = GEMINI_THINKING_INCLUDE_THOUGHTS_STR.lower() == "true"

# Thinking budget (tokens allocated for internal reasoning)
# Higher values allow more complex reasoning but cost more
GEMINI_THINKING_BUDGET = int(os.getenv("GEMINI_THINKING_BUDGET", "8192"))

# Models that support thinking
THINKING_SUPPORTED_MODELS = {
    GEMINI_2_5_FLASH_MODEL_NAME,
    GEMINI_2_5_PRO_MODEL_NAME
}

def is_thinking_supported(model_name: str) -> bool:
    """Check if the given model supports thinking."""
    return model_name in THINKING_SUPPORTED_MODELS

def should_enable_thinking(model_name: str) -> bool:
    """Determine if thinking should be enabled for the given model."""
    return GEMINI_THINKING_ENABLE and is_thinking_supported(model_name)

# --- Observability and Telemetry Configuration ---
# Agent observability control
DEVOPS_AGENT_OBSERVABILITY_ENABLE = os.getenv('DEVOPS_AGENT_OBSERVABILITY_ENABLE', '').lower() in ('true', '1', 'yes')
DEVOPS_AGENT_ENABLE_LOCAL_METRICS = os.getenv('DEVOPS_AGENT_ENABLE_LOCAL_METRICS', '').lower() in ('true', '1', 'yes')
DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT = os.getenv('DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT', '').lower() in ('true', '1', 'yes')

# Grafana Cloud OTLP configuration
GRAFANA_OTLP_ENDPOINT = os.getenv('GRAFANA_OTLP_ENDPOINT')
GRAFANA_OTLP_TOKEN = os.getenv('GRAFANA_OTLP_TOKEN')
GRAFANA_EXPORT_INTERVAL_SECONDS = int(os.getenv('GRAFANA_EXPORT_INTERVAL_SECONDS', '120'))
GRAFANA_EXPORT_TIMEOUT_SECONDS = int(os.getenv('GRAFANA_EXPORT_TIMEOUT_SECONDS', '30'))

# OpenLIT configuration
OPENLIT_ENVIRONMENT = os.getenv('OPENLIT_ENVIRONMENT', 'Production')
OPENLIT_APPLICATION_NAME = os.getenv('OPENLIT_APPLICATION_NAME')
OPENLIT_COLLECT_GPU_STATS = os.getenv('OPENLIT_COLLECT_GPU_STATS', 'false').lower() in ('true', '1', 'yes')
OPENLIT_DISABLE_METRICS = os.getenv('OPENLIT_DISABLE_METRICS', 'false').lower() in ('true', '1', 'yes')
OPENLIT_CAPTURE_CONTENT = os.getenv('OPENLIT_CAPTURE_CONTENT', 'true').lower() in ('true', '1', 'yes')
OPENLIT_DISABLE_BATCH = os.getenv('OPENLIT_DISABLE_BATCH', 'false').lower() in ('true', '1', 'yes')
OPENLIT_DISABLED_INSTRUMENTORS = os.getenv('OPENLIT_DISABLED_INSTRUMENTORS', '')

# Service identification
SERVICE_INSTANCE_ID = os.getenv('SERVICE_INSTANCE_ID', f"devops-agent-{os.getpid()}")
SERVICE_VERSION = os.getenv('SERVICE_VERSION', '1.0.0')

# OpenTelemetry resource attributes
OTEL_RESOURCE_ATTRIBUTES = os.getenv('OTEL_RESOURCE_ATTRIBUTES', '')

# Tracing configuration
TRACE_SAMPLING_RATE = float(os.getenv('TRACE_SAMPLING_RATE', '1.0'))

# Kubernetes attributes (commented out but available for future use)
# K8S_POD_NAME = os.getenv('K8S_POD_NAME')
# K8S_NAMESPACE_NAME = os.getenv('K8S_NAMESPACE_NAME', 'default')
# K8S_NODE_NAME = os.getenv('K8S_NODE_NAME', 'unknown')

def should_enable_observability() -> bool:
    """Check if observability should be enabled based on configuration."""
    # Check if explicitly enabled
    if DEVOPS_AGENT_OBSERVABILITY_ENABLE:
        return True
    
    # Check if local metrics are explicitly enabled
    if DEVOPS_AGENT_ENABLE_LOCAL_METRICS:
        return True
    
    # Check if any observability configuration is present (auto-enable for convenience)
    has_grafana_config = bool(GRAFANA_OTLP_ENDPOINT and GRAFANA_OTLP_TOKEN)
    has_openlit_config = bool(OPENLIT_ENVIRONMENT != 'Production' or OPENLIT_APPLICATION_NAME)
    
    # Auto-enable if production observability is configured
    if has_grafana_config or has_openlit_config:
        return True
    
    # Default: observability disabled for clean output
    return False

# --- RAG and Tools Configuration ---
CHROMA_DATA_PATH = os.getenv("CHROMA_DATA_PATH")
SOFTWARE_ENGINEER_CONTEXT = os.getenv("SOFTWARE_ENGINEER_CONTEXT", "eval/project_context_empty.json")

# --- Agent Control Configuration ---
DEVOPS_AGENT_INTERACTIVE = os.getenv('DEVOPS_AGENT_INTERACTIVE', '').lower() in ('true', '1', 'yes')
DEVOPS_AGENT_QUIET = os.getenv('DEVOPS_AGENT_QUIET', '').lower() in ('true', '1', 'yes')

# --- Debugging and Development Configuration ---
LOG_FULL_PROMPTS = os.getenv('LOG_FULL_PROMPTS', 'false').lower() == 'true'

# --- LLM Generation Configuration ---
MAIN_LLM_GENERATION_CONFIG = genai_types.GenerateContentConfig(
    temperature=0.3,
    max_output_tokens=10000,
    safety_settings=[
        genai_types.SafetySetting(
            category=genai_types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=genai_types.HarmBlockThreshold.OFF,
        )
    ]
)

# --- LLM Token Limits (Context Window Sizes) ---
# These are FALLBACK values if dynamic fetching from model info fails.
# Verify with official documentation for the specific model version.
GEMINI_FLASH_TOKEN_LIMIT_FALLBACK = 1048576
GEMINI_PRO_TOKEN_LIMIT_FALLBACK = 1048576 # Standard Pro is 1M, can be up to 2M for some versions/APIs
# Generic fallback if model name doesn't match known ones
DEFAULT_TOKEN_LIMIT_FALLBACK = 1000000

# ACTUAL_LLM_TOKEN_LIMIT will be determined dynamically in devops_agent.py
# by inspecting the model_info, with fallback to these constants.

# --- Context Management Configuration ---
# Parameters for tuning the context manager's behavior
CONTEXT_TARGET_RECENT_TURNS = 15
CONTEXT_TARGET_CODE_SNIPPETS = 5
CONTEXT_TARGET_TOOL_RESULTS = 10
CONTEXT_MAX_STORED_CODE_SNIPPETS = 5
CONTEXT_MAX_STORED_TOOL_RESULTS = 20

# --- Tool Configuration ---
# File Summarizer Tool
SUMMARIZER_MODEL_NAME = DEFAULT_SUMMARIZER_MODEL
MAX_CONTENT_CHARS_FOR_SUMMARIZER_SINGLE_PASS = 200000

# Shell Command Tool
DEFAULT_SHELL_COMMAND_TIMEOUT = 60  # seconds
DEFAULT_SAFE_COMMANDS = [
    "ls", "cat", "grep", "find", "head", "tail", "wc", "echo", "pwd", 
    "cd", "mkdir", "rm", "cp", "mv", "git", "gh", "docker", "kubectl", 
    "helm", "terraform", "aws", "gcloud", "az", "df", "du", "ps", 
    "curl", "wget", "jq", "yq", "awk", "sed", "python", "pip", "npm",
    "node", "yarn", "go", "make", "mvn", "gradle", "jira", "bw"
]

# Persistent Memory Tool
DEFAULT_MEMORY_FILE = ".memory.json"

# --- MCP Tool Configurations ---
# MCP_ALLOWED_DIRECTORIES_STR = os.getenv("MCP_ALLOWED_DIRECTORIES")
# MCP_ALLOWED_DIRECTORIES = []
# if MCP_ALLOWED_DIRECTORIES_STR:
#     MCP_ALLOWED_DIRECTORIES = [d.strip() for d in MCP_ALLOWED_DIRECTORIES_STR.split(",") if d.strip()]
# if not MCP_ALLOWED_DIRECTORIES:
#     MCP_ALLOWED_DIRECTORIES = [os.path.dirname(os.path.abspath(__file__))]
#     logger.info(f"MCP_ALLOWED_DIRECTORIES not set in .env, defaulting to agent directory: {MCP_ALLOWED_DIRECTORIES[0]}")

# --- Feature Flags ---
ENABLE_INTERACTIVE_PLANNING_STR = os.getenv("ENABLE_INTERACTIVE_PLANNING", "false")
ENABLE_INTERACTIVE_PLANNING = ENABLE_INTERACTIVE_PLANNING_STR.lower() == "true"

ENABLE_CODE_EXECUTION_STR = os.getenv("ENABLE_CODE_EXECUTION", "false")
ENABLE_CODE_EXECUTION = ENABLE_CODE_EXECUTION_STR.lower() == "true"

# --- Logging of configurations ---
logger.info(f"Config - Google API Key Loaded: {'Yes' if GOOGLE_API_KEY else 'No'}")
logger.info(f"Config - Default Agent Model: {DEFAULT_AGENT_MODEL}")
logger.info(f"Config - Default Sub-Agent Model: {DEFAULT_SUB_AGENT_MODEL}")
logger.info(f"Config - Default Code Execution Model: {DEFAULT_CODE_EXECUTION_MODEL}")
logger.info(f"Config - Default Search Model: {DEFAULT_SEARCH_MODEL}")
logger.info(f"Config - Default Summarizer Model: {DEFAULT_SUMMARIZER_MODEL}")
logger.info(f"Config - Interactive Planning Enabled: {ENABLE_INTERACTIVE_PLANNING}")
logger.info(f"Config - Code Execution Enabled: {ENABLE_CODE_EXECUTION}")
logger.info(f"Config - Gemini Thinking Enabled: {GEMINI_THINKING_ENABLE}")
if GEMINI_THINKING_ENABLE:
    logger.info(f"Config - Gemini Thinking Include Thoughts: {GEMINI_THINKING_INCLUDE_THOUGHTS}")
    logger.info(f"Config - Gemini Thinking Budget: {GEMINI_THINKING_BUDGET}")
    logger.info(f"Config - Agent Model Supports Thinking: {is_thinking_supported(DEFAULT_AGENT_MODEL)}")
logger.info(f"Config - Observability Enabled: {should_enable_observability()}")
logger.info(f"Config - Context Target Recent Turns: {CONTEXT_TARGET_RECENT_TURNS}")
logger.info(f"Config - Context Target Code Snippets: {CONTEXT_TARGET_CODE_SNIPPETS}")
logger.info(f"Config - Context Target Tool Results: {CONTEXT_TARGET_TOOL_RESULTS}")
logger.info(f"Config - Shell Command Default Timeout: {DEFAULT_SHELL_COMMAND_TIMEOUT}s")
# logger.info(f"Config - MCP Allowed Directories: {MCP_ALLOWED_DIRECTORIES}")
