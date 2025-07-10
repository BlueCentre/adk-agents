---
title: Test Patterns and Best Practices
layout: default
nav_order: 2
parent: Testing
---

# Test Patterns and Best Practices

This guide documents the specific test patterns, architectural decisions, and best practices used in the ADK Agents integration test suite.

## Core Test Patterns

### 1. Agent Lifecycle Testing Pattern

The agent lifecycle pattern validates complete conversation turns with proper context management.

#### Pattern Structure

```python
class TestAgentLifecycle:
    @pytest.fixture
    def context_manager(self):
        """Create context manager with proper mocking."""
        return ContextManager(
            model_name="test-model",
            max_llm_token_limit=100000,
            llm_client=create_mock_llm_client()
        )
    
    def test_complete_turn_execution(self, context_manager):
        """Test complete conversation turn with context updates."""
        # Arrange - Setup initial state
        turn_number = context_manager.start_new_turn("Test user message")
        
        # Act - Execute agent operations
        context_manager.add_code_snippet("test.py", "content", 1, 10)
        context_manager.add_tool_result("test_tool", {"result": "success"})
        
        # Assert - Verify expected outcomes
        context_dict, token_count = context_manager.assemble_context(10000)
        assert len(context_dict["conversation_history"]) == 1
        assert token_count > 0
```

#### Key Principles

1. **Complete Turn Simulation** - Test full conversation cycles
2. **Context State Validation** - Verify context is properly maintained
3. **Token Management** - Ensure token limits are respected
4. **Multi-turn Correlation** - Test conversation continuity

### 2. Workflow Orchestration Pattern

The workflow orchestration pattern tests all four workflow types with proper state management.

#### Pattern Structure

```python
class TestWorkflowOrchestration:
    @pytest.mark.asyncio
    async def test_sequential_workflow_execution(self, mock_agents):
        """Test sequential workflow with proper dependency management."""
        # Arrange - Setup workflow steps
        workflow_steps = [
            {"agent": "analysis", "task": "analyze_code"},
            {"agent": "implementation", "task": "implement_fix"},
            {"agent": "testing", "task": "run_tests"}
        ]
        
        # Act - Execute workflow
        results = await execute_sequential_workflow(workflow_steps, mock_agents)
        
        # Assert - Verify execution order and results
        assert len(results) == 3
        assert all(r.success for r in results)
        assert results[0].start_time < results[1].start_time < results[2].start_time
```

#### Workflow Types

1. **Sequential Workflows** - Step-by-step execution with dependencies
2. **Parallel Workflows** - Concurrent execution where possible
3. **Iterative Workflows** - Repeated cycles with feedback loops
4. **Human-in-Loop Workflows** - Human approval and intervention points

### 3. Context Management Testing Pattern

The context management pattern validates advanced context features like smart prioritization and RAG integration.

#### Pattern Structure

```python
class TestContextManagement:
    def test_smart_prioritization(self, prioritizer, test_data):
        """Test smart prioritization with relevance scoring."""
        # Arrange - Setup diverse content
        code_snippets = create_diverse_code_snippets()
        current_context = "Fix authentication security issues"
        
        # Act - Apply prioritization
        prioritized = prioritizer.prioritize_code_snippets(
            code_snippets, current_context, current_turn=5
        )
        
        # Assert - Verify prioritization logic
        assert len(prioritized) == len(code_snippets)
        assert prioritized[0]["_relevance_score"].final_score >= prioritized[-1]["_relevance_score"].final_score
        
        # Verify security-related content is prioritized
        security_items = [item for item in prioritized if "auth" in item["file_path"].lower()]
        assert len(security_items) > 0
```

#### Advanced Features

1. **Smart Prioritization** - Content relevance scoring
2. **Cross-turn Correlation** - Relationship detection across conversations
3. **Intelligent Summarization** - Context-aware content reduction
4. **Dynamic Context Expansion** - Automatic content discovery

### 4. Tool Orchestration Pattern

The tool orchestration pattern tests complex tool coordination with error handling and recovery.

#### Pattern Structure

```python
class TestToolOrchestration:
    @pytest.mark.asyncio
    async def test_tool_dependency_management(self, orchestrator):
        """Test tool execution with proper dependency handling."""
        # Arrange - Setup dependent tools
        dependencies = [
            ("read_file", {"file_path": "test.py"}, []),
            ("analyze_code", {"file_path": "test.py"}, ["read_file_0"]),
            ("fix_issues", {"file_path": "test.py"}, ["analyze_code_1"])
        ]
        
        # Act - Execute with dependencies
        results = []
        for i, (tool, args, deps) in enumerate(dependencies):
            result = await orchestrator.execute_tool(tool, args, deps, f"{tool}_{i}")
            results.append(result)
        
        # Assert - Verify dependency order
        assert all(r.status == ToolExecutionStatus.COMPLETED for r in results)
        assert results[0].execution_time < results[1].execution_time
```

#### Error Handling Features

1. **Automatic Recovery** - Retry logic with exponential backoff
2. **Fallback Strategies** - Alternative approaches when primary fails
3. **Error Classification** - Different recovery strategies per error type
4. **State Consistency** - Proper cleanup on failures

### 5. Performance Testing Pattern

The performance testing pattern validates system behavior under load and stress conditions.

#### Pattern Structure

```python
class TestPerformanceVerification:
    @pytest.fixture
    def performance_monitor(self):
        """Create performance monitor for metrics collection."""
        return PerformanceMonitor()
    
    @pytest.mark.asyncio
    async def test_load_testing_simulation(self, context_manager, performance_monitor):
        """Test system performance under concurrent load."""
        # Arrange - Setup load test parameters
        concurrent_users = 10
        operations_per_user = 50
        
        performance_monitor.start_monitoring()
        
        # Act - Simulate concurrent users
        async def simulate_user(user_id):
            for op in range(operations_per_user):
                # Simulate user operations
                context_manager.start_new_turn(f"User {user_id} operation {op}")
                # ... perform operations
                performance_monitor.record_operation(success=True)
        
        tasks = [simulate_user(i) for i in range(concurrent_users)]
        await asyncio.gather(*tasks)
        
        metrics = performance_monitor.stop_monitoring()
        
        # Assert - Verify performance thresholds
        assert metrics.success_rate >= 0.95
        assert metrics.throughput_ops_per_sec >= 100
        assert metrics.memory_usage_mb <= 1000
```

#### Performance Metrics

1. **Throughput** - Operations per second
2. **Memory Usage** - Real-time memory consumption
3. **CPU Usage** - Processor utilization
4. **Response Time** - Operation completion time

## Advanced Testing Patterns

### 1. Mock Strategy Pattern

Comprehensive mocking strategy for external dependencies.

#### LLM Client Mocking

```python
def create_mock_llm_client():
    """Create realistic LLM client mock."""
    client = AsyncMock()
    
    # Mock generate_content with realistic responses
    client.generate_content.return_value = AsyncMock(
        text="Mock LLM response",
        usage_metadata=AsyncMock(
            prompt_token_count=100,
            candidates_token_count=200,
            total_token_count=300
        )
    )
    
    # Mock count_tokens for token management
    client.count_tokens.return_value = AsyncMock(total_tokens=150)
    
    return client
```

#### Session State Mocking

```python
def create_mock_session_state():
    """Create mock session state for multi-agent coordination."""
    return {
        "conversation_id": "test-conversation-123",
        "current_phase": "analysis",
        "shared_context": {},
        "agent_states": {
            "analysis_agent": {"status": "ready", "last_action": None},
            "implementation_agent": {"status": "waiting", "dependencies": ["analysis"]},
            "testing_agent": {"status": "waiting", "dependencies": ["implementation"]}
        },
        "workflow_history": [],
        "error_count": 0,
        "performance_metrics": {
            "total_tokens": 0,
            "execution_time": 0.0,
            "memory_usage": 0.0
        }
    }
```

### 2. Fixture Strategy Pattern

Reusable test components for consistent test setup.

#### Parameterized Fixtures

```python
@pytest.fixture(params=[
    {"workflow_type": "sequential", "agent_count": 3},
    {"workflow_type": "parallel", "agent_count": 5},
    {"workflow_type": "iterative", "agent_count": 2},
    {"workflow_type": "human_in_loop", "agent_count": 4}
])
def workflow_config(request):
    """Parameterized workflow configuration."""
    return request.param

def test_workflow_execution(workflow_config, mock_agents):
    """Test with different workflow configurations."""
    # Test implementation adapts based on workflow_config
    pass
```

#### Scoped Fixtures

```python
@pytest.fixture(scope="module")
def performance_test_data():
    """Module-scoped performance test data."""
    return create_performance_test_data()

@pytest.fixture(scope="function")
def isolated_context_manager():
    """Function-scoped context manager for isolation."""
    return ContextManager(test_mode=True)
```

### 3. Assertion Strategy Pattern

Comprehensive assertion patterns for different validation types.

#### Context Validation

```python
def assert_context_consistency(context_dict, expected_components):
    """Assert context has expected components and structure."""
    assert isinstance(context_dict, dict)
    
    for component in expected_components:
        assert component in context_dict, f"Missing context component: {component}"
    
    if "conversation_history" in context_dict:
        assert len(context_dict["conversation_history"]) > 0
        for turn in context_dict["conversation_history"]:
            assert "turn_number" in turn
            assert "user_message" in turn or "agent_message" in turn
    
    if "tool_results" in context_dict:
        for result in context_dict["tool_results"]:
            assert "tool_name" in result
            assert "response" in result
            assert "summary" in result
```

#### Performance Validation

```python
def assert_performance_thresholds(metrics, thresholds):
    """Assert performance metrics meet defined thresholds."""
    assert metrics.execution_time <= thresholds["max_execution_time"]
    assert metrics.memory_usage_mb <= thresholds["max_memory_mb"]
    assert metrics.success_rate >= thresholds["min_success_rate"]
    assert metrics.throughput_ops_per_sec >= thresholds["min_throughput"]
```

### 4. Data Generation Pattern

Realistic test data generation for comprehensive testing.

#### Content Generation

```python
def create_diverse_code_snippets():
    """Create diverse code snippets for testing prioritization."""
    return [
        {
            "file_path": "src/auth.py",
            "content": "class AuthManager:\n    def authenticate(self, user, password):\n        return jwt.encode({...})",
            "language": "python",
            "complexity": "medium"
        },
        {
            "file_path": "src/config.py", 
            "content": "SECRET_KEY = 'hardcoded-secret-key'\nDEBUG = True",
            "language": "python",
            "complexity": "low"
        },
        {
            "file_path": "tests/test_auth.py",
            "content": "def test_authentication():\n    assert auth_manager.authenticate('user', 'pass')",
            "language": "python",
            "complexity": "low"
        }
    ]
```

#### Performance Test Data

```python
def create_performance_test_data():
    """Create realistic performance test data."""
    return {
        "large_files": [generate_large_file_content(i) for i in range(100)],
        "complex_queries": [generate_complex_query(i) for i in range(50)],
        "tool_chains": [generate_tool_chain(i) for i in range(25)],
        "user_scenarios": [generate_user_scenario(i) for i in range(200)]
    }
```

## Best Practices

### 1. Test Organization

#### File Structure

```
tests/
├── integration/
│   ├── test_agent_lifecycle.py
│   ├── test_context_management_advanced.py
│   ├── test_tool_orchestration_advanced.py
│   ├── test_performance_verification.py
│   └── run_integration_tests.py
├── fixtures/
│   ├── test_helpers.py
│   └── mock_data.py
└── conftest.py
```

#### Test Class Organization

```python
class TestFeatureArea:
    """Test class for specific feature area."""
    
    # Fixtures specific to this test class
    @pytest.fixture
    def feature_setup(self):
        """Setup for feature-specific tests."""
        pass
    
    # Basic functionality tests
    def test_basic_functionality(self):
        """Test basic feature functionality."""
        pass
    
    # Edge case tests
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        pass
    
    # Error handling tests
    def test_error_handling(self):
        """Test error conditions and recovery."""
        pass
    
    # Performance tests
    @pytest.mark.performance
    def test_performance_characteristics(self):
        """Test performance under load."""
        pass
```

### 2. Test Naming Conventions

#### Descriptive Test Names

```python
# Good: Describes what is being tested and expected outcome
def test_context_assembly_with_token_limit_respects_budget():
    """Test that context assembly respects token budget limits."""
    pass

def test_tool_orchestration_recovers_from_file_not_found_error():
    """Test tool orchestration handles file not found errors with retry."""
    pass

# Bad: Vague or unclear purpose
def test_context():
    pass

def test_tool_error():
    pass
```

#### Test Categories

```python
# Mark tests with appropriate categories
@pytest.mark.unit
def test_basic_functionality():
    pass

@pytest.mark.integration
def test_component_interaction():
    pass

@pytest.mark.performance
def test_load_handling():
    pass

@pytest.mark.slow
def test_comprehensive_scenario():
    pass
```

### 3. Mocking Best Practices

#### Realistic Behavior

```python
# Mock with realistic behavior patterns
def create_realistic_llm_mock():
    """Create LLM mock with realistic response patterns."""
    mock = AsyncMock()
    
    # Simulate response time variation
    async def mock_generate(*args, **kwargs):
        await asyncio.sleep(random.uniform(0.1, 0.5))  # Realistic response time
        return generate_realistic_response(*args, **kwargs)
    
    mock.generate_content.side_effect = mock_generate
    return mock
```

#### State Consistency

```python
# Maintain consistent state across mock interactions
class StatefulMock:
    def __init__(self):
        self.state = {"calls": 0, "context": {}}
    
    async def mock_method(self, *args, **kwargs):
        self.state["calls"] += 1
        # Update state based on method calls
        return self.generate_response_based_on_state()
```

### 4. Error Testing Patterns

#### Comprehensive Error Scenarios

```python
@pytest.mark.parametrize("error_type,expected_recovery", [
    ("file_not_found", "retry_with_alternatives"),
    ("permission_denied", "escalate_permissions"),
    ("timeout", "extend_timeout_and_retry"),
    ("rate_limit", "exponential_backoff"),
    ("network_error", "fallback_strategy")
])
def test_error_recovery_patterns(error_type, expected_recovery):
    """Test various error recovery patterns."""
    # Simulate specific error type
    # Verify expected recovery behavior
    pass
```

### 5. Performance Testing Patterns

#### Baseline and Regression Testing

```python
def test_performance_regression():
    """Test that performance hasn't regressed."""
    baseline_metrics = load_baseline_metrics()
    current_metrics = measure_current_performance()
    
    # Allow for some variance but catch significant regressions
    assert current_metrics.execution_time <= baseline_metrics.execution_time * 1.1
    assert current_metrics.memory_usage <= baseline_metrics.memory_usage * 1.1
```

#### Resource Monitoring

```python
def test_resource_usage_within_limits():
    """Test that resource usage stays within defined limits."""
    with ResourceMonitor() as monitor:
        # Execute test operations
        execute_test_scenario()
    
    # Verify resource usage
    assert monitor.peak_memory_mb <= 1000
    assert monitor.peak_cpu_percent <= 80
    assert monitor.open_file_descriptors <= 100
```

## Conftest.py Fixture Patterns

### 1. Fixture Organization Pattern

The integration test suite uses a dedicated `conftest.py` file for integration-specific fixtures following Google ADK patterns.

#### Fixture Hierarchy

```python
# tests/integration/conftest.py
import pytest
from tests.fixtures.test_helpers import create_mock_llm_client

# Session-scoped fixtures for expensive operations
@pytest.fixture(scope="session")
def performance_test_data():
    """Create test data once per session."""
    return create_performance_test_data()

# Function-scoped fixtures for isolated tests
@pytest.fixture(scope="function")
def mock_context_manager(mock_llm_client):
    """Create fresh context manager for each test."""
    return MockContextManager(
        model_name="test-model",
        max_llm_token_limit=100000,
        llm_client=mock_llm_client
    )

# Phase-specific fixtures combining multiple components
@pytest.fixture(scope="function")
def foundation_test_setup(mock_context_manager, mock_agent_pool, workflow_configs):
    """Complete setup for foundation phase tests."""
    return {
        "context_manager": mock_context_manager,
        "agent_pool": mock_agent_pool,
        "workflow_configs": workflow_configs
    }
```

### 2. Parametrized Fixture Pattern

Use parametrized fixtures to test multiple scenarios efficiently.

#### Workflow Scenario Testing

```python
@pytest.fixture(params=[
    {"workflow_type": "sequential", "agent_count": 3},
    {"workflow_type": "parallel", "agent_count": 5},
    {"workflow_type": "iterative", "agent_count": 2},
    {"workflow_type": "human_in_loop", "agent_count": 4}
])
def workflow_scenario(request):
    """Test different workflow scenarios."""
    return request.param

# Usage in tests
def test_workflow_execution(workflow_scenario):
    # Automatically runs with all 4 parameter combinations
    assert workflow_scenario['workflow_type'] in VALID_WORKFLOW_TYPES
    assert workflow_scenario['agent_count'] > 0
```

#### Load Testing Scenarios

```python
@pytest.fixture(params=[1, 5, 10, 25, 50])
def load_test_scenario(request):
    """Test different load levels."""
    return {
        "concurrent_users": request.param,
        "operations_per_user": 100,
        "expected_min_throughput": max(50, 500 / request.param)
    }
```

### 3. Conditional Fixture Pattern

Use conditional fixtures for environment-specific testing.

#### Environment-Specific Skipping

```python
def pytest_runtest_setup(item):
    """Setup for each test run with conditional skipping."""
    # Skip performance tests on slow systems
    if "performance" in item.keywords:
        if os.environ.get("SKIP_PERFORMANCE_TESTS", "false").lower() == "true":
            pytest.skip("Performance tests skipped on slow systems")
    
    # Skip stress tests unless explicitly requested
    if "stress" in item.keywords:
        if os.environ.get("RUN_STRESS_TESTS", "false").lower() != "true":
            pytest.skip("Stress tests skipped unless explicitly requested")
```

### 4. Fixture Dependency Pattern

Create fixtures that depend on other fixtures for complex setups.

#### Layered Dependencies

```python
@pytest.fixture(scope="function")
def mock_llm_client():
    """Base LLM client mock."""
    return create_mock_llm_client()

@pytest.fixture(scope="function")
def mock_context_manager(mock_llm_client):
    """Context manager that depends on LLM client."""
    return MockContextManager(llm_client=mock_llm_client)

@pytest.fixture(scope="function")
def mock_devops_agent(mock_context_manager, mock_llm_client):
    """Agent that depends on context manager and LLM client."""
    return MockDevOpsAgent(
        context_manager=mock_context_manager,
        llm_client=mock_llm_client
    )

@pytest.fixture(scope="function")
def complete_integration_setup(mock_devops_agent, mock_performance_monitor):
    """Complete setup depending on multiple components."""
    return {
        "agent": mock_devops_agent,
        "monitor": mock_performance_monitor,
        "ready": True
    }
```

### 5. Cleanup Fixture Pattern

Implement automatic cleanup to prevent test pollution.

#### Automatic Cleanup

```python
@pytest.fixture(scope="function", autouse=True)
def cleanup_after_test():
    """Automatic cleanup after each test."""
    yield
    
    # Clean up any temporary files
    temp_files = ["test_temp_file.txt", "test_context.json"]
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
    
    # Create session info
    session_info = {
        "session_id": f"integration_test_session_{int(time.time())}",
        "start_time": time.time()
    }
    
    yield session_info
    
    # Session cleanup
    logger.info("Ending integration test session")
```

### 6. Metrics Collection Pattern

Use fixtures to collect test metrics and performance data.

#### Test Metrics Collection

```python
@pytest.fixture(scope="function")
def test_metrics_collector():
    """Collect test metrics during execution."""
    class MetricsCollector:
        def __init__(self):
            self.metrics = []
            self.start_time = time.time()
        
        def record_metric(self, name: str, value: float, tags: Dict[str, str] = None):
            self.metrics.append({
                "name": name,
                "value": value,
                "timestamp": time.time(),
                "tags": tags or {}
            })
        
        def get_summary(self) -> Dict[str, Any]:
            return {
                "total_metrics": len(self.metrics),
                "execution_time": time.time() - self.start_time,
                "metrics": self.metrics
            }
    
    return MetricsCollector()

# Usage in tests
def test_with_metrics(test_metrics_collector):
    test_metrics_collector.record_metric("test_start", 1.0)
    # ... test operations ...
    test_metrics_collector.record_metric("test_end", 1.0)
    
    summary = test_metrics_collector.get_summary()
    assert summary["total_metrics"] == 2
```

### 7. Mock State Management Pattern

Maintain consistent state across mock interactions.

#### Stateful Mock Fixtures

```python
@pytest.fixture(scope="function")
def stateful_mock_context():
    """Create stateful mock context that maintains consistency."""
    class StatefulMockContext:
        def __init__(self):
            self.code_snippets = []
            self.tool_results = []
            self.conversation_history = []
            self.turn_count = 0
        
        def add_code_snippet(self, file_path, content, start_line=1, end_line=None):
            snippet = {
                "file_path": file_path,
                "content": content,
                "start_line": start_line,
                "end_line": end_line or start_line + len(content.split('\n'))
            }
            self.code_snippets.append(snippet)
            return snippet
        
        def start_new_turn(self, message):
            self.turn_count += 1
            turn = {
                "turn_number": self.turn_count,
                "user_message": message,
                "timestamp": time.time()
            }
            self.conversation_history.append(turn)
            return self.turn_count
        
        def get_state(self):
            return {
                "code_snippets": len(self.code_snippets),
                "tool_results": len(self.tool_results),
                "conversation_history": len(self.conversation_history),
                "turn_count": self.turn_count
            }
    
    return StatefulMockContext()
```

### 8. Error Simulation Pattern

Create fixtures for testing error scenarios.

#### Error Simulation Configuration

```python
@pytest.fixture(scope="function")
def error_simulation_config():
    """Configuration for error simulation tests."""
    return {
        "error_types": [
            "network_error",
            "timeout_error", 
            "rate_limit_error",
            "authentication_error",
            "validation_error"
        ],
        "error_probabilities": {
            "network_error": 0.1,
            "timeout_error": 0.05,
            "rate_limit_error": 0.02,
            "authentication_error": 0.01,
            "validation_error": 0.03
        },
        "recovery_strategies": {
            "network_error": "retry_with_backoff",
            "timeout_error": "extend_timeout",
            "rate_limit_error": "exponential_backoff",
            "authentication_error": "refresh_credentials",
            "validation_error": "validate_and_retry"
        }
    }
```

### 9. Performance Monitoring Pattern

Integrate performance monitoring into fixtures.

#### Performance Monitoring Integration

```python
@pytest.fixture(scope="function")
def performance_monitor():
    """Monitor test performance metrics."""
    class PerformanceMonitor:
        def __init__(self):
            self.metrics = []
            self.start_time = None
        
        def start_monitoring(self):
            self.start_time = time.time()
        
        def stop_monitoring(self):
            return MagicMock(
                execution_time=time.time() - (self.start_time or time.time()),
                peak_memory_mb=100,
                operations_per_second=100
            )
        
        def record_operation(self, success=True):
            self.metrics.append({
                "success": success,
                "timestamp": time.time()
            })
    
    return PerformanceMonitor()
```

## Testing Anti-Patterns to Avoid

### 1. Flaky Tests

```python
# Bad: Time-dependent test that can fail randomly
def test_operation_timing():
    start = time.time()
    execute_operation()
    end = time.time()
    assert end - start < 1.0  # Flaky due to system variance

# Good: Test behavior, not exact timing
def test_operation_completes_within_reasonable_time():
    with timeout(5.0):  # Reasonable upper bound
        execute_operation()
    # Test succeeded if no timeout
```

### 2. Overly Complex Tests

```python
# Bad: Testing too many things in one test
def test_everything():
    # Setup for multiple unrelated features
    # Test feature A
    # Test feature B  
    # Test feature C
    # Complex assertions mixing concerns

# Good: Focused tests
def test_specific_feature():
    # Setup for one feature
    # Test one specific aspect
    # Clear, focused assertions
```

### 3. Inadequate Mocking

```python
# Bad: Over-mocking or under-mocking
def test_with_everything_mocked():
    # Mock everything including the system under test
    # Test becomes meaningless

# Good: Mock external dependencies only
def test_with_appropriate_mocks():
    # Mock external services, databases, APIs
    # Test real integration between internal components
```

## Conclusion

These test patterns and practices provide a solid foundation for building reliable, maintainable, and comprehensive integration tests. By following these patterns, you can ensure your test suite effectively validates the complex interactions in your multi-agent system while remaining maintainable and providing clear feedback on system behavior.

Remember to:
- Keep tests focused and independent
- Use realistic mocking strategies
- Validate both happy path and error conditions
- Monitor performance and resource usage
- Maintain clear documentation and naming conventions

For specific implementation examples, see the [Integration Testing Guide](integration-testing.md) and [Performance Testing Guide](performance-testing.md). 