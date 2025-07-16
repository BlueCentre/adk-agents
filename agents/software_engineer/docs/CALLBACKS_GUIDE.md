# SWE Agent Callbacks Guide

This guide explains how to use the telemetry and observability callbacks implemented for the Software Engineer Agent.

## Overview

The SWE agent now includes comprehensive callback support that provides:

- **Telemetry and Observability**: Track LLM requests, responses, and tool executions
- **Performance Monitoring**: Measure response times and token usage
- **Error Tracking**: Monitor tool failures and execution issues
- **Enhanced Debugging**: Detailed logging of agent operations

## Implementation

### Callback Types

The implementation provides two types of callbacks:

1. **Basic Callbacks** (`create_telemetry_callbacks`): Standard logging and timing
2. **Enhanced Callbacks** (`create_enhanced_telemetry_callbacks`): Includes DevOps agent telemetry integration

### Callback Functions

Each agent gets four callback functions:

- `before_model_callback`: Executed before LLM model requests
- `after_model_callback`: Executed after LLM model responses
- `before_tool_callback`: Executed before tool executions
- `after_tool_callback`: Executed after tool executions

## Usage

### Automatic Integration

The callbacks are automatically integrated into:

- **Main SWE Agent** (`agents/software_engineer/agent.py`)
- **Enhanced SWE Agent** (`agents/software_engineer/enhanced_agent.py`)
- **Sub-agents** (code_review_agent, debugging_agent, etc.)

### Manual Integration

To add callbacks to a new agent:

```python
from agents.software_engineer.shared_libraries.callbacks import create_enhanced_telemetry_callbacks

# Create callbacks
(
    before_model_callback,
    after_model_callback,
    before_tool_callback,
    after_tool_callback,
) = create_enhanced_telemetry_callbacks("my_agent_name")

# Apply to agent
my_agent = Agent(
    model="gemini-2.0-flash",
    name="my_agent",
    description="My custom agent",
    instruction="Do something useful",
    tools=[...],
    # Add callbacks
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
    before_tool_callback=before_tool_callback,
    after_tool_callback=after_tool_callback,
)
```

## What Gets Tracked

### LLM Requests/Responses
- Request content preview
- Response content preview
- Response time
- Token usage (prompt tokens, completion tokens, total)
- Model information

### Tool Executions
- Tool name and input parameters
- Execution time
- Success/failure status
- Output results
- Error details

### Enhanced Telemetry (when available)
- Integration with DevOps agent telemetry system
- Structured metrics collection
- OpenTelemetry tracing support
- Performance analytics

## Log Output Examples

### Basic Callback Logs
```
2024-01-15 10:30:15 - agents.software_engineer.shared_libraries.callbacks - DEBUG - [software_engineer] Before model request - ID: inv_123
2024-01-15 10:30:15 - agents.software_engineer.shared_libraries.callbacks - DEBUG - [software_engineer] Request content preview: Hello, can you help me...
2024-01-15 10:30:17 - agents.software_engineer.shared_libraries.callbacks - DEBUG - [software_engineer] After model response - ID: inv_123
2024-01-15 10:30:17 - agents.software_engineer.shared_libraries.callbacks - DEBUG - [software_engineer] Response time: 2.15s
2024-01-15 10:30:17 - agents.software_engineer.shared_libraries.callbacks - INFO - [software_engineer] Token usage - Prompt: 150, Response: 300, Total: 450
```

### Tool Execution Logs
```
2024-01-15 10:30:18 - agents.software_engineer.shared_libraries.callbacks - DEBUG - [software_engineer] Before tool execution - Tool: read_file_tool, ID: inv_124
2024-01-15 10:30:18 - agents.software_engineer.shared_libraries.callbacks - DEBUG - [software_engineer] Tool input preview: {'file_path': 'src/main.py'}
2024-01-15 10:30:18 - agents.software_engineer.shared_libraries.callbacks - DEBUG - [software_engineer] After tool execution - Tool: read_file_tool, ID: inv_124
2024-01-15 10:30:18 - agents.software_engineer.shared_libraries.callbacks - DEBUG - [software_engineer] Tool execution time: 0.05s
2024-01-15 10:30:18 - agents.software_engineer.shared_libraries.callbacks - DEBUG - [software_engineer] Tool read_file_tool completed successfully
```

## Configuration

### Logging Level
Set the logging level to see callback output:

```bash
export LOG_LEVEL=DEBUG
```

Or in Python:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Enhanced Telemetry
Enhanced telemetry automatically activates when DevOps agent telemetry is available:

```python
# This will try to import DevOps telemetry
from ...devops.telemetry import track_llm_request, track_tool_execution
```

If import fails, it falls back to basic callbacks.

## Testing

Run the callback test script:

```bash
cd agents/software_engineer/examples
python test_callbacks.py
```

This will:
1. Test callback creation
2. Test agent execution with callbacks
3. Verify sub-agent callback integration

## Benefits

### For Development
- **Debugging**: See exactly what the agent is doing
- **Performance**: Identify slow operations
- **Usage**: Track token consumption and costs

### For Production
- **Monitoring**: Track agent health and performance
- **Analytics**: Understand usage patterns
- **Troubleshooting**: Diagnose issues quickly

### For Optimization
- **Bottlenecks**: Identify slow tools or models
- **Efficiency**: Optimize token usage
- **Reliability**: Monitor error rates

## Integration with DevOps Agent

The enhanced callbacks can leverage the DevOps agent's telemetry system when available:

- **Structured Metrics**: Consistent metric collection
- **OpenTelemetry**: Distributed tracing support
- **Performance Analytics**: Advanced monitoring capabilities
- **Shared Infrastructure**: Unified observability across agents

This provides a consistent observability experience across all agents in the system.

## Future Enhancements

Planned improvements include:

1. **Custom Metrics**: Agent-specific performance indicators
2. **Alerting**: Automatic notifications for issues
3. **Dashboards**: Visual monitoring interfaces
4. **Cost Tracking**: Detailed usage and cost analysis
5. **A/B Testing**: Compare agent performance variations 