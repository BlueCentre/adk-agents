---
title: Troubleshooting Guide
layout: default
nav_order: 4
parent: Testing
---

# Troubleshooting Guide

This guide provides solutions for common issues encountered when running the ADK Agents integration test suite.

## Common Issues and Solutions

### 1. Test Execution Issues

#### Tests Not Running

**Symptoms:**
- No tests discovered or executed
- Import errors when running tests
- Module not found errors

**Solutions:**

```bash
# Check Python environment
uv run python --version
which python  # For system comparison

# Verify test dependencies
pip list | grep -E "(pytest|asyncio|mock)"

# Install missing dependencies
pip install -r requirements-test.txt

# Check PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Run tests with verbose output
./tests/integration/run_integration_tests.py --verbose
```

#### Import Errors

**Symptoms:**
```
ImportError: cannot import name 'ContextManager' from 'agents.devops.components.context_management'
ModuleNotFoundError: No module named 'agents.devops'
```

**Solutions:**

```bash
# Add project root to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Install package in development mode
uv pip install -e .

# Check package structure
ls -la agents/devops/components/context_management/

# Verify __init__.py files exist
find agents/ -name "__init__.py"
```

### 2. Mock-Related Issues

#### Mock Failures

**Symptoms:**
- AttributeError: 'Mock' object has no attribute 'X'
- Unexpected mock behavior
- Tests passing when they should fail

**Solutions:**

```python
# Use AsyncMock for async functions
from unittest.mock import AsyncMock, MagicMock

# Create properly configured mocks
def create_mock_llm_client():
    client = AsyncMock()
    client.generate_content.return_value = AsyncMock(
        text="Mock response",
        usage_metadata=AsyncMock(
            total_token_count=100
        )
    )
    return client

# Verify mock calls
mock_client = create_mock_llm_client()
# ... use mock
mock_client.generate_content.assert_called_once()
```

#### Mock State Issues

**Symptoms:**
- Mocks not resetting between tests
- Unexpected mock behavior from previous tests
- Inconsistent test results

**Solutions:**

```python
# Use proper fixture scope
@pytest.fixture(scope="function")  # Not "session" or "module"
def mock_client():
    return create_mock_llm_client()

# Manual reset if needed
@pytest.fixture(autouse=True)
def reset_mocks():
    yield
    # Reset any persistent mocks here
    reset_all_mocks()
```

### 3. Async/Await Issues

#### Async Test Failures

**Symptoms:**
- RuntimeError: This event loop is already running
- TypeError: object is not awaitable
- Tests hanging or not completing

**Solutions:**

```python
# Use proper async test decoration
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_operation()
    assert result is not None

# Check for missing awaits
async def test_with_proper_await():
    # Wrong: result = async_function()
    # Right: result = await async_function()
    result = await async_function()
    assert result is not None

# Use asyncio.run for non-test async code
import asyncio

def run_async_test():
    async def test_logic():
        # Test implementation
        pass
    
    asyncio.run(test_logic())
```

#### Event Loop Issues

**Symptoms:**
- RuntimeError: cannot be called from a running event loop
- Event loop conflicts between tests

**Solutions:**

```python
# Use pytest-asyncio properly
# In conftest.py
import pytest
import asyncio

@pytest.fixture(scope="function")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# Or use asyncio.create_task for concurrent operations
async def test_concurrent_operations():
    tasks = [
        asyncio.create_task(operation1()),
        asyncio.create_task(operation2()),
        asyncio.create_task(operation3())
    ]
    results = await asyncio.gather(*tasks)
    assert len(results) == 3
```

### 4. Context Management Issues

#### Context Assembly Failures

**Symptoms:**
- Empty context dictionaries
- Missing context components
- Token counting errors

**Solutions:**

```python
# Debug context assembly
def debug_context_assembly(context_manager):
    print(f"Code snippets: {len(context_manager.code_snippets)}")
    print(f"Tool results: {len(context_manager.tool_results)}")
    print(f"Conversation history: {len(context_manager.conversation_history)}")
    
    context_dict, token_count = context_manager.assemble_context(10000)
    print(f"Assembled context keys: {list(context_dict.keys())}")
    print(f"Token count: {token_count}")
    
    return context_dict, token_count

# Check context manager initialization
context_manager = ContextManager(
    model_name="test-model",
    max_llm_token_limit=100000,
    llm_client=create_mock_llm_client()
)

# Verify content addition
context_manager.add_code_snippet("test.py", "content", 1, 10)
assert len(context_manager.code_snippets) == 1
```

#### Token Counting Issues

**Symptoms:**
- Incorrect token counts
- Token counting taking too long
- Token limit not respected

**Solutions:**

```python
# Mock token counting for tests
def create_mock_token_counter():
    def mock_count_tokens(text):
        # Simple approximation for testing
        return len(text.split()) * 1.3  # Rough token estimate
    
    return mock_count_tokens

# Test token counting behavior
def test_token_counting():
    context_manager = ContextManager(
        model_name="test-model",
        max_llm_token_limit=100000,
        llm_client=create_mock_llm_client()
    )
    
    # Add content with known token count
    test_content = "hello world test"
    context_manager.add_code_snippet("test.py", test_content, 1, 10)
    
    context_dict, token_count = context_manager.assemble_context(10000)
    assert token_count > 0
    assert token_count < 10000  # Should be within limit
```

### 5. Performance Test Issues

#### Performance Test Failures

**Symptoms:**
- Performance tests failing due to system load
- Inconsistent performance results
- Tests timing out

**Solutions:**

```python
# Use relative performance thresholds
def test_performance_with_baseline():
    # Run operation multiple times
    times = []
    for i in range(5):
        start = time.time()
        perform_operation()
        end = time.time()
        times.append(end - start)
    
    # Use median time to avoid outliers
    median_time = sorted(times)[len(times) // 2]
    
    # Compare against baseline with tolerance
    baseline_time = load_baseline_time()
    assert median_time <= baseline_time * 1.5  # 50% tolerance

# Skip performance tests on slow systems
@pytest.mark.skipif(
    is_slow_system(),
    reason="Performance tests skipped on slow systems"
)
def test_performance_requirement():
    # Performance test implementation
    pass
```

#### Resource Monitoring Issues

**Symptoms:**
- Resource monitoring not working
- Memory/CPU measurements incorrect
- Monitoring interfering with tests

**Solutions:**

```python
# Check if monitoring dependencies are available
def check_monitoring_availability():
    try:
        import psutil
        return True
    except ImportError:
        return False

# Use monitoring conditionally
class ConditionalResourceMonitor:
    def __init__(self):
        self.monitoring_available = check_monitoring_availability()
        if self.monitoring_available:
            import psutil
            self.process = psutil.Process()
    
    def get_memory_usage(self):
        if self.monitoring_available:
            return self.process.memory_info().rss / 1024 / 1024
        return 0  # Return 0 if monitoring not available

# Use mock monitoring for tests
@pytest.fixture
def performance_monitor():
    if check_monitoring_availability():
        return ResourceMonitor()
    else:
        return MockResourceMonitor()
```

### 6. Test Data Issues

#### Test Data Generation Problems

**Symptoms:**
- Inconsistent test data
- Test data generation taking too long
- Memory issues with large test data

**Solutions:**

```python
# Use deterministic test data generation
import random

def create_test_data(seed=42):
    random.seed(seed)  # Ensure reproducible results
    
    return {
        "code_snippets": [
            {
                "file_path": f"test_{i}.py",
                "content": f"def test_{i}():\n    pass",
                "language": "python"
            }
            for i in range(10)
        ]
    }

# Cache expensive test data
@pytest.fixture(scope="session")
def expensive_test_data():
    # Generate once per test session
    return create_expensive_test_data()

# Use lazy generation for large datasets
class LazyTestDataGenerator:
    def __init__(self, count):
        self.count = count
        self._data = None
    
    @property
    def data(self):
        if self._data is None:
            self._data = [self.generate_item(i) for i in range(self.count)]
        return self._data
    
    def generate_item(self, index):
        return {"id": index, "content": f"test content {index}"}
```

### 7. Environment Issues

#### Environment Configuration Problems

**Symptoms:**
- Tests behaving differently on different machines
- Environment variables not set
- Dependency version conflicts

**Solutions:**

```bash
# Check environment configuration
echo $PYTHONPATH
echo $DEVOPS_AGENT_TESTING
echo $DEVOPS_AGENT_LOG_LEVEL

# Set required environment variables
export DEVOPS_AGENT_TESTING=true
export DEVOPS_AGENT_LOG_LEVEL=DEBUG

# Check Python environment
uv run python -c "import sys; print(sys.path)"
pip freeze | grep -E "(pytest|asyncio|mock)"

# Create isolated environment
python -m venv test_env
source test_env/bin/activate
uv sync --dev
```

#### Dependency Conflicts

**Symptoms:**
- ImportError with package version conflicts
- Tests working in one environment but not another
- Mysterious test failures

**Solutions:**

```bash
# Check for dependency conflicts
pip check

# Create requirements file with specific versions
pip freeze > requirements-test-frozen.txt

# Use virtual environment
python -m venv clean_env
source clean_env/bin/activate
uv sync --frozen

# Check for duplicate packages
pip list | sort | uniq -d
```

## Debugging Techniques

### 1. Verbose Logging

#### Enable Debug Logging

```python
import logging

# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add logging to test components
logger = logging.getLogger(__name__)

def test_with_logging():
    logger.debug("Starting test")
    logger.info("Test checkpoint 1")
    
    try:
        result = perform_operation()
        logger.info(f"Operation result: {result}")
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        raise
    
    logger.debug("Test completed")
```

#### Test-Specific Logging

```python
@pytest.fixture
def enable_debug_logging():
    """Enable debug logging for a specific test."""
    logger = logging.getLogger("agents.devops")
    original_level = logger.level
    logger.setLevel(logging.DEBUG)
    
    yield
    
    logger.setLevel(original_level)

def test_with_debug_logging(enable_debug_logging):
    # Test will have debug logging enabled
    pass
```

### 2. Test Isolation

#### Isolate Failing Tests

```python
# Run single test for debugging
uv run pytest tests/integration/test_context_management_advanced.py::TestSmartPrioritization::test_smart_prioritization -v

# Run with pdb debugger
uv run pytest tests/integration/test_context_management_advanced.py::TestSmartPrioritization::test_smart_prioritization -v --pdb

# Run with custom markers
@pytest.mark.debug
def test_problematic_behavior():
    # Test implementation
    pass

# Run only debug tests
uv run pytest -m debug -v
```

#### Test State Inspection

```python
import pdb

def test_with_debugging():
    # Setup
    context_manager = create_context_manager()
    
    # Debug point
    pdb.set_trace()  # Interactive debugging
    
    # Continue test
    result = context_manager.assemble_context(10000)
    
    # Inspect state
    print(f"Context keys: {list(result[0].keys())}")
    print(f"Token count: {result[1]}")
```

### 3. Mock Debugging

#### Debug Mock Behavior

```python
def debug_mock_calls(mock_object):
    """Debug mock object calls."""
    print(f"Called: {mock_object.called}")
    print(f"Call count: {mock_object.call_count}")
    print(f"Call args: {mock_object.call_args}")
    print(f"Call args list: {mock_object.call_args_list}")

# Use in tests
def test_with_mock_debugging():
    mock_client = create_mock_llm_client()
    
    # Use mock
    result = mock_client.generate_content("test")
    
    # Debug mock state
    debug_mock_calls(mock_client.generate_content)
```

#### Verify Mock Setup

```python
def verify_mock_setup(mock_client):
    """Verify mock is configured correctly."""
    assert hasattr(mock_client, 'generate_content')
    assert hasattr(mock_client, 'count_tokens')
    
    # Test mock responses
    response = mock_client.generate_content("test")
    assert response is not None
    assert hasattr(response, 'text')
    assert hasattr(response, 'usage_metadata')
```

### 4. Performance Debugging

#### Profile Test Performance

```python
import cProfile
import pstats

def profile_test_performance():
    """Profile test performance."""
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Run test operation
    perform_test_operation()
    
    profiler.disable()
    
    # Analyze results
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Top 10 time consumers
```

#### Memory Profiling

```python
import tracemalloc

def profile_memory_usage():
    """Profile memory usage during test."""
    tracemalloc.start()
    
    # Run test operation
    perform_test_operation()
    
    # Get memory snapshot
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    
    print("Top 10 memory consumers:")
    for stat in top_stats[:10]:
        print(f"{stat.traceback.format()}: {stat.size / 1024 / 1024:.1f} MB")
```

## Error Recovery Strategies

### 1. Test Retry Logic

```python
import pytest
import time

def retry_test(max_retries=3, delay=1):
    """Decorator to retry flaky tests."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    print(f"Test failed (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(delay)
        return wrapper
    return decorator

@retry_test(max_retries=3, delay=2)
def test_flaky_operation():
    # Test that might fail due to timing issues
    pass
```

### 2. Graceful Failure Handling

```python
def test_with_graceful_failure():
    """Test with graceful failure handling."""
    try:
        result = risky_operation()
        assert result is not None
    except SpecificException as e:
        # Handle known failure modes
        pytest.skip(f"Skipping due to known issue: {e}")
    except Exception as e:
        # Log unexpected failures
        logger.error(f"Unexpected failure: {e}")
        raise
```

### 3. Test Cleanup

```python
@pytest.fixture
def cleanup_test_data():
    """Ensure test data is cleaned up."""
    test_data = []
    
    yield test_data
    
    # Cleanup after test
    for item in test_data:
        try:
            cleanup_item(item)
        except Exception as e:
            logger.warning(f"Failed to cleanup {item}: {e}")
```

## Getting Help

### 1. Test Output Analysis

When tests fail, analyze the output systematically:

1. **Check the error message** - Look for specific error types
2. **Review the stack trace** - Identify where the failure occurred
3. **Check test setup** - Verify fixtures and mocks are correct
4. **Examine test data** - Ensure test data is valid
5. **Review environment** - Check for configuration issues

### 2. Debug Information Collection

Collect debug information for complex issues:

```python
def collect_debug_info():
    """Collect debug information for troubleshooting."""
    import sys
    import platform
    
    debug_info = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "environment_variables": {
            key: value for key, value in os.environ.items()
            if key.startswith("DEVOPS_AGENT")
        },
        "installed_packages": get_installed_packages(),
        "test_configuration": get_test_configuration()
    }
    
    return debug_info
```

### 3. Support Resources

- **Documentation**: Check the [Integration Testing Guide](integration-testing.md)
- **Test Patterns**: Review the [Test Patterns Guide](test-patterns.md)
- **Performance**: See the [Performance Testing Guide](performance-testing.md)
- **Logs**: Check test logs in `test_reports/`
- **Community**: Reach out to the development team

## Prevention Strategies

### 1. Proactive Testing

- Run tests frequently during development
- Use continuous integration to catch issues early
- Implement performance monitoring
- Review test coverage regularly

### 2. Test Maintenance

- Keep tests up-to-date with system changes
- Review and update mocks regularly
- Monitor test execution times
- Clean up obsolete tests

### 3. Documentation

- Document test-specific setup requirements
- Maintain troubleshooting notes
- Share knowledge with team members
- Update documentation when resolving issues

## Quick Reference

### Common Commands

```bash
# Run all integration tests
./tests/integration/run_integration_tests.py

# Run with verbose output
./tests/integration/run_integration_tests.py --verbose

# Run specific test suite
./tests/integration/run_integration_tests.py --suite "Foundation"

# Run with debugging
uv run pytest tests/integration/test_file.py::test_name -v --pdb

# Check environment
uv run python -c "import sys; print(sys.path)"
pip list | grep -E "(pytest|asyncio|mock)"
```

### Environment Variables

```bash
export DEVOPS_AGENT_TESTING=true
export DEVOPS_AGENT_LOG_LEVEL=DEBUG
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Quick Fixes

1. **Import errors**: Check PYTHONPATH and __init__.py files
2. **Mock issues**: Use AsyncMock for async functions
3. **Test isolation**: Use function-scoped fixtures
4. **Performance issues**: Use relative thresholds
5. **Environment issues**: Use virtual environments

Remember: When in doubt, start with the simplest solution and work your way up to more complex debugging techniques. 