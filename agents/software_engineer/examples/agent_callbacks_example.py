#!/usr/bin/env python3
"""
Example demonstrating the enhanced callback system with agent callbacks.

This script shows how the new agent callbacks provide additional telemetry
information about the entire agent session, including project context,
session metrics, and lifecycle events.
"""

import logging
from pathlib import Path
import sys

# Add the parent directory to the path so we can import from agents
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.software_engineer.shared_libraries.callbacks import (
    create_enhanced_telemetry_callbacks,
    create_telemetry_callbacks,
)

# Configure logging to see callback output
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def demonstrate_basic_callbacks():
    """Demonstrate basic callback creation and structure."""
    print("=== Basic Callbacks Demo ===")

    # Create basic callbacks (now includes agent callbacks)
    callbacks = create_telemetry_callbacks("demo_agent")

    print(f"Number of callbacks returned: {len(callbacks)}")
    print("Callback functions:")
    print("  - before_model: Callback executed before LLM model request")
    print("  - after_model: Callback executed after LLM model response")
    print("  - before_tool: Callback executed before tool execution")
    print("  - after_tool: Callback executed after tool execution")
    print("  - before_agent: Callback executed before agent starts processing")
    print("  - after_agent: Callback executed after agent completes processing")

    # Access callbacks via dictionary keys
    callbacks["before_model"]
    callbacks["after_model"]
    callbacks["before_tool"]
    callbacks["after_tool"]
    callbacks["before_agent"]
    callbacks["after_agent"]

    print("\nAll callbacks are callable:", all(callable(cb) for cb in callbacks.values()))
    return callbacks


def demonstrate_enhanced_callbacks():
    """Demonstrate enhanced callback creation with DevOps integration."""
    print("\n=== Enhanced Callbacks Demo ===")

    # Create enhanced callbacks (falls back to basic if DevOps telemetry not available)
    callbacks = create_enhanced_telemetry_callbacks("demo_enhanced_agent")

    print(f"Number of callbacks returned: {len(callbacks)}")
    print("Enhanced callbacks include:")
    print("  - DevOps telemetry integration (if available)")
    print("  - Session-level metrics tracking")
    print("  - Project context discovery")
    print("  - Cross-session correlation")

    return callbacks


def simulate_agent_session():
    """Simulate an agent session to show callback execution."""
    print("\n=== Agent Session Simulation ===")

    # Create callbacks
    callbacks = create_telemetry_callbacks("simulation_agent")

    # Mock callback context
    class MockCallbackContext:
        def __init__(self):
            self.session_id = "sim_session_123"
            self.invocation_id = "sim_inv_456"
            self.user_data = {}

    # Mock LLM request/response
    class MockLLMRequest:
        def __init__(self):
            self.contents = "Simulate a request to help with Python code"
            self.model = "gemini-2.0-flash"

    class MockLLMResponse:
        def __init__(self):
            self.text = "Here's how I can help with your Python code..."
            self.usage_metadata = MockUsageMetadata()

    class MockUsageMetadata:
        def __init__(self):
            self.prompt_token_count = 125
            self.candidates_token_count = 200

    # Mock tool
    class MockTool:
        def __init__(self):
            self.name = "read_file_tool"

    # Mock tool context
    class MockToolContext:
        def __init__(self):
            self.state = {}

    # Create mock objects
    context = MockCallbackContext()
    request = MockLLMRequest()
    response = MockLLMResponse()
    tool = MockTool()
    tool_context = MockToolContext()

    print("Starting agent session simulation...")

    # 1. Agent session starts
    print("\n1. Agent session starting...")
    callbacks["before_agent"](context)

    # 2. Model request
    print("\n2. Making LLM request...")
    callbacks["before_model"](context, request)

    # 3. Model response
    print("\n3. Processing LLM response...")
    callbacks["after_model"](context, response)

    # 4. Tool execution
    print("\n4. Executing tool...")
    callbacks["before_tool"](tool, {"file_path": "example.py"}, tool_context, context)

    # 5. Tool completion
    print("\n5. Tool completed...")
    callbacks["after_tool"](
        tool,
        "File content returned",
        context,
        {"file_path": "example.py"},
        tool_context,
    )

    # 6. Agent session ends
    print("\n6. Agent session ending...")
    callbacks["after_agent"](context)

    print("\nAgent session simulation completed!")


def show_callback_benefits():
    """Show the benefits of using agent callbacks."""
    print("\n=== Agent Callbacks Benefits ===")

    benefits = {
        "Session-Level Insights": [
            "Total session duration",
            "Aggregate token usage across all LLM calls",
            "Tool usage patterns and frequencies",
            "Error rates and failure analysis",
        ],
        "Project Context": [
            "Automatic project type detection",
            "File structure analysis",
            "Project-specific metrics",
            "Development environment insights",
        ],
        "Resource Management": [
            "Session initialization tracking",
            "Resource cleanup monitoring",
            "Memory and state management",
            "Session lifecycle events",
        ],
        "Performance Analytics": [
            "Cross-session performance comparison",
            "Agent efficiency metrics",
            "Bottleneck identification",
            "Usage optimization insights",
        ],
    }

    for category, items in benefits.items():
        print(f"\n{category}:")
        for item in items:
            print(f"  • {item}")


def main():
    """Main demonstration function."""
    print("Enhanced Agent Callbacks Demonstration")
    print("=" * 50)

    # Demonstrate callback creation
    demonstrate_basic_callbacks()
    demonstrate_enhanced_callbacks()

    # Simulate an agent session
    simulate_agent_session()

    # Show benefits
    show_callback_benefits()

    print("\n" + "=" * 50)
    print("Demo completed! Check the logs above to see callback output.")
    print("\nTo see more detailed logs, run with DEBUG level:")
    print("  LOG_LEVEL=DEBUG python agent_callbacks_example.py")


if __name__ == "__main__":
    main()
