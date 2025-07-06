"""
Example demonstrating the enhanced software engineer agent with ADK workflow patterns.
"""

import asyncio
import logging

from agents.software_engineer.enhanced_agent import enhanced_root_agent
from agents.software_engineer.workflows.iterative_workflows import (
    create_iterative_refinement_workflow,
)
from agents.software_engineer.workflows.parallel_workflows import create_parallel_analysis_workflow
from agents.software_engineer.workflows.sequential_workflows import (
    create_feature_development_workflow,
)

# Enable debug logging to see workflow orchestration
logging.basicConfig(level=logging.INFO)


async def demonstrate_enhanced_agent():
    """Demonstrate the enhanced agent with various workflow patterns."""
    
    print("🚀 Enhanced Software Engineer Agent Demo")
    print("=" * 50)
    
    # Example 1: Simple task (traditional delegation)
    print("\n1. Simple Code Review (Traditional Delegation)")
    print("-" * 45)
    
    simple_task = "Review the authentication logic in src/auth.py for security issues"
    result = await enhanced_root_agent.run(simple_task)
    print(f"Result: {result}")
    
    # Example 2: Complex feature development (sequential workflow)
    print("\n2. Complex Feature Development (Sequential Workflow)")
    print("-" * 50)
    
    complex_task = "Implement a complete user management system with authentication, authorization, and profile management"
    result = await enhanced_root_agent.run(complex_task)
    print(f"Result: {result}")
    
    # Example 3: Code analysis (parallel workflow)
    print("\n3. Code Analysis (Parallel Workflow)")
    print("-" * 35)
    
    analysis_task = "Analyze our API codebase for security vulnerabilities, performance issues, and test coverage"
    result = await enhanced_root_agent.run(analysis_task)
    print(f"Result: {result}")
    
    # Example 4: Quality improvement (iterative workflow)
    print("\n4. Quality Improvement (Iterative Workflow)")
    print("-" * 42)
    
    quality_task = "Improve code quality in our payment processing module until it meets enterprise standards"
    result = await enhanced_root_agent.run(quality_task)
    print(f"Result: {result}")


async def demonstrate_direct_workflows():
    """Demonstrate using workflows directly."""
    
    print("\n🛠️ Direct Workflow Usage Demo")
    print("=" * 35)
    
    # Example 1: Parallel analysis workflow
    print("\n1. Direct Parallel Analysis")
    print("-" * 25)
    
    parallel_workflow = create_parallel_analysis_workflow()
    result = await parallel_workflow.run("Analyze codebase for security and performance issues")
    print(f"Result: {result}")
    
    # Example 2: Sequential feature development
    print("\n2. Direct Sequential Development")
    print("-" * 30)
    
    sequential_workflow = create_feature_development_workflow()
    result = await sequential_workflow.run("Implement OAuth2 authentication system")
    print(f"Result: {result}")
    
    # Example 3: Iterative refinement
    print("\n3. Direct Iterative Refinement")
    print("-" * 28)
    
    iterative_workflow = create_iterative_refinement_workflow()
    result = await iterative_workflow.run("Refactor legacy authentication code for better maintainability")
    print(f"Result: {result}")


def demonstrate_workflow_selection():
    """Demonstrate workflow selection tool."""
    
    print("\n🎯 Workflow Selection Demo")
    print("=" * 30)
    
    from agents.software_engineer.enhanced_agent import workflow_selector_tool

    # Example scenarios
    scenarios = [
        {
            "task_type": "feature_development",
            "complexity": "high",
            "requires_approval": True,
            "parallel_capable": False,
            "iterative": False
        },
        {
            "task_type": "analysis",
            "complexity": "medium",
            "requires_approval": False,
            "parallel_capable": True,
            "iterative": False
        },
        {
            "task_type": "refinement",
            "complexity": "high",
            "requires_approval": False,
            "parallel_capable": False,
            "iterative": True
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. Scenario: {scenario['task_type'].title()}")
        selection = workflow_selector_tool(**scenario)
        print(f"   Selected: {selection['selected_workflow']}")
        print(f"   Reason: {selection['recommendation_reason']}")


async def main():
    """Main demonstration function."""
    
    try:
        # Demonstrate enhanced agent
        await demonstrate_enhanced_agent()
        
        # Demonstrate direct workflows
        await demonstrate_direct_workflows()
        
        # Demonstrate workflow selection
        demonstrate_workflow_selection()
        
        print("\n✅ Demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(main())
