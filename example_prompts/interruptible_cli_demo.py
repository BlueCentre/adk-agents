#!/usr/bin/env python3
"""
Demo script for the Interruptible CLI feature.

This script demonstrates how to use the new interruptible CLI that allows:
- Persistent input pane that remains active while the agent is responding
- Ability to interrupt long-running agent operations with Ctrl+C
- Split-pane interface with output above and input below
- Real-time status updates

Usage:
    # Using the interruptible CLI
    uv run python -m src.wrapper.adk.cli.cli --agent agents.devops --interruptible
    
    # Or using the regular CLI
    uv run python -m src.wrapper.adk.cli.cli --agent agents.devops
    
    # With theme selection
    uv run python -m src.wrapper.adk.cli.cli --agent agents.devops --interruptible --theme dark
"""

import asyncio
import sys
import os

# Add the project root to the path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.wrapper.adk.cli.cli import run_cli


async def demo_interruptible_cli():
    """Demo the interruptible CLI with DevOps agent."""
    print("🚀 Starting Interruptible CLI Demo")
    print("=" * 50)
    print()
    print("Features to try:")
    print("• Type a query and see it processed in real-time")
    print("• While the agent is responding, you can type another query")
    print("• Press Ctrl+C to interrupt long-running operations")
    print("• Use Ctrl+T to toggle themes")
    print("• Type 'help' for more commands")
    print()
    print("Starting the interruptible CLI...")
    print()
    
    try:
        await run_cli(
            agent_module_name="agents.devops",
            interruptible=True,
            ui_theme="dark",
            save_session=False
        )
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")


if __name__ == "__main__":
    # Run the demo
    asyncio.run(demo_interruptible_cli()) 