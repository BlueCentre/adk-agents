"""
Shared mock classes for integration tests.
"""

import time
from unittest.mock import MagicMock


# Simple mock classes for integration testing
class MockContextManager:
    """
    Mock context manager for testing.

    This class simulates the behavior of the real context manager, allowing for
    the addition of code snippets, tool results, and conversation history. It
    also provides a basic implementation of context assembly and token counting.
    """

    def __init__(self, model_name="test-model", max_llm_token_limit=100000, llm_client=None):
        self.model_name = model_name
        self.max_llm_token_limit = max_llm_token_limit
        self.llm_client = llm_client
        self.code_snippets = []
        self.tool_results = []
        self.conversation_history = []

    def add_code_snippet(self, file_path, content, start_line=1, end_line=None):
        self.code_snippets.append(
            {
                "file_path": file_path,
                "content": content,
                "start_line": start_line,
                "end_line": end_line or start_line + len(content.split("\n")),
            }
        )

    def add_tool_result(self, tool_name, result):
        self.tool_results.append(
            {"tool_name": tool_name, "result": result, "timestamp": time.time()}
        )

    def start_new_turn(self, message):
        turn_number = len(self.conversation_history) + 1
        self.conversation_history.append(
            {
                "turn_number": turn_number,
                "user_message": message,
                "timestamp": time.time(),
            }
        )
        return turn_number

    def assemble_context(self, _token_limit):
        context_dict = {
            "conversation_history": self.conversation_history,
            "code_snippets": self.code_snippets,
            "tool_results": self.tool_results,
        }
        # More realistic token count approximation by summing words from relevant fields
        words = 0
        words += sum(
            len(str(turn.get("user_message", "")).split()) for turn in self.conversation_history
        )
        words += sum(len(str(snippet.get("content", "")).split()) for snippet in self.code_snippets)
        words += sum(len(str(result.get("result", "")).split()) for result in self.tool_results)
        token_count = words * 1.3
        return context_dict, int(token_count)

    def clear_context(self):
        self.code_snippets = []
        self.tool_results = []
        self.conversation_history = []


class MockSmartPrioritizer:
    """
    Mock smart prioritizer for testing.

    This class simulates the behavior of the smart prioritizer, which is
    responsible for ranking code snippets based on their relevance to the
    current context.
    """

    def prioritize_code_snippets(self, snippets, _context, _current_turn=1):
        # Simple prioritization - just add relevance scores
        for snippet in snippets:
            snippet["_relevance_score"] = MagicMock(final_score=0.5)
        return snippets


class MockCrossTurnCorrelator:
    """
    Mock cross-turn correlator for testing.

    This class simulates the behavior of the cross-turn correlator, which is
    responsible for identifying relationships between different turns in a
    conversation.
    """

    def correlate_turns(self, turns):
        return [{"turn": turn, "correlation_score": 0.5} for turn in turns]


class MockIntelligentSummarizer:
    """
    Mock intelligent summarizer for testing.

    This class simulates the behavior of the intelligent summarizer, which is
    responsible for creating concise summaries of content.
    """

    def summarize_content(self, _content, _max_tokens=500):
        return {"summary": "Test summary", "token_count": 100}


class MockRAGSystem:
    """
    Mock RAG system for testing.

    This class simulates the behavior of the RAG (Retrieval-Augmented
    Generation) system, which is responsible for retrieving relevant documents
    from a knowledge base.
    """

    def query(self, _query, top_k=5):
        return [{"content": f"RAG result {i}", "score": 0.9 - i * 0.1} for i in range(top_k)]


class MockAgent:
    """
    Base mock agent for testing.

    This class provides a base implementation for mock agents, including a
    `process_message` method that returns a mock response.
    """

    def __init__(self, context_manager=None, llm_client=None):
        self.context_manager = context_manager
        self.llm_client = llm_client
        self.name = "mock_agent"

    async def process_message(self, message):
        return {"response": f"Mock response to: {message}", "success": True}


class MockDevOpsAgent(MockAgent):
    """
    Mock DevOps agent for testing.

    This class extends the base mock agent to simulate the behavior of a
    DevOps agent.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "devops_agent"


class MockSoftwareEngineerAgent(MockAgent):
    """
    Mock Software Engineer agent for testing.

    This class extends the base mock agent to simulate the behavior of a
    Software Engineer agent.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "software_engineer_agent"


class MockSWEAgent(MockAgent):
    """
    Mock SWE agent for testing.

    This class extends the base mock agent to simulate the behavior of a
    SWE (Software Engineer) agent.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "swe_agent"


class MockWorkflowEngine:
    """
    Mock workflow engine for testing.

    This class simulates the behavior of the workflow engine, which is
    responsible for executing workflows of different types.
    """

    async def execute_workflow(self, workflow_type, agents, config=None):  # noqa: ARG002
        return {"workflow_type": workflow_type, "agents": len(agents), "success": True}


class MockToolOrchestrator:
    """
    Mock tool orchestrator for testing.

    This class simulates the behavior of the tool orchestrator, which is
    responsible for executing tools and managing their dependencies.
    """

    async def execute_tool(self, tool_name, args, dependencies=None, tool_id=None):  # noqa: ARG002
        return MagicMock(
            status="COMPLETED",
            result={"tool": tool_name, "success": True},
            execution_time=0.1,
            tool_id=tool_id,
        )


class MockPerformanceMonitor:
    """
    Mock performance monitor for testing.

    This class simulates the behavior of the performance monitor, which is
    responsible for collecting and reporting performance metrics.
    """

    def __init__(self):
        self.metrics = []

    def start_monitoring(self):
        self.start_time = time.time()

    def stop_monitoring(self):
        return MagicMock(
            execution_time=time.time() - getattr(self, "start_time", time.time()),
            peak_memory_mb=100,
            avg_memory_mb=80,
            peak_cpu_percent=50,
            avg_cpu_percent=30,
            total_operations=10,
            operations_per_second=100,
        )

    def record_operation(self, success=True):
        self.metrics.append({"success": success, "timestamp": time.time()})


class MockResourceMonitor:
    """
    Mock resource monitor for testing.

    This class simulates the behavior of the resource monitor, which is
    responsible for monitoring system resources such as memory and CPU usage.
    """

    def get_memory_usage(self):
        return 100.0  # MB

    def get_cpu_usage(self):
        return 50.0  # percent
