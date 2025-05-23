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
from .smart_prioritization import SmartPrioritizer, RelevanceScore
from .cross_turn_correlation import CrossTurnCorrelator, CorrelationScore
from .intelligent_summarization import (
    IntelligentSummarizer,
    SummarizationContext,
    ContentType,
)
from .dynamic_context_expansion import (
    DynamicContextExpander,
    ExpansionContext,
    DiscoveredContent,
)

__all__ = [
    'ContextManager',
    'TOOL_PROCESSORS',
    'extract_goal_from_user_message',
    'get_last_user_content',
    'inject_structured_context',
    'file_change_tracker',
    'SmartPrioritizer',
    'RelevanceScore',
    'CrossTurnCorrelator',
    'CorrelationScore',
    'IntelligentSummarizer',
    'SummarizationContext',
    'ContentType',
    'DynamicContextExpander',
    'ExpansionContext',
    'DiscoveredContent',
] 