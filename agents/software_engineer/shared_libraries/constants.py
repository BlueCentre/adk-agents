"""Shared constants for the SWE Agent."""

# Supported dependency file types for project context detection
DEPENDENCY_FILES = [
    "pyproject.toml",
    "package.json",
    "requirements.txt",
    "Cargo.toml",
    "go.mod",
]

# Default ignore patterns for project structure mapping
DEFAULT_IGNORE_PATTERNS = [
    ".git",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".coverage",
    "*.pyc",
    ".DS_Store",
    "venv",
    ".venv",
    "env",
    ".env",
    "dist",
    "build",
    ".idea",
    ".vscode",
    "*.egg-info",
]

# Project structure mapping defaults
DEFAULT_MAX_DEPTH = 3
MAX_COMMAND_HISTORY = 50
MAX_RECENT_ERRORS = 20
