---
title: Integration Testing Guide
layout: default
nav_order: 1
parent: Testing
---

# Integration Testing Guide

This guide covers the comprehensive integration test suite for the ADK Agents system, designed following Google ADK integration testing patterns and best practices.

## Overview

The integration test suite provides end-to-end validation of the multi-agent system, including:

- **Agent Lifecycle Management** - Complete conversation turns with context management
- **Workflow Orchestration** - Sequential, parallel, iterative, and human-in-loop patterns
- **Context Management** - Smart prioritization, cross-turn correlation, and RAG integration
- **Tool Orchestration** - Advanced tool coordination with error handling
- **Performance Verification** - Load testing, optimization validation, and stress testing

## Test Suite Architecture

### 4-Phase Implementation

The integration tests are organized into 4 distinct phases:

#### Phase 1: Foundation Tests
- **Agent Lifecycle Tests** - Basic conversation turn execution
- **Workflow Orchestration** - Core workflow pattern validation
- **Context Flow** - Multi-turn context management
- **Token Management** - Budget management and optimization

#### Phase 2: Core Integration Tests
- **Smart Prioritization** - Content relevance scoring
- **Cross-turn Correlation** - Conversation relationship detection
- **Intelligent Summarization** - Context-aware content reduction
- **Dynamic Context Expansion** - Automatic content discovery
- **RAG Integration** - Semantic search and indexing

#### Phase 3: Tool Orchestration Tests
- **Sequential Tool Execution** - Dependency management
- **Parallel Tool Execution** - Performance optimization
- **Error Handling** - Recovery mechanisms
- **State Management** - Tool coordination
- **Complex Workflows** - Multi-phase execution

#### Phase 4: Performance Verification
- **Load Testing** - Concurrent user simulation
- **Performance Comparison** - Parallel vs sequential execution
- **Memory Optimization** - Leak detection and management
- **Token Optimization** - Counting performance
- **Stress Testing** - Extreme scenario handling

## Package Management

**Important**: This project uses `uv` exclusively for all Python package management tasks. Never use `pip` directly.

### Installation and Setup

```bash
# Install dependencies
uv sync --dev

# Install additional test dependencies
uv add --dev pytest-xdist pytest-benchmark

# Install project in development mode
uv pip install -e .

# Check installed packages
uv pip list
```

### Running Tests with uv

All test commands should be prefixed with `uv run`:

```bash
# Basic test execution
uv run pytest

# With specific options
uv run pytest --cov=src --cov-report=html

# Run specific test files
uv run pytest tests/integration/test_agent_lifecycle.py

# Run with markers
uv run pytest -m "integration and foundation"
```

### Why uv?

- **Consistency**: Ensures all team members use the same package versions
- **Performance**: Faster dependency resolution and installation
- **Reliability**: Better handling of dependency conflicts
- **Modern**: State-of-the-art Python package management

## Quick Start

### Running All Tests

```bash
# Run the complete integration test suite
./tests/integration/run_integration_tests.py

# Run with detailed output
./tests/integration/run_integration_tests.py --verbose

# Run in parallel mode (faster)
./tests/integration/run_integration_tests.py --parallel

# Test conftest.py fixtures
uv run pytest tests/integration/test_conftest_example.py -v

# Run integration tests with pytest directly
uv run pytest tests/integration/ -m "integration and foundation" -v
```

### Running Specific Test Suites

```bash
# Run only foundation tests
./tests/integration/run_integration_tests.py --suite "Foundation"

# Run only performance tests
./tests/integration/run_integration_tests.py --suite "Performance"

# Run only tool orchestration tests
./tests/integration/run_integration_tests.py --suite "Tool Orchestration"
```

### Including Stress Tests

```bash
# Run all tests including stress tests
./tests/integration/run_integration_tests.py --stress
```

## Test Files Overview

### Core Test Files

| File | Purpose | Test Count |
|------|---------|------------|
| `test_agent_lifecycle.py` | Agent lifecycle and workflow orchestration | 12+ |
| `test_context_management_advanced.py` | Advanced context management with RAG | 15+ |
| `test_tool_orchestration_advanced.py` | Tool orchestration with error handling | 18+ |
| `test_performance_verification.py` | Performance and load testing | 12+ |
| `test_conftest_example.py` | Fixture usage examples and validation | 26+ |
| `run_integration_tests.py` | Comprehensive test runner | N/A |

### Test Utilities

| File | Purpose |
|------|---------|
| `tests/fixtures/test_helpers.py` | Mock utilities and test fixtures |
| `tests/conftest.py` | Main pytest configuration and shared fixtures |
| `tests/integration/conftest.py` | Integration-specific fixtures and configuration |

## Understanding Test Results

### Test Output Format

```
🧪 INTEGRATION TEST SUITE SUMMARY
================================================================================
Total Duration: 45.2s
Total Tests: 57
Passed: 57 ✅
Failed: 0 ❌
Success Rate: 100.0%
Test Suites: 4

📋 TEST SUITE BREAKDOWN:
  ✅ Foundation Tests: 8/8 passed (100.0%)
  ✅ Core Integration Tests: 15/15 passed (100.0%)
  ✅ Tool Orchestration Tests: 18/18 passed (100.0%)
  ✅ Performance Verification Tests: 16/16 passed (100.0%)

⚡ PERFORMANCE METRICS:
  Fastest Test: test_token_counting_performance (0.012s)
  Slowest Test: test_load_testing_simulation (8.450s)
  Average Test Duration: 0.793s

💡 RECOMMENDATIONS:
  🎉 Perfect test suite! All tests passing - excellent work!
```

### Report Files

Test results are automatically saved to `test_reports/` with detailed JSON reports including:

- **Test execution details** with timings and results
- **Performance metrics** with memory and CPU usage
- **Error analysis** with detailed failure information
- **Recommendations** for optimization and improvements

## Key Features

### Integration-Specific Configuration

The `tests/integration/conftest.py` file provides:

- **Comprehensive Fixture Library** - All fixtures needed for different test phases
- **Custom Test Markers** - Foundation, core, orchestration, verification phase markers
- **Environment Setup** - Automatic test environment configuration
- **Parametrized Testing** - Multiple scenarios for workflow, load, and context testing
- **Error Simulation** - Configuration for testing error handling scenarios
- **Performance Monitoring** - Integration with performance testing infrastructure
- **Automatic Cleanup** - Session and test-level cleanup management
- **Skip Conditions** - Environment-specific test skipping (performance, stress, load tests)

### Advanced Mocking

The test suite includes sophisticated mocking for:

- **LLM Clients** - Realistic response simulation
- **Session States** - Multi-agent state management
- **Test Workspaces** - Isolated test environments
- **Tool Execution** - Comprehensive tool behavior simulation

### Performance Monitoring

Built-in performance monitoring tracks:

- **Memory Usage** - Real-time memory consumption
- **CPU Usage** - Processor utilization
- **Token Counting** - Token processing performance
- **Context Assembly** - Context generation timing
- **Throughput** - Operations per second

### Error Handling Validation

Comprehensive error scenario testing:

- **Recovery Mechanisms** - Automatic error recovery
- **Retry Logic** - Configurable retry strategies
- **Fallback Behavior** - Graceful degradation
- **State Consistency** - Error state management

### Load Testing

Realistic load testing capabilities:

- **Concurrent Users** - Multiple simultaneous sessions
- **Resource Monitoring** - System resource tracking
- **Throughput Testing** - Performance under load
- **Scalability Analysis** - System capacity evaluation

## Using Conftest.py Fixtures

The integration test suite includes comprehensive fixtures for all testing scenarios. Here's how to use them:

### Basic Fixture Usage

```python
import pytest

@pytest.mark.integration
@pytest.mark.foundation
class TestMyFeature:
    def test_with_basic_fixtures(self, mock_llm_client, mock_session_state, test_workspace):
        # Use mock LLM client
        assert mock_llm_client is not None
        assert hasattr(mock_llm_client, 'generate')
        
        # Use mock session state
        assert 'agent_coordination' in mock_session_state
        assert 'context_state' in mock_session_state
        
        # Use test workspace
        assert 'workspace_dir' in test_workspace
```

### Context Management Fixtures

```python
@pytest.mark.integration
@pytest.mark.core
class TestContextManagement:
    def test_context_features(self, mock_context_manager, mock_smart_prioritizer, mock_rag_system):
        # Add content to context
        mock_context_manager.add_code_snippet("test.py", "print('hello')")
        mock_context_manager.add_tool_result("test_tool", {"result": "success"})
        
        # Assemble context
        context, token_count = mock_context_manager.assemble_context(10000)
        assert context is not None
        assert token_count > 0
        
        # Use smart prioritizer
        snippets = [{"content": "test code", "file_path": "test.py"}]
        prioritized = mock_smart_prioritizer.prioritize_code_snippets(snippets, "test context")
        assert len(prioritized) == 1
        
        # Use RAG system
        rag_results = mock_rag_system.query("test query", top_k=3)
        assert len(rag_results) == 3
```

### Agent Fixtures

```python
@pytest.mark.integration
@pytest.mark.foundation
class TestAgents:
    def test_agent_types(self, mock_devops_agent, mock_software_engineer_agent, mock_swe_agent):
        agents = [mock_devops_agent, mock_software_engineer_agent, mock_swe_agent]
        
        for agent in agents:
            assert hasattr(agent, 'name')
            assert hasattr(agent, 'context_manager')
            assert hasattr(agent, 'process_message')
```

### Async Fixtures

```python
@pytest.mark.integration
@pytest.mark.asyncio
class TestAsyncOperations:
    async def test_workflow_execution(self, mock_workflow_engine, mock_tool_orchestrator):
        # Test workflow engine
        result = await mock_workflow_engine.execute_workflow(
            "test_workflow", 
            ["agent1", "agent2"], 
            {"config": "test"}
        )
        assert result["success"] is True
        
        # Test tool orchestrator
        tool_result = await mock_tool_orchestrator.execute_tool(
            "test_tool", 
            {"arg1": "value1"}, 
            tool_id="test_tool_1"
        )
        assert tool_result.status == "COMPLETED"
```

### Performance Fixtures

```python
@pytest.mark.integration
@pytest.mark.performance
class TestPerformance:
    def test_monitoring(self, mock_performance_monitor, test_metrics_collector):
        # Start monitoring
        mock_performance_monitor.start_monitoring()
        
        # Record metrics
        test_metrics_collector.record_metric("execution_time", 1.5, {"test": "example"})
        
        # Stop monitoring
        metrics = mock_performance_monitor.stop_monitoring()
        assert hasattr(metrics, 'execution_time')
        assert hasattr(metrics, 'peak_memory_mb')
```

### Parametrized Fixtures

```python
@pytest.mark.integration
@pytest.mark.core
class TestParametrizedScenarios:
    def test_workflow_scenarios(self, workflow_scenario):
        # Automatically tests with different workflow configurations
        assert workflow_scenario['workflow_type'] in ["sequential", "parallel", "iterative", "human_in_loop"]
        assert workflow_scenario['agent_count'] > 0
        
    def test_context_scenarios(self, context_scenario):
        # Automatically tests with different context sizes
        assert context_scenario['context_size'] > 0
        assert context_scenario['token_limit'] > context_scenario['context_size']
```

### Phase-Specific Fixtures

```python
@pytest.mark.integration
@pytest.mark.foundation
class TestFoundationPhase:
    def test_foundation_setup(self, foundation_test_setup):
        # Complete foundation test setup
        assert 'context_manager' in foundation_test_setup
        assert 'agent_pool' in foundation_test_setup
        assert 'workflow_configs' in foundation_test_setup

@pytest.mark.integration
@pytest.mark.core
class TestCorePhase:
    def test_core_setup(self, core_integration_setup):
        # Complete core integration test setup
        assert 'smart_prioritizer' in core_integration_setup
        assert 'cross_turn_correlator' in core_integration_setup
        assert 'rag_system' in core_integration_setup
```

### Test Markers

Use these markers to categorize and run specific test types:

```python
@pytest.mark.integration          # All integration tests
@pytest.mark.foundation           # Foundation phase tests
@pytest.mark.core                 # Core integration phase tests
@pytest.mark.orchestration        # Tool orchestration phase tests
@pytest.mark.verification         # Performance verification phase tests
@pytest.mark.performance          # Performance tests
@pytest.mark.slow                 # Slow tests (>5 seconds)
@pytest.mark.stress               # Stress tests
@pytest.mark.load                 # Load tests
```

### Example: Complete Integration Test

```python
@pytest.mark.integration
@pytest.mark.foundation
class TestCompleteScenario:
    @pytest.mark.asyncio
    async def test_complete_workflow(
        self, 
        mock_devops_agent, 
        mock_context_manager, 
        mock_workflow_engine,
        mock_performance_monitor,
        test_metrics_collector
    ):
        # Start performance monitoring
        mock_performance_monitor.start_monitoring()
        test_metrics_collector.record_metric("test_start", 1.0, {"phase": "setup"})
        
        # Setup context
        mock_context_manager.add_code_snippet("main.py", "def main(): pass")
        mock_context_manager.add_tool_result("analyze_code", {"complexity": "low"})
        
        # Start conversation turn
        turn_id = mock_context_manager.start_new_turn("Fix the code issues")
        
        # Process message through agent
        response = await mock_devops_agent.process_message("Fix the code issues")
        assert response["success"] is True
        
        # Execute workflow
        workflow_result = await mock_workflow_engine.execute_workflow(
            "fix_issues", 
            [mock_devops_agent], 
            {"priority": "high"}
        )
        assert workflow_result["success"] is True
        
        # Stop performance monitoring
        performance_metrics = mock_performance_monitor.stop_monitoring()
        test_metrics_collector.record_metric(
            "test_execution_time", 
            performance_metrics.execution_time, 
            {"test": "complete_workflow"}
        )
        
        # Verify final state
        context, token_count = mock_context_manager.assemble_context(50000)
        assert len(context["conversation_history"]) == 1
        assert len(context["code_snippets"]) == 1
        assert len(context["tool_results"]) == 1
```

## Best Practices

### Test Organization

1. **Follow the 4-phase structure** - Foundation → Core → Tool → Performance
2. **Use descriptive test names** - Clear intent and scope
3. **Implement proper fixtures** - Reusable test components
4. **Mock external dependencies** - Isolated test execution

### Performance Considerations

1. **Use parallel execution** - Faster test runs where possible
2. **Monitor resource usage** - Prevent test environment impact
3. **Set appropriate timeouts** - Balance thoroughness with speed
4. **Profile slow tests** - Identify optimization opportunities

### Maintenance

1. **Keep tests up-to-date** - Sync with system changes
2. **Review test coverage** - Ensure comprehensive validation
3. **Update mocks regularly** - Maintain realistic behavior
4. **Document new patterns** - Share knowledge with team

## Integration with CI/CD

### GitHub Actions Integration

```yaml
name: Integration Tests
on: [push, pull_request]
jobs:
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          uv sync
      - name: Run integration tests
        run: |
          ./tests/integration/run_integration_tests.py --parallel
```

### Performance Monitoring

Set up performance thresholds:

```yaml
- name: Check performance thresholds
  run: |
    python -c "
    import json
    with open('test_reports/integration_test_report_latest.json') as f:
        report = json.load(f)
    avg_duration = report['performance_metrics']['average_test_duration']
    if avg_duration > 2.0:
        raise Exception(f'Average test duration too high: {avg_duration}s')
    print(f'Performance check passed: {avg_duration}s average')
    "
```

## Troubleshooting

### Common Issues

1. **Test Timeouts** - Increase timeout values or optimize slow tests
2. **Memory Issues** - Check for memory leaks in test setup/teardown
3. **Mock Failures** - Ensure mocks match actual system behavior
4. **Flaky Tests** - Add proper wait conditions and state validation

### Debug Mode

Enable verbose logging for detailed debugging:

```bash
./tests/integration/run_integration_tests.py --verbose
```

### Environment Issues

Ensure proper test environment setup:

```bash
# Install test dependencies
uv sync --dev

# Set environment variables
export DEVOPS_AGENT_TESTING=true
export DEVOPS_AGENT_LOG_LEVEL=DEBUG
```

## Next Steps

1. **Run the complete test suite** to validate your implementation
2. **Review test reports** for performance insights
3. **Integrate into CI/CD** for continuous validation
4. **Expand test coverage** as your system evolves
5. **Share knowledge** with your development team

For detailed information about specific test patterns, see the [Test Patterns Guide](test-patterns.md).

For performance testing specifics, see the [Performance Testing Guide](performance-testing.md).

For troubleshooting help, see the [Troubleshooting Guide](troubleshooting.md). 