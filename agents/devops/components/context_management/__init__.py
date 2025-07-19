"""Context manager initialization and package exports."""

from .context_manager import ContextManager
from .cross_turn_correlation import CorrelationScore, CrossTurnCorrelator
from .dynamic_context_expansion import (
    DiscoveredContent,
    DynamicContextExpander,
    ExpansionContext,
)
from .file_tracker import file_change_tracker
from .intelligent_summarization import (
    ContentType,
    IntelligentSummarizer,
    SummarizationContext,
)
from .llm_injection import (
    get_last_user_content,
    inject_structured_context,
)
from .smart_prioritization import RelevanceScore, SmartPrioritizer
from .tool_hooks import (
    TOOL_PROCESSORS,
    extract_goal_from_user_message,
)

__all__ = [
    "TOOL_PROCESSORS",
    "ContentType",
    "ContextManager",
    "CorrelationScore",
    "CrossTurnCorrelator",
    "DiscoveredContent",
    "DynamicContextExpander",
    "ExpansionContext",
    "IntelligentSummarizer",
    "RelevanceScore",
    "SmartPrioritizer",
    "SummarizationContext",
    "extract_goal_from_user_message",
    "file_change_tracker",
    "get_last_user_content",
    "inject_structured_context",
]
