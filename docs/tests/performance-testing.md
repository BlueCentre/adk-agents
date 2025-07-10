---
title: Performance Testing Guide
layout: default
nav_order: 3
parent: Testing
---

# Performance Testing Guide

This guide covers performance testing patterns, metrics, monitoring, and optimization strategies used in the ADK Agents integration test suite.

## Overview

Performance testing in the ADK Agents system focuses on:

- **Context Assembly Performance** - Efficient context generation with token optimization
- **Tool Orchestration Speed** - Parallel vs sequential execution performance
- **Memory Management** - Leak detection and resource optimization
- **Load Testing** - Concurrent user simulation and scalability
- **Token Optimization** - Efficient token counting and management
- **Cross-turn Correlation** - Performance of conversation relationship detection

## Performance Testing Architecture

### Core Performance Metrics

#### Primary Metrics

1. **Execution Time** - Total time for operation completion
2. **Memory Usage** - Peak and average memory consumption
3. **CPU Usage** - Processor utilization during operations
4. **Throughput** - Operations per second
5. **Token Processing Speed** - Tokens processed per second
6. **Context Assembly Time** - Time to assemble context from components

#### Secondary Metrics

1. **Response Time Distribution** - P50, P95, P99 percentiles
2. **Error Rate** - Percentage of failed operations
3. **Resource Utilization** - System resource efficiency
4. **Concurrent User Capacity** - Maximum supported concurrent users
5. **Memory Leak Detection** - Memory growth over time
6. **Context Size Efficiency** - Token count vs content ratio

### Performance Test Categories

#### 1. Baseline Performance Tests

Tests that establish performance baselines for core operations.

```python
class TestBaselinePerformance:
    def test_context_assembly_performance(self, context_manager):
        """Test baseline context assembly performance."""
        # Arrange - Setup test data
        context_manager.add_code_snippet("test.py", "def test(): pass", 1, 10)
        context_manager.add_tool_result("test_tool", {"result": "success"})
        
        # Act - Measure performance
        start_time = time.time()
        context_dict, token_count = context_manager.assemble_context(10000)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Assert - Verify performance thresholds
        assert execution_time < 0.1  # 100ms threshold
        assert token_count > 0
        assert "conversation_history" in context_dict
```

#### 2. Load Testing

Tests that simulate realistic user loads and concurrent operations.

```python
class TestLoadPerformance:
    @pytest.mark.asyncio
    async def test_concurrent_context_assembly(self, context_manager):
        """Test context assembly under concurrent load."""
        concurrent_users = 10
        operations_per_user = 100
        
        async def simulate_user_operations(user_id):
            results = []
            for i in range(operations_per_user):
                start_time = time.time()
                context_dict, token_count = context_manager.assemble_context(5000)
                end_time = time.time()
                
                results.append({
                    "user_id": user_id,
                    "operation": i,
                    "execution_time": end_time - start_time,
                    "token_count": token_count
                })
            return results
        
        # Execute concurrent operations
        tasks = [simulate_user_operations(i) for i in range(concurrent_users)]
        all_results = await asyncio.gather(*tasks)
        
        # Analyze performance
        flat_results = [r for results in all_results for r in results]
        avg_execution_time = sum(r["execution_time"] for r in flat_results) / len(flat_results)
        
        assert avg_execution_time < 0.2  # 200ms average under load
```

#### 3. Stress Testing

Tests that push the system beyond normal operating conditions.

```python
class TestStressPerformance:
    @pytest.mark.asyncio
    async def test_extreme_load_handling(self, context_manager):
        """Test system behavior under extreme load."""
        # Extreme parameters
        concurrent_users = 50
        operations_per_user = 200
        large_context_size = 50000
        
        # Monitor system resources
        resource_monitor = ResourceMonitor()
        resource_monitor.start_monitoring()
        
        async def stress_operations(user_id):
            for i in range(operations_per_user):
                try:
                    context_dict, token_count = context_manager.assemble_context(large_context_size)
                    await asyncio.sleep(0.001)  # Minimal delay
                except Exception as e:
                    # Log but don't fail - expect some degradation
                    print(f"User {user_id} operation {i} failed: {e}")
        
        # Execute stress test
        tasks = [stress_operations(i) for i in range(concurrent_users)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        metrics = resource_monitor.stop_monitoring()
        
        # Verify system didn't crash and resources are reasonable
        assert metrics.peak_memory_mb < 2000  # 2GB limit
        assert metrics.peak_cpu_percent < 95  # 95% CPU limit
```

#### 4. Memory Performance Tests

Tests that focus on memory usage patterns and leak detection.

```python
class TestMemoryPerformance:
    def test_memory_leak_detection(self, context_manager):
        """Test for memory leaks in context management."""
        import gc
        import tracemalloc
        
        tracemalloc.start()
        
        # Baseline memory
        gc.collect()
        baseline_snapshot = tracemalloc.take_snapshot()
        
        # Execute many operations
        for i in range(1000):
            context_manager.add_code_snippet(f"test_{i}.py", f"def test_{i}(): pass", 1, 10)
            context_dict, token_count = context_manager.assemble_context(10000)
            
            # Clear context periodically
            if i % 100 == 0:
                context_manager.clear_context()
        
        # Final memory measurement
        gc.collect()
        final_snapshot = tracemalloc.take_snapshot()
        
        # Calculate memory growth
        top_stats = final_snapshot.compare_to(baseline_snapshot, 'lineno')
        total_memory_growth = sum(stat.size_diff for stat in top_stats if stat.size_diff > 0)
        
        # Assert reasonable memory growth (< 50MB)
        assert total_memory_growth < 50 * 1024 * 1024  # 50MB limit
```

## Performance Monitoring Infrastructure

### Resource Monitor Implementation

```python
class ResourceMonitor:
    """Monitor system resources during test execution."""
    
    def __init__(self):
        self.monitoring = False
        self.start_time = None
        self.metrics = {
            "memory_usage": [],
            "cpu_usage": [],
            "operations": [],
            "timestamps": []
        }
    
    def start_monitoring(self):
        """Start resource monitoring."""
        self.monitoring = True
        self.start_time = time.time()
        
        # Start background monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_resources)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring and return metrics."""
        self.monitoring = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=1.0)
        
        return PerformanceMetrics(
            execution_time=time.time() - self.start_time,
            peak_memory_mb=max(self.metrics["memory_usage"]) if self.metrics["memory_usage"] else 0,
            avg_memory_mb=sum(self.metrics["memory_usage"]) / len(self.metrics["memory_usage"]) if self.metrics["memory_usage"] else 0,
            peak_cpu_percent=max(self.metrics["cpu_usage"]) if self.metrics["cpu_usage"] else 0,
            avg_cpu_percent=sum(self.metrics["cpu_usage"]) / len(self.metrics["cpu_usage"]) if self.metrics["cpu_usage"] else 0,
            total_operations=len(self.metrics["operations"]),
            operations_per_second=len(self.metrics["operations"]) / (time.time() - self.start_time) if self.start_time else 0
        )
    
    def record_operation(self, operation_type="generic", success=True):
        """Record an operation for metrics."""
        self.metrics["operations"].append({
            "type": operation_type,
            "success": success,
            "timestamp": time.time()
        })
    
    def _monitor_resources(self):
        """Background resource monitoring."""
        import psutil
        
        while self.monitoring:
            try:
                # Get current process
                process = psutil.Process()
                
                # Record memory usage (MB)
                memory_mb = process.memory_info().rss / 1024 / 1024
                self.metrics["memory_usage"].append(memory_mb)
                
                # Record CPU usage (%)
                cpu_percent = process.cpu_percent()
                self.metrics["cpu_usage"].append(cpu_percent)
                
                # Record timestamp
                self.metrics["timestamps"].append(time.time())
                
                time.sleep(0.1)  # Sample every 100ms
                
            except Exception as e:
                print(f"Resource monitoring error: {e}")
                break
```

### Performance Metrics Data Structure

```python
@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    execution_time: float
    peak_memory_mb: float
    avg_memory_mb: float
    peak_cpu_percent: float
    avg_cpu_percent: float
    total_operations: int
    operations_per_second: float
    
    def to_dict(self):
        """Convert metrics to dictionary for reporting."""
        return {
            "execution_time": self.execution_time,
            "peak_memory_mb": self.peak_memory_mb,
            "avg_memory_mb": self.avg_memory_mb,
            "peak_cpu_percent": self.peak_cpu_percent,
            "avg_cpu_percent": self.avg_cpu_percent,
            "total_operations": self.total_operations,
            "operations_per_second": self.operations_per_second
        }
    
    def meets_thresholds(self, thresholds):
        """Check if metrics meet performance thresholds."""
        return (
            self.execution_time <= thresholds.get("max_execution_time", float('inf')) and
            self.peak_memory_mb <= thresholds.get("max_memory_mb", float('inf')) and
            self.operations_per_second >= thresholds.get("min_operations_per_second", 0) and
            self.peak_cpu_percent <= thresholds.get("max_cpu_percent", 100)
        )
```

## Performance Test Patterns

### 1. Benchmark Comparison Pattern

Compare performance between different implementations or configurations.

```python
class TestPerformanceComparison:
    def test_parallel_vs_sequential_execution(self, tool_orchestrator):
        """Compare parallel vs sequential tool execution performance."""
        tools = [
            ("read_file", {"file_path": f"test_{i}.py"}),
            ("analyze_code", {"file_path": f"test_{i}.py"}),
            ("generate_tests", {"file_path": f"test_{i}.py"})
            for i in range(10)
        ]
        
        # Test sequential execution
        start_time = time.time()
        sequential_results = []
        for tool_name, args in tools:
            result = tool_orchestrator.execute_tool_sync(tool_name, args)
            sequential_results.append(result)
        sequential_time = time.time() - start_time
        
        # Test parallel execution
        start_time = time.time()
        parallel_results = tool_orchestrator.execute_tools_parallel(tools)
        parallel_time = time.time() - start_time
        
        # Assert performance improvement
        assert parallel_time < sequential_time * 0.8  # At least 20% improvement
        assert len(parallel_results) == len(sequential_results)
        
        # Log performance comparison
        speedup = sequential_time / parallel_time
        print(f"Parallel execution {speedup:.2f}x faster than sequential")
```

### 2. Scalability Testing Pattern

Test how performance scales with increasing load.

```python
class TestScalabilityPerformance:
    @pytest.mark.parametrize("user_count", [1, 5, 10, 25, 50])
    def test_scalability_with_user_count(self, user_count, context_manager):
        """Test how performance scales with increasing user count."""
        operations_per_user = 100
        
        # Monitor performance
        resource_monitor = ResourceMonitor()
        resource_monitor.start_monitoring()
        
        async def simulate_user_load(user_id):
            for i in range(operations_per_user):
                context_dict, token_count = context_manager.assemble_context(5000)
                await asyncio.sleep(0.01)  # Realistic user delay
        
        # Execute load test
        start_time = time.time()
        tasks = [simulate_user_load(i) for i in range(user_count)]
        await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        metrics = resource_monitor.stop_monitoring()
        
        # Calculate scalability metrics
        throughput = (user_count * operations_per_user) / total_time
        
        # Assert reasonable scalability
        expected_min_throughput = max(50, 500 / user_count)  # Adjust expectations
        assert throughput >= expected_min_throughput
        
        # Log scalability data
        print(f"Users: {user_count}, Throughput: {throughput:.2f} ops/sec, "
              f"Memory: {metrics.peak_memory_mb:.1f} MB")
```

### 3. Optimization Validation Pattern

Validate that optimizations improve performance without affecting functionality.

```python
class TestOptimizationValidation:
    def test_token_counting_optimization(self, context_manager):
        """Test that token counting optimization improves performance."""
        # Test data
        large_content = "def test_function():\n    pass\n" * 1000
        
        # Test without optimization
        context_manager.disable_token_counting_optimization()
        start_time = time.time()
        for i in range(100):
            context_manager.add_code_snippet(f"test_{i}.py", large_content, 1, 1000)
            context_dict, token_count = context_manager.assemble_context(50000)
        unoptimized_time = time.time() - start_time
        
        # Clear and test with optimization
        context_manager.clear_context()
        context_manager.enable_token_counting_optimization()
        start_time = time.time()
        for i in range(100):
            context_manager.add_code_snippet(f"test_{i}.py", large_content, 1, 1000)
            context_dict, token_count = context_manager.assemble_context(50000)
        optimized_time = time.time() - start_time
        
        # Assert optimization improves performance
        improvement = (unoptimized_time - optimized_time) / unoptimized_time
        assert improvement > 0.2  # At least 20% improvement
        
        print(f"Token counting optimization: {improvement:.1%} improvement")
```

### 4. Regression Testing Pattern

Detect performance regressions by comparing against baseline metrics.

```python
class TestPerformanceRegression:
    def test_context_assembly_regression(self, context_manager):
        """Test for performance regression in context assembly."""
        # Load baseline metrics
        baseline_metrics = self.load_baseline_metrics("context_assembly")
        
        # Execute current performance test
        resource_monitor = ResourceMonitor()
        resource_monitor.start_monitoring()
        
        # Perform standardized operations
        for i in range(100):
            context_manager.add_code_snippet(f"test_{i}.py", f"def test_{i}(): pass", 1, 10)
            context_dict, token_count = context_manager.assemble_context(10000)
        
        current_metrics = resource_monitor.stop_monitoring()
        
        # Compare against baseline (allow 10% degradation)
        assert current_metrics.execution_time <= baseline_metrics["execution_time"] * 1.1
        assert current_metrics.peak_memory_mb <= baseline_metrics["peak_memory_mb"] * 1.1
        assert current_metrics.operations_per_second >= baseline_metrics["operations_per_second"] * 0.9
        
        # Update baseline if significantly improved
        if current_metrics.execution_time < baseline_metrics["execution_time"] * 0.9:
            self.update_baseline_metrics("context_assembly", current_metrics.to_dict())
    
    def load_baseline_metrics(self, test_name):
        """Load baseline metrics from file."""
        baseline_file = f"test_reports/baseline_{test_name}.json"
        if os.path.exists(baseline_file):
            with open(baseline_file, 'r') as f:
                return json.load(f)
        else:
            # Return permissive defaults if no baseline exists
            return {
                "execution_time": 10.0,
                "peak_memory_mb": 1000.0,
                "operations_per_second": 1.0
            }
    
    def update_baseline_metrics(self, test_name, metrics):
        """Update baseline metrics file."""
        baseline_file = f"test_reports/baseline_{test_name}.json"
        os.makedirs(os.path.dirname(baseline_file), exist_ok=True)
        with open(baseline_file, 'w') as f:
            json.dump(metrics, f, indent=2)
```

## Performance Thresholds and SLAs

### Standard Performance Thresholds

```python
PERFORMANCE_THRESHOLDS = {
    "context_assembly": {
        "max_execution_time": 0.5,  # 500ms
        "max_memory_mb": 500,       # 500MB
        "min_operations_per_second": 100,
        "max_cpu_percent": 80
    },
    "tool_orchestration": {
        "max_execution_time": 2.0,  # 2 seconds
        "max_memory_mb": 1000,      # 1GB
        "min_operations_per_second": 50,
        "max_cpu_percent": 90
    },
    "load_testing": {
        "max_execution_time": 10.0, # 10 seconds
        "max_memory_mb": 2000,      # 2GB
        "min_operations_per_second": 200,
        "max_cpu_percent": 95
    }
}
```

### Performance SLA Validation

```python
def validate_performance_sla(metrics, test_category):
    """Validate performance metrics against SLA thresholds."""
    thresholds = PERFORMANCE_THRESHOLDS.get(test_category, {})
    
    violations = []
    
    if "max_execution_time" in thresholds:
        if metrics.execution_time > thresholds["max_execution_time"]:
            violations.append(f"Execution time {metrics.execution_time:.2f}s exceeds limit {thresholds['max_execution_time']:.2f}s")
    
    if "max_memory_mb" in thresholds:
        if metrics.peak_memory_mb > thresholds["max_memory_mb"]:
            violations.append(f"Memory usage {metrics.peak_memory_mb:.1f}MB exceeds limit {thresholds['max_memory_mb']:.1f}MB")
    
    if "min_operations_per_second" in thresholds:
        if metrics.operations_per_second < thresholds["min_operations_per_second"]:
            violations.append(f"Throughput {metrics.operations_per_second:.1f} ops/sec below minimum {thresholds['min_operations_per_second']}")
    
    if "max_cpu_percent" in thresholds:
        if metrics.peak_cpu_percent > thresholds["max_cpu_percent"]:
            violations.append(f"CPU usage {metrics.peak_cpu_percent:.1f}% exceeds limit {thresholds['max_cpu_percent']:.1f}%")
    
    return violations
```

## Performance Optimization Strategies

### 1. Context Assembly Optimization

```python
class OptimizedContextManager:
    """Context manager with performance optimizations."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token_cache = {}
        self.content_cache = {}
        self.optimization_enabled = True
    
    def assemble_context(self, token_limit):
        """Optimized context assembly with caching."""
        if not self.optimization_enabled:
            return super().assemble_context(token_limit)
        
        # Use cached results when possible
        cache_key = self._generate_cache_key(token_limit)
        if cache_key in self.content_cache:
            return self.content_cache[cache_key]
        
        # Perform optimized assembly
        context_dict = {}
        current_tokens = 0
        
        # Prioritize content efficiently
        prioritized_content = self._get_prioritized_content()
        
        for content in prioritized_content:
            content_tokens = self._get_cached_token_count(content)
            if current_tokens + content_tokens <= token_limit:
                context_dict[content["type"]] = content["data"]
                current_tokens += content_tokens
            else:
                break
        
        # Cache result
        result = (context_dict, current_tokens)
        self.content_cache[cache_key] = result
        
        return result
    
    def _get_cached_token_count(self, content):
        """Get token count with caching."""
        content_hash = hash(str(content))
        if content_hash not in self.token_cache:
            self.token_cache[content_hash] = self._count_tokens(content)
        return self.token_cache[content_hash]
```

### 2. Parallel Processing Optimization

```python
class ParallelToolOrchestrator:
    """Tool orchestrator with parallel processing optimization."""
    
    async def execute_tools_optimized(self, tools, max_concurrency=10):
        """Execute tools with optimized parallelism."""
        # Group tools by dependency level
        dependency_groups = self._group_by_dependencies(tools)
        
        results = {}
        
        # Execute each dependency level
        for level, tool_group in dependency_groups.items():
            # Limit concurrency to prevent resource exhaustion
            semaphore = asyncio.Semaphore(max_concurrency)
            
            async def execute_with_semaphore(tool):
                async with semaphore:
                    return await self._execute_single_tool(tool, results)
            
            # Execute tools in parallel within dependency level
            level_results = await asyncio.gather(
                *[execute_with_semaphore(tool) for tool in tool_group],
                return_exceptions=True
            )
            
            # Update results
            for tool, result in zip(tool_group, level_results):
                if isinstance(result, Exception):
                    results[tool["id"]] = {"error": str(result)}
                else:
                    results[tool["id"]] = result
        
        return results
```

### 3. Memory Optimization

```python
class MemoryOptimizedContextManager:
    """Context manager with memory optimization."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.memory_threshold_mb = 1000
        self.cleanup_interval = 100
        self.operation_count = 0
    
    def add_content(self, content_type, content_data):
        """Add content with memory management."""
        super().add_content(content_type, content_data)
        
        self.operation_count += 1
        
        # Periodic memory cleanup
        if self.operation_count % self.cleanup_interval == 0:
            self._cleanup_memory()
    
    def _cleanup_memory(self):
        """Cleanup memory by removing old or low-priority content."""
        import gc
        import psutil
        
        # Check current memory usage
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        if memory_mb > self.memory_threshold_mb:
            # Remove old content
            self._remove_old_content()
            
            # Remove low-priority content
            self._remove_low_priority_content()
            
            # Force garbage collection
            gc.collect()
    
    def _remove_old_content(self):
        """Remove content older than threshold."""
        cutoff_time = time.time() - 3600  # 1 hour
        
        for content_type in list(self.content_store.keys()):
            self.content_store[content_type] = [
                item for item in self.content_store[content_type]
                if item.get("timestamp", 0) > cutoff_time
            ]
    
    def _remove_low_priority_content(self):
        """Remove content with low priority scores."""
        for content_type in list(self.content_store.keys()):
            if len(self.content_store[content_type]) > 100:
                # Keep only top 100 priority items
                self.content_store[content_type] = sorted(
                    self.content_store[content_type],
                    key=lambda x: x.get("priority_score", 0),
                    reverse=True
                )[:100]
```

## Performance Reporting and Analysis

### Performance Report Generation

```python
class PerformanceReportGenerator:
    """Generate comprehensive performance reports."""
    
    def generate_report(self, test_results, output_file="performance_report.html"):
        """Generate HTML performance report."""
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "test_results": test_results,
            "summary": self._generate_summary(test_results),
            "recommendations": self._generate_recommendations(test_results)
        }
        
        html_content = self._generate_html_report(report_data)
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        return output_file
    
    def _generate_summary(self, test_results):
        """Generate performance summary."""
        total_tests = len(test_results)
        passed_tests = sum(1 for r in test_results if r["status"] == "passed")
        
        avg_execution_time = sum(r["metrics"]["execution_time"] for r in test_results) / total_tests
        avg_memory_usage = sum(r["metrics"]["peak_memory_mb"] for r in test_results) / total_tests
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": passed_tests / total_tests * 100,
            "avg_execution_time": avg_execution_time,
            "avg_memory_usage": avg_memory_usage
        }
    
    def _generate_recommendations(self, test_results):
        """Generate performance optimization recommendations."""
        recommendations = []
        
        # Check for slow tests
        slow_tests = [r for r in test_results if r["metrics"]["execution_time"] > 5.0]
        if slow_tests:
            recommendations.append({
                "type": "performance",
                "priority": "high",
                "message": f"Found {len(slow_tests)} slow tests (>5s). Consider optimization.",
                "affected_tests": [t["name"] for t in slow_tests]
            })
        
        # Check for memory issues
        memory_heavy_tests = [r for r in test_results if r["metrics"]["peak_memory_mb"] > 1000]
        if memory_heavy_tests:
            recommendations.append({
                "type": "memory",
                "priority": "medium",
                "message": f"Found {len(memory_heavy_tests)} memory-heavy tests (>1GB). Review memory usage.",
                "affected_tests": [t["name"] for t in memory_heavy_tests]
            })
        
        return recommendations
```

## Best Practices for Performance Testing

### 1. Test Environment Consistency

- Use dedicated test environments for performance testing
- Control for external factors (network, disk, CPU load)
- Use consistent hardware specifications
- Monitor and account for system background processes

### 2. Baseline Management

- Establish performance baselines for critical operations
- Update baselines when legitimate improvements are made
- Track performance trends over time
- Alert on significant regressions

### 3. Test Data Management

- Use realistic test data that matches production patterns
- Ensure consistent test data across test runs
- Include edge cases and boundary conditions
- Scale test data appropriately for load testing

### 4. Measurement Accuracy

- Use appropriate measurement granularity
- Account for warmup time and JIT compilation
- Run multiple iterations and use statistical measures
- Isolate performance measurements from test setup

### 5. Performance Monitoring

- Monitor multiple metrics simultaneously
- Use percentile-based measurements (P95, P99)
- Track resource utilization patterns
- Identify performance bottlenecks systematically

## Integration with CI/CD

### Performance Gate Configuration

```yaml
performance_gates:
  context_assembly:
    max_execution_time: 0.5
    max_memory_mb: 500
    min_throughput_ops_per_sec: 100
  
  tool_orchestration:
    max_execution_time: 2.0
    max_memory_mb: 1000
    min_throughput_ops_per_sec: 50
  
  load_testing:
    max_execution_time: 10.0
    max_memory_mb: 2000
    min_throughput_ops_per_sec: 200
```

### Automated Performance Testing

```yaml
name: Performance Testing
on:
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  performance-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          uv sync --dev
      
      - name: Run performance tests
        run: |
          ./tests/integration/run_integration_tests.py --suite "Performance" --parallel
      
      - name: Check performance gates
        run: |
          uv run python scripts/check_performance_gates.py test_reports/integration_test_report_latest.json
      
      - name: Generate performance report
        run: |
          uv run python scripts/generate_performance_report.py
      
      - name: Upload performance report
        uses: actions/upload-artifact@v3
        with:
          name: performance-report
          path: test_reports/performance_report.html
```

## Conclusion

Performance testing is critical for ensuring the ADK Agents system maintains acceptable performance characteristics under various conditions. By implementing comprehensive performance testing patterns, monitoring infrastructure, and optimization strategies, you can:

- Detect performance regressions early
- Validate optimization efforts
- Ensure system scalability
- Maintain performance SLAs
- Provide data-driven insights for system improvements

Remember to:
- Establish baseline performance metrics
- Test under realistic conditions
- Monitor multiple performance dimensions
- Automate performance testing in CI/CD
- Optimize based on actual performance data

For general testing patterns, see the [Test Patterns Guide](test-patterns.md).

For troubleshooting performance issues, see the [Troubleshooting Guide](troubleshooting.md). 