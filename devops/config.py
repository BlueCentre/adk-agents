# Agents/devops/config.py
import os
import logging
from dotenv import load_dotenv
from google.genai import types as genai_types

# Load .env file from the current directory (Agents/devops/)
# This assumes .env is in the same directory as config.py
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)

logger = logging.getLogger(__name__)

# --- Core Agent Configuration ---
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-pro-latest")
DEFAULT_SUB_AGENT_MODEL = "gemini-1.5-flash-latest" # Or make this configurable too

# --- Feature Flags ---
ENABLE_INTERACTIVE_PLANNING_STR = os.getenv("ENABLE_INTERACTIVE_PLANNING", "false")
ENABLE_INTERACTIVE_PLANNING = ENABLE_INTERACTIVE_PLANNING_STR.lower() == "true"

MCP_PLAYWRIGHT_ENABLED_STR = os.getenv("MCP_PLAYWRIGHT_ENABLED", "false")
MCP_PLAYWRIGHT_ENABLED = MCP_PLAYWRIGHT_ENABLED_STR.lower() == "true"

# --- MCP Tool Configurations ---
MCP_ALLOWED_DIRECTORIES_STR = os.getenv("MCP_ALLOWED_DIRECTORIES")
MCP_ALLOWED_DIRECTORIES = []
if MCP_ALLOWED_DIRECTORIES_STR:
    MCP_ALLOWED_DIRECTORIES = [d.strip() for d in MCP_ALLOWED_DIRECTORIES_STR.split(",") if d.strip()]
if not MCP_ALLOWED_DIRECTORIES:
    # Default to the parent directory of this config file (i.e., Agents/devops/)
    MCP_ALLOWED_DIRECTORIES = [os.path.dirname(os.path.abspath(__file__))]
    logger.info(f"MCP_ALLOWED_DIRECTORIES not set in .env, defaulting to agent directory: {MCP_ALLOWED_DIRECTORIES[0]}")

DATADOG_API_KEY = os.getenv("DATADOG_API_KEY")
DATADOG_APP_KEY = os.getenv("DATADOG_APP_KEY")

# --- LLM Generation Configuration ---
# This is for the main MyDevopsAgent instance
MAIN_LLM_GENERATION_CONFIG = genai_types.GenerateContentConfig(
    temperature=0.3,
    max_output_tokens=8000,
)

# --- Logging of configurations (optional but good for debugging) ---
logger.info(f"Config - GEMINI_MODEL_NAME: {GEMINI_MODEL_NAME}")
logger.info(f"Config - DEFAULT_SUB_AGENT_MODEL: {DEFAULT_SUB_AGENT_MODEL}")
logger.info(f"Config - Interactive Planning Enabled: {ENABLE_INTERACTIVE_PLANNING}")
logger.info(f"Config - MCP Playwright Enabled: {MCP_PLAYWRIGHT_ENABLED}")
logger.info(f"Config - MCP Allowed Directories: {MCP_ALLOWED_DIRECTORIES}")
logger.info(f"Config - Datadog API Key Loaded: {'Yes' if DATADOG_API_KEY else 'No'}")
logger.info(f"Config - Datadog App Key Loaded: {'Yes' if DATADOG_APP_KEY else 'No'}")
