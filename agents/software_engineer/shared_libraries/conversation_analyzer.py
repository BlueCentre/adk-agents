"""Conversation structure analysis for smart filtering and optimization."""

from dataclasses import dataclass, field
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolChain:
    """Represents a complete tool execution chain."""

    start_index: int
    end_index: Optional[int] = None
    user_message: Optional[Any] = None
    assistant_with_tools: Optional[Any] = None
    tool_results: list[Any] = field(default_factory=list)
    final_response: Optional[Any] = None
    is_complete: bool = False
    has_errors: bool = False


@dataclass
class ConversationSegment:
    """Represents a complete conversation segment."""

    start_index: int
    end_index: int
    messages: list[Any] = field(default_factory=list)
    has_tool_activity: bool = False
    user_query: Optional[str] = None
    segment_type: str = "conversation"  # conversation, tool_chain, system


class ConversationAnalyzer:
    """Analyzes conversation structure for smart filtering and optimization."""

    def __init__(self):
        """Initialize the conversation analyzer."""
        self.message_type_indicators = {
            "system": ["SYSTEM CONTEXT (JSON):", "SYSTEM:", "System:"],
            "context_injection": ["SYSTEM CONTEXT (JSON):"],
            "tool_result": ["tool_result", "function_result"],
        }

    def analyze_conversation_structure(self, contents: list) -> dict[str, Any]:
        """
        Analyze conversation structure to identify key components.

        Args:
            contents: List of conversation contents/messages

        Returns:
            Dictionary containing analyzed conversation structure
        """
        if not contents:
            return {
                "total_messages": 0,
                "message_types": {},
                "tool_chains": [],
                "conversation_segments": [],
                "current_tool_chains": [],
                "completed_conversations": [],
                "current_user_message": None,
                "system_messages": [],
                "context_injections": [],
            }

        logger.debug(f"Analyzing conversation with {len(contents)} messages")

        # Classify all message types
        message_types = self.classify_message_types(contents)

        # Identify tool execution chains
        tool_chains = self.identify_tool_chains(contents)

        # Segment the conversation
        conversation_segments = self._segment_conversation(contents)

        # Identify current vs completed elements
        current_tool_chains = [tc for tc in tool_chains if not tc.is_complete]
        completed_conversations = [
            seg for seg in conversation_segments if seg.segment_type == "conversation"
        ]

        # Find current user message (usually the last user message)
        current_user_message = self._find_current_user_message(message_types)

        analysis = {
            "total_messages": len(contents),
            "message_types": {
                "system": len(message_types.get("system", [])),
                "user": len(message_types.get("user", [])),
                "assistant": len(message_types.get("assistant", [])),
                "tool_result": len(message_types.get("tool_result", [])),
                "context_injection": len(message_types.get("context_injection", [])),
            },
            "tool_chains": tool_chains,
            "conversation_segments": conversation_segments,
            "current_tool_chains": current_tool_chains,
            "completed_conversations": completed_conversations,
            "current_user_message": current_user_message,
            "system_messages": message_types.get("system", []),
            "context_injections": message_types.get("context_injection", []),
        }

        logger.debug(
            f"Analysis complete: {analysis['message_types']} messages, "
            f"{len(tool_chains)} tool chains, {len(conversation_segments)} segments"
        )

        return analysis

    def classify_message_types(self, contents: list) -> dict[str, list]:
        """
        Classify messages by type (system, user, assistant, tool_result, context_injection).

        Args:
            contents: List of conversation contents/messages

        Returns:
            Dictionary mapping message types to lists of messages
        """
        classified = {
            "system": [],
            "user": [],
            "assistant": [],
            "tool_result": [],
            "context_injection": [],
            "unknown": [],
        }

        for i, content in enumerate(contents):
            try:
                message_type = self._classify_single_message(content)
                classified[message_type].append((i, content))
            except Exception as e:
                logger.warning(f"Error classifying message {i}: {e}")
                classified["unknown"].append((i, content))

        logger.debug(f"Message classification: {[(k, len(v)) for k, v in classified.items() if v]}")

        return classified

    def identify_tool_chains(self, contents: list) -> list[ToolChain]:
        """
        Identify complete tool execution chains.

        Tool chains follow the pattern:
        user_message → assistant_with_tool_calls → tool_results → assistant_response

        Args:
            contents: List of conversation contents/messages

        Returns:
            List of identified tool chains
        """
        tool_chains = []
        i = 0

        while i < len(contents):
            chain = self._extract_tool_chain_from_position(contents, i)
            if chain:
                tool_chains.append(chain)
                i = chain.end_index + 1 if chain.end_index is not None else i + 1
            else:
                i += 1

        logger.debug(f"Identified {len(tool_chains)} tool chains")

        return tool_chains

    def _classify_single_message(self, content: Any) -> str:
        """
        Classify a single message by type.

        Args:
            content: Single message content

        Returns:
            Message type as string
        """
        # Check for role-based classification
        if hasattr(content, "role"):
            role = (
                content.role.lower()
                if hasattr(content.role, "lower")
                else str(content.role).lower()
            )

            # Check for context injections (special system messages)
            if role in ["user", "system"] and self._is_context_injection(content):
                return "context_injection"

            # Check for system messages
            if role == "system" or self._is_system_message(content):
                return "system"

            # Check for tool results
            if role == "tool" or self._is_tool_result(content):
                return "tool_result"

            # Standard role classification
            if role in ["user", "assistant"]:
                return role

        # Content-based classification fallback
        if self._is_context_injection(content):
            return "context_injection"
        if self._is_system_message(content):
            return "system"
        if self._is_tool_result(content):
            return "tool_result"

        return "unknown"

    def _is_context_injection(self, content: Any) -> bool:
        """Check if content is a context injection."""
        text = self._extract_text_from_content(content)
        if text:
            return any(
                indicator in text for indicator in self.message_type_indicators["context_injection"]
            )
        return False

    def _is_system_message(self, content: Any) -> bool:
        """Check if content is a system message."""
        text = self._extract_text_from_content(content)
        if text:
            return any(indicator in text for indicator in self.message_type_indicators["system"])
        return False

    def _is_tool_result(self, content: Any) -> bool:
        """Check if content is a tool result."""
        # Check for tool result indicators in content
        if hasattr(content, "parts") and content.parts:
            for part in content.parts:
                if hasattr(part, "function_response") or hasattr(part, "tool_response"):
                    return True

        # Check text content
        text = self._extract_text_from_content(content)
        if text:
            return any(
                indicator in text.lower()
                for indicator in self.message_type_indicators["tool_result"]
            )

        return False

    def _extract_text_from_content(self, content: Any) -> Optional[str]:
        """Extract text content from various content formats."""
        try:
            # Direct text attribute
            if hasattr(content, "text") and content.text:
                return content.text

            # Parts-based content
            if hasattr(content, "parts") and content.parts:
                texts = []
                for part in content.parts:
                    if hasattr(part, "text") and part.text:
                        texts.append(part.text)
                return " ".join(texts) if texts else None

            # String conversion fallback
            text = str(content)
            return text if text and text != str(type(content)) else None

        except Exception as e:
            logger.debug(f"Error extracting text from content: {e}")
            return None

    def _extract_tool_chain_from_position(
        self, contents: list, start_pos: int
    ) -> Optional[ToolChain]:
        """
        Extract a tool execution chain starting from the given position.

        Args:
            contents: List of conversation contents
            start_pos: Starting position to look for tool chain

        Returns:
            ToolChain object if found, None otherwise
        """
        if start_pos >= len(contents):
            return None

        chain = ToolChain(start_index=start_pos)
        current_pos = start_pos

        # Look for user message
        if current_pos < len(contents):
            content = contents[current_pos]
            if hasattr(content, "role") and content.role == "user":
                chain.user_message = content
                current_pos += 1
            else:
                # Not a tool chain if it doesn't start with user message
                return None

        # Look for assistant message with tool calls
        if current_pos < len(contents):
            content = contents[current_pos]
            if hasattr(content, "role") and content.role == "assistant":
                if self._has_tool_calls(content):
                    chain.assistant_with_tools = content
                    current_pos += 1
                else:
                    # Assistant message without tools - not a tool chain
                    return None
            else:
                # Expected assistant message but found something else
                return None

        # Look for tool results
        while current_pos < len(contents):
            content = contents[current_pos]

            if self._is_tool_result(content):
                chain.tool_results.append(content)
                current_pos += 1

                # Check for errors in tool results
                if self._has_tool_errors(content):
                    chain.has_errors = True
            else:
                break

        # Look for final assistant response
        if current_pos < len(contents):
            content = contents[current_pos]
            if hasattr(content, "role") and content.role == "assistant":
                chain.final_response = content
                chain.end_index = current_pos
                chain.is_complete = True
            else:
                # No final response - incomplete chain
                chain.end_index = current_pos - 1
                chain.is_complete = False
        else:
            # Reached end without final response - incomplete chain
            chain.end_index = current_pos - 1
            chain.is_complete = False

        # Only return chain if it has at least user message and assistant with tools
        if chain.user_message and chain.assistant_with_tools:
            return chain

        return None

    def _has_tool_calls(self, content: Any) -> bool:
        """Check if assistant message has tool calls."""
        if hasattr(content, "parts") and content.parts:
            for part in content.parts:
                if hasattr(part, "function_call") or hasattr(part, "tool_call"):
                    return True
        return False

    def _has_tool_errors(self, content: Any) -> bool:
        """Check if tool result indicates an error."""
        text = self._extract_text_from_content(content)
        if text:
            error_indicators = ["error", "failed", "exception", "traceback"]
            return any(indicator in text.lower() for indicator in error_indicators)
        return False

    def _segment_conversation(self, contents: list) -> list[ConversationSegment]:
        """
        Segment the conversation into logical units.

        Args:
            contents: List of conversation contents

        Returns:
            List of conversation segments
        """
        segments = []
        current_segment = None

        for i, content in enumerate(contents):
            message_type = self._classify_single_message(content)

            # Start new segment for user messages (new conversation turns)
            if message_type == "user" and not self._is_context_injection(content):
                if current_segment is not None:
                    current_segment.end_index = i - 1
                    segments.append(current_segment)

                current_segment = ConversationSegment(
                    start_index=i,
                    end_index=i,
                    user_query=self._extract_text_from_content(content),
                    segment_type="conversation",
                )
                current_segment.messages.append(content)

            elif current_segment is not None:
                # Add to current segment
                current_segment.messages.append(content)
                current_segment.end_index = i

                # Check for tool activity
                if message_type in ["tool_result"] or self._has_tool_calls(content):
                    current_segment.has_tool_activity = True

            else:
                # Standalone system/context messages
                system_segment = ConversationSegment(
                    start_index=i,
                    end_index=i,
                    segment_type="system" if message_type == "system" else "context_injection",
                )
                system_segment.messages.append(content)
                segments.append(system_segment)

        # Close final segment
        if current_segment is not None:
            segments.append(current_segment)

        return segments

    def _find_current_user_message(self, message_types: dict[str, list]) -> Optional[Any]:
        """
        Find the current (most recent) user message.

        Args:
            message_types: Classified message types

        Returns:
            Current user message or None
        """
        user_messages = message_types.get("user", [])
        if not user_messages:
            return None

        # Find the last user message that's not a context injection
        for i in reversed(range(len(user_messages))):
            _, content = user_messages[i]
            if not self._is_context_injection(content):
                return content

        return None
