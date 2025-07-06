#!/usr/bin/env python3
"""
Quick test script for the enhanced software engineer agent.
Usage: python quick_test.py [task_description]
"""

import asyncio
import logging
import sys

from agents.software_engineer.enhanced_agent import enhanced_root_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def quick_test(task_description: str):
    """Run a quick test of the enhanced agent."""
    
    print(f"🚀 Testing Enhanced Agent")
    print(f"Task: {task_description}")
    print("=" * 60)
    
    try:
        # Run the task
        result = await enhanced_root_agent.run(task_description)
        
        print("\n✅ Task completed successfully!")
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"\n❌ Task failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function."""
    
    if len(sys.argv) < 2:
        print("Usage: python quick_test.py [task_description]")
        print("\nExample tasks:")
        print("  python quick_test.py 'Review code in src/auth.py'")
        print("  python quick_test.py 'Implement user authentication system'")
        print("  python quick_test.py 'Analyze API performance issues'")
        print("  python quick_test.py 'Improve code quality in payment module'")
        return
    
    task_description = " ".join(sys.argv[1:])
    asyncio.run(quick_test(task_description))

if __name__ == "__main__":
    main()
