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
GEMINI_FLASH_MODEL_NAME = "gemini-1.5-flash-latest"
GEMINI_PRO_MODEL_NAME = "gemini-1.5-pro-latest"

GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", GEMINI_PRO_MODEL_NAME) # Default to Pro
DEFAULT_SUB_AGENT_MODEL = GEMINI_FLASH_MODEL_NAME 

# --- LLM Generation Configuration ---
MAIN_LLM_GENERATION_CONFIG = genai_types.GenerateContentConfig(
    temperature=0.3,
    max_output_tokens=8000,
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
CONTEXT_TARGET_RECENT_TURNS = 5
CONTEXT_TARGET_CODE_SNIPPETS = 7
CONTEXT_TARGET_TOOL_RESULTS = 7
CONTEXT_MAX_STORED_CODE_SNIPPETS = 10
CONTEXT_MAX_STORED_TOOL_RESULTS = 20

# --- Tool Configuration ---
# File Summarizer Tool
SUMMARIZER_MODEL_NAME = os.getenv("SUMMARIZER_GEMINI_MODEL", "gemini-1.5-flash-latest")
MAX_CONTENT_CHARS_FOR_SUMMARIZER_SINGLE_PASS = 200000

# Shell Command Tool
DEFAULT_SHELL_COMMAND_TIMEOUT = 60  # seconds
DEFAULT_SAFE_COMMANDS = [
    "ls", "cat", "grep", "find", "head", "tail", "wc", "echo", "pwd", 
    "cd", "mkdir", "rm", "cp", "mv", "git", "gh", "docker", "kubectl", 
    "helm", "terraform", "aws", "gcloud", "az", "df", "du", "ps", 
    "curl", "wget", "jq", "yq", "awk", "sed", "python", "pip", "npm",
    "node", "yarn", "go", "make", "mvn", "gradle"
]

# Persistent Memory Tool
DEFAULT_MEMORY_FILE = "./.manual_agent_memory.json"

# --- MCP Tool Configurations ---
MCP_ALLOWED_DIRECTORIES_STR = os.getenv("MCP_ALLOWED_DIRECTORIES")
MCP_ALLOWED_DIRECTORIES = []
if MCP_ALLOWED_DIRECTORIES_STR:
    MCP_ALLOWED_DIRECTORIES = [d.strip() for d in MCP_ALLOWED_DIRECTORIES_STR.split(",") if d.strip()]
if not MCP_ALLOWED_DIRECTORIES:
    MCP_ALLOWED_DIRECTORIES = [os.path.dirname(os.path.abspath(__file__))]
    logger.info(f"MCP_ALLOWED_DIRECTORIES not set in .env, defaulting to agent directory: {MCP_ALLOWED_DIRECTORIES[0]}")

DATADOG_API_KEY = os.getenv("DATADOG_API_KEY")
DATADOG_APP_KEY = os.getenv("DATADOG_APP_KEY")

# --- Feature Flags ---
ENABLE_INTERACTIVE_PLANNING_STR = os.getenv("ENABLE_INTERACTIVE_PLANNING", "false")
ENABLE_INTERACTIVE_PLANNING = ENABLE_INTERACTIVE_PLANNING_STR.lower() == "true"

MCP_PLAYWRIGHT_ENABLED_STR = os.getenv("MCP_PLAYWRIGHT_ENABLED", "false")
MCP_PLAYWRIGHT_ENABLED = MCP_PLAYWRIGHT_ENABLED_STR.lower() == "true"

# --- Logging of configurations ---
logger.info(f"Config - GEMINI_MODEL_NAME: {GEMINI_MODEL_NAME}")
logger.info(f"Config - DEFAULT_SUB_AGENT_MODEL: {DEFAULT_SUB_AGENT_MODEL}")
logger.info(f"Config - Google API Key Loaded: {'Yes' if GOOGLE_API_KEY else 'No'}")
logger.info(f"Config - Interactive Planning Enabled: {ENABLE_INTERACTIVE_PLANNING}")
logger.info(f"Config - Context Target Recent Turns: {CONTEXT_TARGET_RECENT_TURNS}")
logger.info(f"Config - Context Target Code Snippets: {CONTEXT_TARGET_CODE_SNIPPETS}")
logger.info(f"Config - Context Target Tool Results: {CONTEXT_TARGET_TOOL_RESULTS}")
logger.info(f"Config - Summarizer Model: {SUMMARIZER_MODEL_NAME}")
logger.info(f"Config - Shell Command Default Timeout: {DEFAULT_SHELL_COMMAND_TIMEOUT}s")
logger.info(f"Config - MCP Allowed Directories: {MCP_ALLOWED_DIRECTORIES}")
logger.info(f"Config - MCP Playwright Enabled: {MCP_PLAYWRIGHT_ENABLED}")
logger.info(f"Config - Datadog API Key Loaded: {'Yes' if DATADOG_API_KEY else 'No'}")
logger.info(f"Config - Datadog App Key Loaded: {'Yes' if DATADOG_APP_KEY else 'No'}")
