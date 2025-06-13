# DevOps Agent Observability Configuration

This document explains how to configure observability for the DevOps Agent and how to prevent messy telemetry output when it's not needed.

## Quick Fix for Messy Output

If you're seeing messy JSON telemetry output like this when running the agent:

```json
{
    "name": "llm_request_before_model",
    "context": {
        "trace_id": "0x34971b9eef7c31c5cce5aa58246b25df",
        ...
    }
}
```

**Solution: Observability is now disabled by default** for clean output. To enable observability when needed:

```bash
# Option 1: Enable full observability (for production/monitoring)
export DEVOPS_AGENT_OBSERVABILITY_ENABLE=true

# Option 2: Enable local metrics only (for debugging)
export DEVOPS_AGENT_ENABLE_LOCAL_METRICS=true

# Then run your agent
echo "hi" | uv run agent run agents.devops
```

## Environment Variables

### Observability Control

#### `DEVOPS_AGENT_OBSERVABILITY_ENABLE`
- **Default**: `false` (observability disabled by default)
- **Purpose**: Enable full observability (OpenLIT + OpenTelemetry)
- **Values**: `true`, `false`, `1`, `0`, `yes`, `no`
- **Use Case**: Production monitoring, comprehensive telemetry
- **Example**: `export DEVOPS_AGENT_OBSERVABILITY_ENABLE=true`

#### `DEVOPS_AGENT_ENABLE_LOCAL_METRICS`
- **Default**: `false`
- **Purpose**: Enable local metrics collection without export
- **Values**: `true`, `false`, `1`, `0`, `yes`, `no`
- **Use Case**: Collect metrics locally for debugging without external export
- **Example**: `export DEVOPS_AGENT_ENABLE_LOCAL_METRICS=true`

#### `DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT`
- **Default**: `false`
- **Purpose**: Disable external telemetry export (keep local collection)
- **Values**: `true`, `false`, `1`, `0`, `yes`, `no`
- **Use Case**: Prevent rate limiting while keeping basic telemetry
- **Example**: `export DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT=true`

### Production Observability

#### `GRAFANA_OTLP_ENDPOINT`
- **Purpose**: Grafana Cloud OTLP endpoint URL
- **Example**: `https://otlp-gateway-prod-us-central-0.grafana.net/otlp`
- **Required**: For production observability

#### `GRAFANA_OTLP_TOKEN`
- **Purpose**: Grafana Cloud authentication token (base64 encoded)
- **Format**: Base64 encoded `instanceID:token`
- **Required**: For production observability

### OpenLIT Configuration

#### `OPENLIT_ENVIRONMENT`
- **Default**: `Production`
- **Purpose**: Environment name for OpenLIT metrics
- **Values**: `Production`, `Development`, `Staging`, etc.

#### `OPENLIT_APPLICATION_NAME`
- **Default**: `DevOps Agent`
- **Purpose**: Application name for OpenLIT metrics

## Configuration Scenarios

### 1. Development (Clean Output - Default)
```bash
# No configuration needed - clean output by default
echo "hi" | uv run agent run agents.devops
```

### 2. Local Testing with Basic Metrics
```bash
# Enable local metrics without external export
export DEVOPS_AGENT_ENABLE_LOCAL_METRICS=true
```

### 3. Production with Full Observability
```bash
# Enable full observability
export DEVOPS_AGENT_OBSERVABILITY_ENABLE=true
# Optionally configure Grafana Cloud for export
export GRAFANA_OTLP_ENDPOINT="https://otlp-gateway-prod-us-central-0.grafana.net/otlp"
export GRAFANA_OTLP_TOKEN="your-grafana-cloud-token"
export OPENLIT_ENVIRONMENT="Production"
```

### 4. Rate Limiting Issues
```bash
# Disable export to prevent Grafana Cloud rate limiting
export DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT=true
# Or increase export interval
export GRAFANA_EXPORT_INTERVAL_SECONDS=300
```

## Decision Logic

The agent uses this logic to determine observability configuration:

1. **Explicitly Enabled**: If `DEVOPS_AGENT_OBSERVABILITY_ENABLE=true` → Full observability
2. **Local Metrics**: If `DEVOPS_AGENT_ENABLE_LOCAL_METRICS=true` → Local metrics only
3. **Configuration Present**: If Grafana Cloud or OpenLIT vars set → Auto-enable observability
4. **Default**: No explicit configuration → Clean output (observability disabled)

## Troubleshooting

### Problem: Messy JSON output in console
**Solution**: Observability is now disabled by default. If you see JSON output, check for existing observability configuration.

### Problem: "Failed to export batch code: 429"
**Solution**: Set `DEVOPS_AGENT_DISABLE_TELEMETRY_EXPORT=true` or increase `GRAFANA_EXPORT_INTERVAL_SECONDS`

### Problem: No metrics in Grafana Cloud
**Solution**: Verify `GRAFANA_OTLP_ENDPOINT` and `GRAFANA_OTLP_TOKEN` are set correctly

### Problem: High memory usage
**Solution**: Observability is disabled by default. If enabled, consider using local metrics only: `DEVOPS_AGENT_ENABLE_LOCAL_METRICS=true`

## Log Messages

When observability is properly configured, you should see one of these messages:

- `✅ OpenLIT observability enabled` - Observability is active
- `🚫 Observability disabled - skipping OpenLIT initialization` - Clean mode
- `🚫 Telemetry disabled - using no-op telemetry` - Local mode only

## Migration Guide

### From Previous Versions
If you were using the agent without observability configuration:

**Before**: Required manual configuration to avoid JSON spam
```bash
export DEVOPS_AGENT_DISABLE_OBSERVABILITY=true
echo "hi" | uv run agent run agents.devops
```

**After**: Clean output by default
```bash
echo "hi" | uv run agent run agents.devops
# Clean, readable output - no configuration needed
```

### Enabling Observability
To add observability when needed:

```bash
# For full observability
export DEVOPS_AGENT_OBSERVABILITY_ENABLE=true

# For local development with metrics only
export DEVOPS_AGENT_ENABLE_LOCAL_METRICS=true

# For production with Grafana Cloud
export DEVOPS_AGENT_OBSERVABILITY_ENABLE=true
export GRAFANA_OTLP_ENDPOINT="your-endpoint"
export GRAFANA_OTLP_TOKEN="your-token"
``` 