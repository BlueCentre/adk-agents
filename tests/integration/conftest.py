"""
Integration test configuration and shared fixtures.

This file provides shared fixtures and configuration for all integration tests,
following Google ADK integration testing patterns.
"""

import asyncio
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

# Import test helpers
from tests.fixtures.test_helpers import (
    MetricsCollector,
    MockCallbackContext,
    MockEvent,
    MockInvocationContext,
    MockLlmResponse,
    MockTool,
    MockToolContext,
    create_error_scenarios,
    create_mock_agent,
    create_mock_agent_with_tools,
    create_mock_context_manager_with_sample_data,
    create_mock_llm_client,
    create_mock_session_state,
    create_mock_workflow_agents,
    create_performance_test_data,
    create_sample_app_state,
    create_sample_code_snippets,
    create_sample_conversation_history,
    create_test_workspace,
    patch_human_approval_responses,
    run_with_timeout,
)

# Configure logging for integration tests
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# Simple mock classes for integration testing
class MockContextManager:
    """Mock context manager for testing."""

    def __init__(
        self, model_name="test-model", max_llm_token_limit=100000, llm_client=None
    ):
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

    def assemble_context(self, token_limit):
        context_dict = {
            "conversation_history": self.conversation_history,
            "code_snippets": self.code_snippets,
            "tool_results": self.tool_results,
        }
        # Simple token count approximation
        token_count = sum(len(str(v).split()) for v in context_dict.values()) * 1.3
        return context_dict, int(token_count)

    def clear_context(self):
        self.code_snippets = []
        self.tool_results = []
        self.conversation_history = []


class MockSmartPrioritizer:
    """Mock smart prioritizer for testing."""

    def prioritize_code_snippets(self, snippets, context, current_turn=1):
        # Simple prioritization - just add relevance scores
        for snippet in snippets:
            snippet["_relevance_score"] = MagicMock(final_score=0.5)
        return snippets


class MockCrossTurnCorrelator:
    """Mock cross-turn correlator for testing."""

    def correlate_turns(self, turns):
        return [{"turn": turn, "correlation_score": 0.5} for turn in turns]


class MockIntelligentSummarizer:
    """Mock intelligent summarizer for testing."""

    def summarize_content(self, content, max_tokens=500):
        return {"summary": "Test summary", "token_count": 100}


class MockRAGSystem:
    """Mock RAG system for testing."""

    def query(self, query, top_k=5):
        return [
            {"content": f"RAG result {i}", "score": 0.9 - i * 0.1} for i in range(top_k)
        ]


class MockAgent:
    """Base mock agent for testing."""

    def __init__(self, context_manager=None, llm_client=None):
        self.context_manager = context_manager
        self.llm_client = llm_client
        self.name = "mock_agent"

    async def process_message(self, message):
        return {"response": f"Mock response to: {message}", "success": True}


class MockDevOpsAgent(MockAgent):
    """Mock DevOps agent for testing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "devops_agent"


class MockSoftwareEngineerAgent(MockAgent):
    """Mock Software Engineer agent for testing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "software_engineer_agent"


class MockSWEAgent(MockAgent):
    """Mock SWE agent for testing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "swe_agent"


class MockWorkflowEngine:
    """Mock workflow engine for testing."""

    async def execute_workflow(self, workflow_type, agents, config=None):
        return {"workflow_type": workflow_type, "agents": len(agents), "success": True}


class MockToolOrchestrator:
    """Mock tool orchestrator for testing."""

    async def execute_tool(self, tool_name, args, dependencies=None, tool_id=None):
        return MagicMock(
            status="COMPLETED",
            result={"tool": tool_name, "success": True},
            execution_time=0.1,
            tool_id=tool_id,
        )


class MockPerformanceMonitor:
    """Mock performance monitor for testing."""

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
    """Mock resource monitor for testing."""

    def get_memory_usage(self):
        return 100.0  # MB

    def get_cpu_usage(self):
        return 50.0  # percent


def create_mock_agent_pool(agents):
    """Create mock agent pool for testing."""
    return {"agents": agents, "count": len(agents)}


def create_mock_workflow_config(workflow_type):
    """Create mock workflow config for testing."""
    return {
        "type": workflow_type,
        "steps": ["step1", "step2", "step3"],
        "parallel": workflow_type == "parallel",
        "max_retries": 3,
    }


def create_mock_context_data():
    """Create mock context data for testing."""
    return {
        "code_snippets": create_sample_code_snippets(),
        "conversation_history": create_sample_conversation_history(),
        "tool_results": [{"tool": "mock_tool", "result": "success"}],
    }


def create_mock_rag_data():
    """Create mock RAG data for testing."""
    return {
        "documents": [{"content": f"Document {i}", "id": i} for i in range(10)],
        "embeddings": [[0.1, 0.2, 0.3] for _ in range(10)],
    }


def create_mock_prioritization_data():
    """Create mock prioritization data for testing."""
    return {
        "context": "Fix authentication issues",
        "snippets": create_sample_code_snippets(),
    }


def create_mock_correlation_data():
    """Create mock correlation data for testing."""
    return {"turns": [{"turn": i, "message": f"Turn {i} message"} for i in range(5)]}


def create_mock_tool_chain_data():
    """Create mock tool chain data for testing."""
    return {
        "tools": [
            {"name": "read_file", "args": {"file_path": "test.py"}, "dependencies": []},
            {
                "name": "analyze_code",
                "args": {"file_path": "test.py"},
                "dependencies": ["read_file"],
            },
            {
                "name": "generate_tests",
                "args": {"file_path": "test.py"},
                "dependencies": ["analyze_code"],
            },
        ]
    }


def create_mock_performance_data():
    """Create mock performance data for testing."""
    return {
        "baseline_metrics": {
            "execution_time": 1.0,
            "memory_mb": 100,
            "cpu_percent": 50,
        },
        "test_scenarios": [
            {"name": "light_load", "users": 5, "operations": 50},
            {"name": "medium_load", "users": 10, "operations": 100},
            {"name": "heavy_load", "users": 25, "operations": 200},
        ],
    }


# Test markers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
]


# Pytest configuration
def pytest_configure(config):
    """Configure pytest for integration tests."""
    # Register custom markers
    config.addinivalue_line("markers", "integration: Integration test")
    config.addinivalue_line("markers", "performance: Performance test")
    config.addinivalue_line("markers", "slow: Slow test (>5 seconds)")
    config.addinivalue_line("markers", "stress: Stress test")
    config.addinivalue_line("markers", "load: Load test")
    config.addinivalue_line("markers", "foundation: Foundation phase tests")
    config.addinivalue_line("markers", "core: Core integration phase tests")
    config.addinivalue_line("markers", "orchestration: Tool orchestration phase tests")
    config.addinivalue_line(
        "markers", "verification: Performance verification phase tests"
    )

    # Set environment variables for integration testing
    os.environ["DEVOPS_AGENT_TESTING"] = "true"
    os.environ["DEVOPS_AGENT_LOG_LEVEL"] = "DEBUG"
    os.environ["DEVOPS_AGENT_INTEGRATION_TEST"] = "true"

    logger.info("Integration test environment configured")


def pytest_unconfigure(config):
    """Cleanup after integration tests."""
    # Clean up environment variables
    env_vars = [
        "DEVOPS_AGENT_TESTING",
        "DEVOPS_AGENT_LOG_LEVEL",
        "DEVOPS_AGENT_INTEGRATION_TEST",
    ]

    for var in env_vars:
        if var in os.environ:
            del os.environ[var]

    logger.info("Integration test environment cleaned up")


# Event loop fixture for async tests
@pytest.fixture(scope="function")
def event_loop():
    """Create a new event loop for each test."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# Core integration test fixtures
@pytest.fixture(scope="function")
def integration_test_env():
    """Create isolated integration test environment."""
    env = {
        "workspace_dir": tempfile.mkdtemp(),
        "test_mode": True,
        "mock_llm_client": create_mock_llm_client(),
        "session_state": create_mock_session_state(),
    }
    yield env
    # Cleanup
    import shutil

    if os.path.exists(env["workspace_dir"]):
        shutil.rmtree(env["workspace_dir"], ignore_errors=True)


@pytest.fixture(scope="function")
def test_workspace():
    """Create temporary test workspace."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = create_test_workspace()
        workspace = {
            "workspace_dir": temp_dir,
            "workspace_path": workspace_path,
            "test_files": [],
            "mock_data": {},
        }
        yield workspace
        # Cleanup is automatic with TemporaryDirectory


@pytest.fixture(scope="function")
def mock_llm_client():
    """Create mock LLM client for testing."""
    return create_mock_llm_client()


@pytest.fixture(scope="function")
def mock_session_state():
    """Create mock session state for multi-agent testing."""
    return create_mock_session_state()


# Context management fixtures
@pytest.fixture(scope="function")
def mock_context_manager(mock_llm_client):
    """Create mock context manager with realistic behavior."""
    context_manager = MockContextManager(
        model_name="test-model", max_llm_token_limit=100000, llm_client=mock_llm_client
    )
    return context_manager


@pytest.fixture(scope="function")
def mock_smart_prioritizer():
    """Create mock smart prioritizer for testing."""
    return MockSmartPrioritizer()


@pytest.fixture(scope="function")
def mock_cross_turn_correlator():
    """Create mock cross-turn correlator for testing."""
    return MockCrossTurnCorrelator()


@pytest.fixture(scope="function")
def mock_intelligent_summarizer():
    """Create mock intelligent summarizer for testing."""
    return MockIntelligentSummarizer()


@pytest.fixture(scope="function")
def mock_rag_system():
    """Create mock RAG system for testing."""
    return MockRAGSystem()


# Agent fixtures
@pytest.fixture(scope="function")
def mock_devops_agent(mock_context_manager, mock_llm_client):
    """Create mock DevOps agent for testing."""
    return MockDevOpsAgent(
        context_manager=mock_context_manager, llm_client=mock_llm_client
    )


@pytest.fixture(scope="function")
def mock_software_engineer_agent(mock_context_manager, mock_llm_client):
    """Create mock Software Engineer agent for testing."""
    return MockSoftwareEngineerAgent(
        context_manager=mock_context_manager, llm_client=mock_llm_client
    )


@pytest.fixture(scope="function")
def mock_swe_agent(mock_context_manager, mock_llm_client):
    """Create mock SWE agent for testing."""
    return MockSWEAgent(
        context_manager=mock_context_manager, llm_client=mock_llm_client
    )


@pytest.fixture(scope="function")
def mock_agent_pool(mock_devops_agent, mock_software_engineer_agent, mock_swe_agent):
    """Create pool of mock agents for testing."""
    return create_mock_agent_pool(
        [mock_devops_agent, mock_software_engineer_agent, mock_swe_agent]
    )


# Workflow orchestration fixtures
@pytest.fixture(scope="function")
def mock_workflow_engine():
    """Create mock workflow engine for testing."""
    return MockWorkflowEngine()


@pytest.fixture(scope="function")
def mock_tool_orchestrator():
    """Create mock tool orchestrator for testing."""
    return MockToolOrchestrator()


@pytest.fixture(scope="function")
def workflow_configs():
    """Create test workflow configurations."""
    return {
        "sequential": create_mock_workflow_config("sequential"),
        "parallel": create_mock_workflow_config("parallel"),
        "iterative": create_mock_workflow_config("iterative"),
        "human_in_loop": create_mock_workflow_config("human_in_loop"),
    }


# Performance monitoring fixtures
@pytest.fixture(scope="function")
def mock_performance_monitor():
    """Create mock performance monitor for testing."""
    return MockPerformanceMonitor()


@pytest.fixture(scope="function")
def mock_resource_monitor():
    """Create mock resource monitor for testing."""
    return MockResourceMonitor()


# Test data fixtures
@pytest.fixture(scope="session")
def diverse_code_snippets():
    """Create diverse code snippets for testing (session-scoped)."""
    return create_sample_code_snippets()


@pytest.fixture(scope="session")
def realistic_tool_results():
    """Create realistic tool results for testing (session-scoped)."""
    return [
        {"tool": "read_file", "result": {"content": "test content", "path": "test.py"}},
        {
            "tool": "analyze_code",
            "result": {"issues": ["minor issue"], "complexity": "low"},
        },
        {
            "tool": "generate_tests",
            "result": {"tests": ["test_function()"], "coverage": "100%"},
        },
    ]


@pytest.fixture(scope="session")
def conversation_history():
    """Create conversation history for testing (session-scoped)."""
    return create_sample_conversation_history()


@pytest.fixture(scope="session")
def performance_test_data():
    """Create performance test data (session-scoped)."""
    return create_performance_test_data()


@pytest.fixture(scope="function")
def mock_context_data():
    """Create mock context data for testing."""
    return create_mock_context_data()


@pytest.fixture(scope="function")
def mock_rag_data():
    """Create mock RAG data for testing."""
    return create_mock_rag_data()


@pytest.fixture(scope="function")
def mock_prioritization_data():
    """Create mock prioritization data for testing."""
    return create_mock_prioritization_data()


@pytest.fixture(scope="function")
def mock_correlation_data():
    """Create mock correlation data for testing."""
    return create_mock_correlation_data()


@pytest.fixture(scope="function")
def mock_tool_chain_data():
    """Create mock tool chain data for testing."""
    return create_mock_tool_chain_data()


@pytest.fixture(scope="function")
def mock_performance_data():
    """Create mock performance data for testing."""
    return create_mock_performance_data()


# Phase-specific fixtures
@pytest.fixture(scope="function")
def foundation_test_setup(mock_context_manager, mock_agent_pool, workflow_configs):
    """Setup for foundation phase tests."""
    return {
        "context_manager": mock_context_manager,
        "agent_pool": mock_agent_pool,
        "workflow_configs": workflow_configs,
    }


@pytest.fixture(scope="function")
def core_integration_setup(
    mock_context_manager,
    mock_smart_prioritizer,
    mock_cross_turn_correlator,
    mock_intelligent_summarizer,
    mock_rag_system,
):
    """Setup for core integration phase tests."""
    return {
        "context_manager": mock_context_manager,
        "smart_prioritizer": mock_smart_prioritizer,
        "cross_turn_correlator": mock_cross_turn_correlator,
        "intelligent_summarizer": mock_intelligent_summarizer,
        "rag_system": mock_rag_system,
    }


@pytest.fixture(scope="function")
def orchestration_setup(
    mock_tool_orchestrator, mock_workflow_engine, mock_agent_pool, mock_tool_chain_data
):
    """Setup for tool orchestration phase tests."""
    return {
        "tool_orchestrator": mock_tool_orchestrator,
        "workflow_engine": mock_workflow_engine,
        "agent_pool": mock_agent_pool,
        "tool_chain_data": mock_tool_chain_data,
    }


@pytest.fixture(scope="function")
def verification_setup(
    mock_performance_monitor,
    mock_resource_monitor,
    mock_context_manager,
    performance_test_data,
):
    """Setup for performance verification phase tests."""
    return {
        "performance_monitor": mock_performance_monitor,
        "resource_monitor": mock_resource_monitor,
        "context_manager": mock_context_manager,
        "performance_test_data": performance_test_data,
    }


# Utility fixtures
@pytest.fixture(scope="function")
def test_reports_dir():
    """Create test reports directory."""
    reports_dir = Path("test_reports")
    reports_dir.mkdir(exist_ok=True)
    return reports_dir


@pytest.fixture(scope="function")
def test_config():
    """Create test configuration."""
    return {
        "max_execution_time": 30.0,
        "max_memory_mb": 1000,
        "max_concurrent_tests": 10,
        "token_limit": 100000,
        "performance_thresholds": {
            "context_assembly": {
                "max_execution_time": 0.5,
                "max_memory_mb": 500,
                "min_operations_per_second": 100,
            },
            "tool_orchestration": {
                "max_execution_time": 2.0,
                "max_memory_mb": 1000,
                "min_operations_per_second": 50,
            },
            "load_testing": {
                "max_execution_time": 10.0,
                "max_memory_mb": 2000,
                "min_operations_per_second": 200,
            },
        },
    }


# Parametrized fixtures for different test scenarios
@pytest.fixture(
    params=[
        {"workflow_type": "sequential", "agent_count": 3},
        {"workflow_type": "parallel", "agent_count": 5},
        {"workflow_type": "iterative", "agent_count": 2},
        {"workflow_type": "human_in_loop", "agent_count": 4},
    ]
)
def workflow_scenario(request):
    """Parametrized workflow scenario for testing."""
    return request.param


@pytest.fixture(params=[1, 5, 10, 25, 50])
def load_test_scenario(request):
    """Parametrized load test scenario."""
    return {
        "concurrent_users": request.param,
        "operations_per_user": 100,
        "expected_min_throughput": max(50, 500 / request.param),
    }


@pytest.fixture(
    params=[
        {"context_size": 1000, "token_limit": 10000},
        {"context_size": 5000, "token_limit": 50000},
        {"context_size": 10000, "token_limit": 100000},
    ]
)
def context_scenario(request):
    """Parametrized context scenario for testing."""
    return request.param


# Error simulation fixtures
@pytest.fixture(scope="function")
def error_simulation_config():
    """Configuration for error simulation tests."""
    return {
        "error_types": [
            "network_error",
            "timeout_error",
            "rate_limit_error",
            "authentication_error",
            "validation_error",
        ],
        "error_probabilities": {
            "network_error": 0.1,
            "timeout_error": 0.05,
            "rate_limit_error": 0.02,
            "authentication_error": 0.01,
            "validation_error": 0.03,
        },
        "recovery_strategies": {
            "network_error": "retry_with_backoff",
            "timeout_error": "extend_timeout",
            "rate_limit_error": "exponential_backoff",
            "authentication_error": "refresh_credentials",
            "validation_error": "validate_and_retry",
        },
    }


# Test result collection fixtures
@pytest.fixture(scope="function")
def test_metrics_collector():
    """Collect test metrics during execution."""

    class MetricsCollector:
        def __init__(self):
            self.metrics = []
            self.start_time = time.time()

        def record_metric(
            self, name: str, value: float, tags: Optional[Dict[str, str]] = None
        ):
            self.metrics.append(
                {
                    "name": name,
                    "value": value,
                    "timestamp": time.time(),
                    "tags": tags or {},
                }
            )

        def get_metrics(self) -> List[Dict[str, Any]]:
            return self.metrics

        def get_summary(self) -> Dict[str, Any]:
            return {
                "total_metrics": len(self.metrics),
                "execution_time": time.time() - self.start_time,
                "metrics": self.metrics,
            }

    return MetricsCollector()


# Cleanup fixtures
@pytest.fixture(scope="function", autouse=True)
def cleanup_after_test():
    """Automatic cleanup after each test."""
    yield

    # Clean up any temporary files
    temp_files = [
        "test_temp_file.txt",
        "test_context.json",
        "test_performance_data.json",
    ]

    for temp_file in temp_files:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception as e:
                logger.warning(f"Failed to cleanup {temp_file}: {e}")


@pytest.fixture(scope="session", autouse=True)
def setup_integration_test_session():
    """Setup integration test session."""
    logger.info("Starting integration test session")

    # Ensure test reports directory exists
    reports_dir = Path("test_reports")
    reports_dir.mkdir(exist_ok=True)

    # Create session info file
    session_info = {
        "session_id": f"integration_test_session_{int(time.time())}",
        "start_time": time.time(),
        "python_version": os.sys.version,
        "platform": os.name,
        "environment": "integration_test",
    }

    with open(reports_dir / "session_info.json", "w") as f:
        json.dump(session_info, f, indent=2)

    yield session_info

    # Session cleanup
    logger.info("Ending integration test session")

    # Update session info with end time
    session_info["end_time"] = time.time()
    session_info["duration"] = session_info["end_time"] - session_info["start_time"]

    with open(reports_dir / "session_info.json", "w") as f:
        json.dump(session_info, f, indent=2)


# Skip conditions for different environments
def pytest_runtest_setup(item):
    """Setup for each test run."""
    # Skip performance tests on slow systems
    if "performance" in item.keywords:
        if os.environ.get("SKIP_PERFORMANCE_TESTS", "false").lower() == "true":
            pytest.skip("Performance tests skipped on slow systems")

    # Skip stress tests unless explicitly requested
    if "stress" in item.keywords:
        if os.environ.get("RUN_STRESS_TESTS", "false").lower() != "true":
            pytest.skip("Stress tests skipped unless explicitly requested")

    # Skip load tests unless explicitly requested
    if "load" in item.keywords:
        if os.environ.get("RUN_LOAD_TESTS", "false").lower() != "true":
            pytest.skip("Load tests skipped unless explicitly requested")


# Test execution hooks
def pytest_runtest_call(item):
    """Called to execute the test."""
    start_time = time.time()

    # Store start time for later use
    item._integration_test_start_time = start_time


def pytest_runtest_teardown(item):
    """Teardown after each test."""
    if hasattr(item, "_integration_test_start_time"):
        execution_time = time.time() - item._integration_test_start_time

        # Log slow tests
        if execution_time > 5.0:
            logger.warning(
                f"Slow test detected: {item.name} took {execution_time:.2f}s"
            )

        # Store execution time for reporting
        if not hasattr(item, "_integration_test_metrics"):
            item._integration_test_metrics = {}
        item._integration_test_metrics["execution_time"] = execution_time
