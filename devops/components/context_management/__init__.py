"""Context manager initialization and package exports."""

from .context_manager import ContextManager
from .tool_hooks import (
    TOOL_PROCESSORS,
    extract_goal_from_user_message,
)
from .llm_injection import (
    get_last_user_content,
    inject_structured_context,
)
from .file_tracker import file_change_tracker

__all__ = [
    'ContextManager',
    'TOOL_PROCESSORS',
    'extract_goal_from_user_message',
    'get_last_user_content',
    'inject_structured_context',
    'file_change_tracker',
] 