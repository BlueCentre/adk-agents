# DevOps Agent Telemetry & Observability Suite

A comprehensive observability system for the DevOps Agent that provides deep insights into performance, usage patterns, and system health through multiple layers of telemetry and monitoring.

## 🎯 Overview

The DevOps Agent telemetry suite combines:
- **OpenLIT Integration**: Production-ready LLM observability
- **Custom OpenTelemetry Metrics**: Detailed operation tracking
- **Tool Performance Analytics**: Comprehensive tool usage insights
- **Structured Logging**: Correlation-aware logging with trace integration
- **Real-time Dashboard**: Live monitoring with performance recommendations

## 🚀 Quick Start

### Production Monitoring with Grafana Cloud

Set up environment variables for automatic export to Grafana Cloud:

```bash
# Configure Grafana Cloud OTLP endpoint (required for production)
export GRAFANA_OTLP_ENDPOINT="https://otlp-gateway-prod-us-central-0.grafana.net/otlp"
export GRAFANA_OTLP_TOKEN="your-grafana-cloud-token"

# Run the agent - telemetry will automatically export to Grafana Cloud
./run.sh
```

### Development Dashboard (Local)

For local development when you need to view metrics without Grafana Cloud:

```bash
# View current telemetry summary
uv run scripts/telemetry_dashboard.py summary

# Export development metrics to JSON
uv run scripts/telemetry_dashboard.py export

# Check Grafana Cloud configuration status
uv run scripts/telemetry_dashboard.py grafana-check
```

## 📊 Telemetry Components

### 1. OpenLIT Integration (`agent.py`)

OpenLIT provides production-ready LLM observability with:

```python
import openlit
openlit.init(application_name="DevOps Agent", environment="Production")
```

**Features:**
- ✅ LLM request/response tracking
- ✅ Token usage and cost analysis
- ✅ Performance monitoring
- ✅ Exception tracking with context
- ✅ Custom metrics support

**Dashboard Access:** OpenLIT provides web dashboards for cost analysis and performance monitoring.

### 2. Enhanced Telemetry Module (`telemetry.py`)

Custom OpenTelemetry implementation with comprehensive metrics:

```python
from agents.devops.telemetry import telemetry, track_tool_execution, OperationType

# Track any operation
@telemetry.track_operation(OperationType.TOOL_EXECUTION, "my_tool")
def my_function():
    return "result"

# Or use convenience decorators
@track_tool_execution("filesystem_operation")
def file_operation():
    pass
```

**Metrics Collected:**
- 📈 **Counters**: Operations, errors, tokens
- ⏱️ **Histograms**: Duration, response times, context sizes  
- 📊 **Gauges**: Active tools, memory usage, average response times
- 🔍 **Traces**: Detailed operation spans with attributes

**Operation Types:**
- `TOOL_EXECUTION` - Tool usage tracking
- `LLM_REQUEST` - Language model interactions
- `CONTEXT_MANAGEMENT` - Context assembly operations
- `PLANNING` - Planning phase operations
- `FILE_OPERATION` - File system operations
- `SHELL_COMMAND` - Shell command executions
- `MEMORY_OPERATION` - Memory management
- `RAG_OPERATION` - Retrieval-augmented generation

### 3. Structured Logging (`logging_config.py`)

Correlation-aware logging with OpenTelemetry integration:

```python
from agents.devops.disabled.logging_config import log_tool_usage, log_performance_metrics, set_user_context

# Set user context for correlation
set_user_context("user123", "session456")

# Log tool usage with metrics
log_tool_usage(
    tool_name="execute_shell_command",
    input_size=100,
    output_size=500,
    duration=2.5,
    success=True,
    command="git status"
)

# Log performance metrics
log_performance_metrics(
    "context_assembly",
    duration=0.150,
    tokens_used=1500,
    memory_mb=45.2
)
```

**Features:**
- 🔗 **Correlation IDs**: Track requests across components
- 🕸️ **Trace Integration**: Automatic trace/span ID inclusion
- 📝 **Structured JSON**: Machine-readable log format
- 👤 **User Context**: Session and user tracking
- 🔧 **Operation Decorators**: Automatic start/end logging

### 4. Tool Performance Analytics (`tools/analytics.py`)

Comprehensive tool usage analysis and optimization:

```python
from agents.devops.tools.disabled.analytics import tool_analytics, track_tool_execution

# Automatic tool tracking decorator
@track_tool_execution("my_custom_tool")
def custom_tool(input_data):
    return process_data(input_data)

# Get performance report for specific tool
report = tool_analytics.get_tool_performance_report("execute_shell_command")
```

**Analytics Provided:**
- 📊 **Success Rates**: Tool reliability metrics
- ⏱️ **Performance Percentiles**: P95, P99 response times
- 📈 **Usage Trends**: 24-hour execution patterns
- 🔧 **Efficiency Scores**: Output/input ratios
- ❌ **Error Patterns**: Common failure types
- 💡 **Performance Recommendations**: Optimization suggestions

## 🎛️ Dashboard Features

The telemetry dashboard provides real-time monitoring with:

### Live Metrics
- Memory usage and trends
- Operation counts and error rates
- Average response times
- Token consumption

### Tool Analytics
- Tool execution counts
- Success rates with color coding
- Performance metrics
- Efficiency scores

### System Health
- Overall health scoring (0-100)
- Performance status indicators
- Automated concern detection
- Health trend analysis

### Performance Recommendations
- Automated optimization suggestions
- Error pattern analysis
- Performance bottleneck identification
- Tool-specific recommendations

## 🔧 Integration Examples

### Adding Telemetry to Custom Tools

```python
from agents.devops.telemetry import track_tool_execution
from agents.devops.tools.disabled.analytics import tool_analytics

@track_tool_execution("my_deployment_tool")
def deploy_application(config):
    start_time = time.time()
    try:
        # Deployment logic here
        result = perform_deployment(config)
        return result
    except Exception as e:
        # Errors are automatically tracked
        raise
    finally:
        # Analytics automatically recorded
        pass
```

### Custom Performance Monitoring

```python
from agents.devops.telemetry import telemetry, OperationType

@telemetry.track_operation(OperationType.PLANNING, "deployment_planning")
def plan_deployment(requirements):
    # Planning logic with automatic telemetry
    return create_plan(requirements)

# Manual metric recording
telemetry.track_llm_request(
    model="gemini-1.5-flash",
    tokens_used=1500,
    response_time=2.3,
    prompt_tokens=1000,
    completion_tokens=500
)
```

### Structured Logging with Context

```python
from agents.devops.disabled.logging_config import log_operation, log_business_event

@log_operation("infrastructure_provisioning", 
               resource_type="kubernetes", 
               environment="production")
def provision_infrastructure(specs):
    # Operations automatically logged with context
    return provision(specs)

# Business event logging
log_business_event("deployment_completed", {
    "application": "web-service",
    "version": "v1.2.3",
    "environment": "production",
    "duration_seconds": 120
})
```

## 📊 Metrics Collection

### OpenTelemetry Metrics

All metrics are exported via OpenTelemetry and can be consumed by:
- Prometheus
- Grafana
- Jaeger
- Custom OTEL collectors

**Key Metrics:**
```
devops_agent_operations_total{operation="tool_execution_shell_command", status="success"}
devops_agent_operation_duration_seconds{operation="llm_request_before_model"}
devops_agent_tokens_total{model="gemini-1.5-flash", type="prompt"}
devops_agent_memory_usage_mb{component="devops_agent"}
```

### Custom Analytics

Tool analytics are persisted locally and provide:
- Historical trend analysis
- Performance baseline comparisons
- Automated health assessments
- Recommendation generation

## 🔍 Performance Optimization

### Telemetry Overhead Assessment

The telemetry system is designed for minimal overhead:

```bash
# Benchmark telemetry performance
uv run python -m devops.telemetry_dashboard benchmark --iterations 10000
```

**Expected Results:**
- < 5% overhead: Excellent performance
- 5-10% overhead: Acceptable for observability benefits
- > 10% overhead: Consider optimization

### Optimization Strategies

1. **Reduce Metric Cardinality**: Limit high-cardinality labels
2. **Batch Operations**: Group related metrics
3. **Sampling**: Use sampling for high-volume operations
4. **Async Processing**: Process telemetry asynchronously

## 🔧 Configuration

### Environment Variables

```bash
# Enable detailed prompt logging (development only)
export LOG_FULL_PROMPTS=true

# Configure OpenLIT
export OPENLIT_APPLICATION_NAME="DevOps Agent"
export OPENLIT_ENVIRONMENT="Production"

# Telemetry configuration
export TELEMETRY_SAMPLE_RATE=1.0
export ANALYTICS_RETENTION_DAYS=30
```

### Custom Configuration

```python
# Configure telemetry instance
from agents.devops.telemetry import telemetry

# Adjust memory snapshot retention
telemetry.memory_snapshots = telemetry.memory_snapshots[-50:]  # Keep last 50

# Configure analytics retention
from agents.devops.tools.disabled.analytics import tool_analytics
tool_analytics.max_records = 5000  # Reduce memory usage
```

## 📈 Monitoring Best Practices

### 1. Regular Health Checks
```bash
# Daily health summary (development)
uv run scripts/telemetry_dashboard.py summary

# Weekly detailed report (development)
uv run scripts/telemetry_dashboard.py export --output weekly_$(date +%Y%m%d).json

# Production monitoring via Grafana Cloud dashboards
# (automatic when GRAFANA_OTLP_ENDPOINT is configured)
```

### 2. Performance Baselines
```python
# Set performance baselines for tools
tool_analytics.set_performance_baseline("execute_shell_command")
tool_analytics.set_performance_baseline("search_files")
```

### 3. Alert Thresholds

Monitor these key metrics:
- Error rate > 10%
- Average response time > 5 seconds
- Memory usage > 1GB
- Tool success rate < 80%

### 4. Trend Analysis

Track these trends over time:
- Token usage patterns
- Tool performance degradation
- Error pattern changes
- Memory leak indicators

## 🛠️ Troubleshooting

### Common Issues

**High Memory Usage:**
```python
# Check memory snapshots
summary = telemetry.get_performance_summary()
print(f"Memory: {summary['current_metrics']['memory_usage_mb']} MB")

# Reduce retention
telemetry.memory_snapshots = telemetry.memory_snapshots[-20:]
```

**Performance Degradation:**
```python
# Analyze tool performance
for tool_name, metrics in tool_analytics.tool_metrics.items():
    if metrics.p95_duration > 10.0:  # 10 second threshold
        print(f"Slow tool detected: {tool_name}")
        report = tool_analytics.get_tool_performance_report(tool_name)
        print(report['recommendations'])
```

**Missing Metrics:**
```python
# Verify telemetry initialization
from agents.devops.telemetry import telemetry
print(f"Operations tracked: {len(telemetry.operation_metrics)}")
print(f"Errors recorded: {len(telemetry.error_counts)}")
```

### Debug Mode

Enable detailed telemetry logging:
```python
import logging
logging.getLogger('devops.telemetry').setLevel(logging.DEBUG)
logging.getLogger('devops.tools.analytics').setLevel(logging.DEBUG)
```

## 🚀 Advanced Usage

### Custom Metric Creation

```python
from agents.devops.telemetry import telemetry

# Add custom counter
custom_counter = telemetry.meter.create_counter(
    name="custom_operations_total",
    description="Custom operation counter"
)

# Use in operations
custom_counter.add(1, {"operation": "custom_task", "status": "success"})
```

### Integration with External Systems

```python
# Export to Prometheus
from prometheus_client import start_http_server, Counter, Histogram

# Create Prometheus metrics
deployment_counter = Counter('deployments_total', 'Total deployments', ['status'])
deployment_duration = Histogram('deployment_duration_seconds', 'Deployment duration')

# Bridge telemetry data
def export_to_prometheus():
    summary = telemetry.get_performance_summary()
    # Export metrics to Prometheus format
```

### Custom Analytics

```python
# Create custom analytics
class CustomAnalytics:
    def __init__(self):
        self.metrics = {}
    
    def track_custom_event(self, event_type, data):
        # Custom tracking logic
        pass

# Integrate with existing system
from agents.devops.tools.disabled.analytics import tool_analytics
tool_analytics.custom_analytics = CustomAnalytics()
```

## 📚 Additional Resources

- [OpenLIT Documentation](https://docs.openlit.io/)
- [OpenTelemetry Python Guide](https://opentelemetry.io/docs/instrumentation/python/)
- [Rich Console Documentation](https://rich.readthedocs.io/)
- [Prometheus Metrics Best Practices](https://prometheus.io/docs/practices/naming/)

## 🤝 Contributing

To add new telemetry features:

1. **Add Metrics**: Extend `telemetry.py` with new operation types
2. **Update Analytics**: Add new analysis in `analytics.py`
3. **Enhance Dashboard**: Update `telemetry_dashboard.py` with new visualizations
4. **Document Changes**: Update this README with new features

---

*Built with ❤️ for comprehensive DevOps Agent observability* 