"""
Integration test configuration and shared fixtures.

This file provides shared fixtures and configuration for all integration tests,
following Google ADK integration testing patterns.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Optional

import pytest

# Import test helpers
from tests.shared.helpers import (
    create_mock_llm_client,
    create_mock_session_state,
    create_performance_test_data,
    create_sample_code_snippets,
    create_sample_conversation_history,
    create_test_workspace,
)

# Configure logging for integration tests
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


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

    if Path(env["workspace_dir"]).exists():
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

        def record_metric(self, name: str, value: float, tags: Optional[dict[str, str]] = None):
            self.metrics.append(
                {
                    "name": name,
                    "value": value,
                    "timestamp": time.time(),
                    "tags": tags or {},
                }
            )

        def get_metrics(self) -> list[dict[str, Any]]:
            return self.metrics

        def get_summary(self) -> dict[str, Any]:
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
        if Path(temp_file).exists():
            try:
                Path(temp_file).unlink()
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

    with Path.open(reports_dir / "session_info.json", "w") as f:
        json.dump(session_info, f, indent=2)

    yield session_info

    # Session cleanup
    logger.info("Ending integration test session")

    # Update session info with end time
    session_info["end_time"] = time.time()
    session_info["duration"] = session_info["end_time"] - session_info["start_time"]

    with Path.open(reports_dir / "session_info.json", "w") as f:
        json.dump(session_info, f, indent=2)
