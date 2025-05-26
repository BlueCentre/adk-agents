# DevOps Agent Telemetry Configuration

This document explains how to configure and manage the DevOps Agent's telemetry system, including solutions for Grafana Cloud rate limiting.

## Overview

The DevOps Agent includes comprehensive telemetry capabilities:
- **OpenLIT Integration**: Automatic LLM observability
- **Custom OpenTelemetry Metrics**: Agent-specific performance tracking
- **Grafana Cloud Export**: Production-ready metrics export
- **Local Development Tools**: Rich dashboard for development

## Environment Variables

### Core Configuration

#### `GRAFANA_OTLP_ENDPOINT`
- **Purpose**: Grafana Cloud OTLP endpoint URL
- **Example**: `https://otlp-gateway-prod-us-central-0.grafana.net/otlp`
- **Required**: For Grafana Cloud export

#### `GRAFANA_OTLP_TOKEN`
- **Purpose**: Grafana Cloud authentication token (base64 encoded)
- **Format**: Base64 encoded `instanceID:token`
- **Required**: For Grafana Cloud export

### OpenLIT Configuration

#### `OPENLIT_ENVIRONMENT`
- **Default**: `Production`
- **Purpose**: Environment name for OpenLIT metrics
- **Values**: `Production`, `Development`, `Staging`, etc.

#### `OPENLIT_COLLECT_GPU_STATS`
- **Default**: `false`
- **Purpose**: Enable GPU monitoring if GPU is available
- **Values**: `true`, `false`, `1`, `0`, `yes`, `no`
- **Note**: Requires GPU and nvidia-ml-py package. Disabled by default to avoid warnings on non-GPU systems.

#### `OPENLIT_DISABLE_METRICS`
- **Default**: `false`
- **Purpose**: Completely disable OpenLIT metrics collection
- **Values**: `true`, `false`, `1`, `0`, `yes`, `no`
- **Use Case**: When you only want custom agent metrics

### Rate Limiting Controls

#### `GRAFANA_EXPORT_INTERVAL_SECONDS`
- **Default**: `120` (2 minutes)
- **Purpose**: How often to export metrics to Grafana Cloud
- **Recommendation**: Increase if hitting rate limits
- **Example**: `export GRAFANA_EXPORT_INTERVAL_SECONDS=300` (5 minutes)

#### `GRAFANA_EXPORT_TIMEOUT_SECONDS`
- **Default**: `30`
- **Purpose**: Timeout for export requests
- **Range**: 10-60 seconds

#### `DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT`
- **Default**: `false`
- **Purpose**: Completely disable telemetry export (local metrics only)
- **Values**: `true`, `false`, `1`, `0`, `yes`, `no`
- **Use Case**: Development, testing, or when hitting rate limits

### Tracing Configuration

#### `OPENLIT_CAPTURE_CONTENT`
- **Default**: `true`
- **Purpose**: Capture LLM prompts and completions in traces
- **Values**: `true`, `false`, `1`, `0`, `yes`, `no`
- **Privacy**: Set to `false` for sensitive data environments

#### `OPENLIT_DISABLE_BATCH`
- **Default**: `false`
- **Purpose**: Disable batch processing of traces (useful for local development)
- **Values**: `true`, `false`, `1`, `0`, `yes`, `no`
- **Use Case**: Local debugging when you want immediate trace export

#### `OPENLIT_DISABLED_INSTRUMENTORS`
- **Default**: `` (empty)
- **Purpose**: Disable specific auto-instrumentation
- **Format**: Comma-separated list
- **Example**: `anthropic,langchain` to disable those instrumentors

#### `TRACE_SAMPLING_RATE`
- **Default**: `1.0`
- **Purpose**: Control what percentage of operations to trace
- **Range**: `0.0` to `1.0`
- **Example**: `0.1` for 10% sampling in high-traffic environments

#### `SERVICE_INSTANCE_ID`
- **Default**: `devops-agent-{pid}`
- **Purpose**: Unique identifier for this agent instance
- **Use Case**: Distinguish between multiple agent instances

#### `SERVICE_VERSION`
- **Default**: `1.0.0`
- **Purpose**: Version identifier for traces
- **Use Case**: Track performance across different agent versions

## Rate Limiting Solutions

### Problem: Grafana Cloud 429 Errors

If you see errors like:
```
Failed to export batch code: 429, reason: the request has been rejected because the tenant exceeded the request rate limit
```

### Solution 1: Increase Export Interval

```bash
# Export every 5 minutes instead of 2 minutes
export GRAFANA_EXPORT_INTERVAL_SECONDS=300
./run.sh
```

### Solution 2: Disable Export for Development

```bash
# Disable Grafana Cloud export entirely
export DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT=true
./run.sh
```

### Solution 3: Remove Credentials Temporarily

```bash
# Unset Grafana Cloud credentials
unset GRAFANA_OTLP_ENDPOINT
unset GRAFANA_OTLP_TOKEN
./run.sh
```

## Metric Types

The agent exports these metric types to Grafana Cloud:

### OpenLIT Auto-Instrumentation Metrics

**LLM/GenAI Metrics:**
- `gen_ai.total.requests`: Number of LLM requests
- `gen_ai.usage.input_tokens`: Input tokens processed
- `gen_ai.usage.output_tokens`: Output tokens processed  
- `gen_ai.usage.total_tokens`: Total tokens processed
- `gen_ai.usage.cost`: Cost distribution of LLM requests

**VectorDB Metrics:**
- `db.total.requests`: Number of VectorDB requests (ChromaDB)

**GPU Metrics (if enabled):**
- `gpu.utilization`: GPU utilization percentage
- `gpu.memory.used/available/total/free`: GPU memory metrics
- `gpu.temperature`: GPU temperature in Celsius
- `gpu.power.draw/limit`: GPU power metrics
- `gpu.fan_speed`: GPU fan speed

### Custom Agent Metrics

**Counters:**
- `devops_agent_operations_total`: Total operations by type and status
- `devops_agent_errors_total`: Total errors by operation and error type  
- `devops_agent_tokens_total`: Total tokens consumed by model and type
- `devops_agent_tool_usage_total`: Total tool executions by tool type
- `devops_agent_context_operations_total`: Total context management operations

**Histograms:**
- `devops_agent_operation_duration_seconds`: Operation execution times
- `devops_agent_llm_response_time_seconds`: LLM response times by model
- `devops_agent_context_size_tokens`: Context sizes in tokens
- `devops_agent_tool_execution_seconds`: Tool execution times
- `devops_agent_file_operation_bytes`: File operation sizes

**Gauges:**
- `devops_agent_active_tools`: Currently active tool executions
- `devops_agent_context_cache_items`: Number of items in context cache
- `devops_agent_memory_usage_mb`: Current memory usage
- `devops_agent_cpu_usage_percent`: Current CPU usage
- `devops_agent_disk_usage_mb`: Current disk usage
- `devops_agent_avg_response_time`: Rolling average response time

## Tracing Capabilities

The agent provides comprehensive distributed tracing through OpenLIT and custom instrumentation.

### OpenLIT Auto-Instrumentation Traces

**LLM Request Traces:**
- Complete request/response lifecycle
- Automatic span creation for each LLM call
- Token usage and cost tracking per request
- Model performance metrics
- Error context and exception details

**Trace Attributes (Semantic Conventions):**
- `gen_ai.system`: LLM provider (google, openai, anthropic)
- `gen_ai.request.model`: Model name (gemini-1.5-flash)
- `gen_ai.operation.name`: Operation type (chat, embedding)
- `gen_ai.request.temperature`: Model temperature
- `gen_ai.usage.input_tokens`: Prompt tokens
- `gen_ai.usage.output_tokens`: Completion tokens
- `gen_ai.usage.cost`: Request cost in USD

**VectorDB Traces:**
- ChromaDB operations (query, insert, update)
- Collection and index operations
- Query performance and result counts

### Custom Agent Traces

**Agent Lifecycle Traces:**
- User request processing
- Planning and execution phases
- Context management operations
- Tool orchestration

**Tool Execution Traces:**
- Individual tool performance
- Input/output size tracking
- Success/failure rates
- Error context and recovery

**Manual Tracing Examples:**

```python
# OpenLIT decorator tracing
@openlit.trace
def complex_operation():
    return process_data()

# OpenLIT context manager tracing
with openlit.start_trace("multi_step_process") as trace:
    result = step1()
    trace.set_metadata({"step1_result": len(result)})
    final = step2(result)
    trace.set_result(f"Processed {len(final)} items")

# Custom agent tracing
with trace_tool_execution("shell_command", command=cmd) as trace:
    result = execute_command(cmd)
    trace.set_metadata({
        "exit_code": result.exit_code,
        "output_size": len(result.stdout)
    })
```

### Trace Export and Analysis

**Export Destinations:**
- Grafana Cloud (production monitoring)
- Jaeger (distributed trace visualization)
- Zipkin (trace analysis)
- Local development (debugging)

**Analysis Capabilities:**
- End-to-end request flow visualization
- Performance bottleneck identification
- Error root cause analysis
- Cost optimization insights
- Capacity planning data

## Local Development

For local development without Grafana Cloud:

```bash
# Run telemetry dashboard
uvx --with "rich>=13.0.0" --with "psutil>=5.9.0" python scripts/telemetry_dashboard.py

# Check telemetry configuration
python scripts/telemetry_check.py
```

## Production Deployment

### Recommended Settings

```bash
# Production environment variables
export GRAFANA_OTLP_ENDPOINT="your-grafana-endpoint"
export GRAFANA_OTLP_TOKEN="your-base64-token"
export GRAFANA_EXPORT_INTERVAL_SECONDS=300  # 5 minutes
export GRAFANA_EXPORT_TIMEOUT_SECONDS=30
export DEVOPS_AGENT_INTERACTIVE=false       # Full logging
```

### Rate Limit Monitoring

Monitor your Grafana Cloud usage:
1. Check your Grafana Cloud metrics usage dashboard
2. Monitor for 429 errors in agent logs
3. Adjust export intervals based on usage patterns

## Troubleshooting

### High Rate Limit Usage

**Symptoms**: 429 errors, export failures
**Solutions**:
1. Increase `GRAFANA_EXPORT_INTERVAL_SECONDS` to 300-600 seconds
2. Temporarily disable export with `DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT=true`
3. Contact Grafana support to increase rate limits

### Missing Metrics

**Symptoms**: No data in Grafana Cloud
**Check**:
1. Verify `GRAFANA_OTLP_ENDPOINT` and `GRAFANA_OTLP_TOKEN` are set
2. Check agent logs for export errors
3. Verify network connectivity to Grafana Cloud

### Local Development Issues

**Symptoms**: Dashboard not working
**Solutions**:
1. Install dependencies: `pip install rich psutil`
2. Run from project root directory
3. Check that telemetry module is importable

## Best Practices

1. **Development**: Use `DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT=true`
2. **Testing**: Set longer export intervals (300+ seconds)
3. **Production**: Monitor rate limit usage and adjust intervals
4. **CI/CD**: Disable telemetry export in automated pipelines
5. **Debugging**: Use local telemetry dashboard for immediate feedback

## Integration Examples

### Docker Deployment
```dockerfile
ENV GRAFANA_OTLP_ENDPOINT=https://otlp-gateway-prod-us-central-0.grafana.net/otlp
ENV GRAFANA_OTLP_TOKEN=your-token-here
ENV GRAFANA_EXPORT_INTERVAL_SECONDS=300
ENV DEVOPS_AGENT_INTERACTIVE=false
```

### Kubernetes Deployment
```yaml
env:
- name: GRAFANA_OTLP_ENDPOINT
  valueFrom:
    secretKeyRef:
      name: grafana-credentials
      key: endpoint
- name: GRAFANA_OTLP_TOKEN
  valueFrom:
    secretKeyRef:
      name: grafana-credentials
      key: token
- name: GRAFANA_EXPORT_INTERVAL_SECONDS
  value: "300"
``` 