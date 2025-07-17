# SWE Agent Callbacks Guide

This guide explains how to use the telemetry and observability callbacks implemented for the Software Engineer Agent.

## Overview

The SWE agent now includes comprehensive callback support that provides:

- **Telemetry and Observability**: Track LLM requests, responses, and tool executions
- **Performance Monitoring**: Measure response times and token usage
- **Error Tracking**: Monitor tool failures and execution issues
- **Enhanced Debugging**: Detailed logging of agent operations
- **Agent Lifecycle Tracking**: Monitor entire agent sessions with agent callbacks

## Implementation

### Callback Types

The implementation provides two types of callbacks:

1. **Basic Callbacks** (`create_telemetry_callbacks`): Standard logging and timing
2. **Enhanced Callbacks** (`create_enhanced_telemetry_callbacks`): Includes DevOps agent telemetry integration

### Callback Functions

Each agent now gets **six callback functions** (previously four):

- **`before_agent_callback`**: Executed when agent session starts (**NEW**)
- **`after_agent_callback`**: Executed when agent session ends (**NEW**)
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

# Create callbacks (returns a dictionary)
callbacks = create_enhanced_telemetry_callbacks("my_agent_name")

# Apply to agent
my_agent = Agent(
    model="gemini-2.0-flash",
    name="my_agent",
    description="My custom agent",
    instruction="Do something useful",
    tools=[...],
    # Add all callbacks using dictionary keys
    before_agent_callback=callbacks["before_agent"],
    after_agent_callback=callbacks["after_agent"],
    before_model_callback=callbacks["before_model"],
    after_model_callback=callbacks["after_model"],
    before_tool_callback=callbacks["before_tool"],
    after_tool_callback=callbacks["after_tool"],
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

### **Agent Lifecycle (NEW)**
- **Session Start/End**: Track when agent sessions begin and complete
- **Session Duration**: Total time spent in agent session
- **Project Context**: Automatic detection of project type, files, and structure
- **Session Metrics**: Aggregated statistics across the entire session
  - Total LLM calls made
  - Total tool executions
  - Total tokens consumed
  - Error counts
  - Project metadata (type, file counts, etc.)
- **Agent Identification**: Track which specific agent and session ID
- **Cleanup Operations**: Monitor resource cleanup and session termination

### Enhanced Telemetry (when available)
- Integration with DevOps agent telemetry system
- Structured metrics collection
- OpenTelemetry tracing support
- Performance analytics

## Agent Callbacks: Additional Information Available

### `before_agent_callback`
When an agent session starts, this callback captures:

- **Session Identification**: Session ID and agent name
- **Project Context Discovery**: 
  - Working directory
  - Project type detection (Python, JavaScript, Rust, Go, etc.)
  - File count statistics
  - Project structure overview
- **Session Initialization**: 
  - Session start timestamp
  - Metrics initialization
  - Resource preparation

### `after_agent_callback`
When an agent session ends, this callback provides:

- **Session Summary**: Complete statistics for the entire session
- **Performance Metrics**: 
  - Total session duration
  - LLM call frequency
  - Tool usage patterns
  - Token consumption totals
- **Error Analysis**: 
  - Error counts and types
  - Failure patterns
- **Project Insights**: 
  - Project type and characteristics
  - File processing statistics
- **Resource Cleanup**: 
  - Cleanup completion status
  - Resource deallocation

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

### **Agent Lifecycle Logs (NEW)**
```
2024-01-15 10:30:10 - agents.software_engineer.shared_libraries.callbacks - INFO - [software_engineer] Agent session started - Session ID: sess_456
2024-01-15 10:30:10 - agents.software_engineer.shared_libraries.callbacks - INFO - [software_engineer] Project context loaded: {'project_type': 'python', 'total_files': 142, 'python_files': 89}
2024-01-15 10:30:10 - agents.software_engineer.shared_libraries.callbacks - INFO - [software_engineer] Agent lifecycle: SESSION_START

... (model and tool callbacks during session) ...

2024-01-15 10:35:22 - agents.software_engineer.shared_libraries.callbacks - INFO - [software_engineer] Agent session ended - Session ID: sess_456
2024-01-15 10:35:22 - agents.software_engineer.shared_libraries.callbacks - INFO - [software_engineer] Total session duration: 312.15s
2024-01-15 10:35:22 - agents.software_engineer.shared_libraries.callbacks - INFO - [software_engineer] Session summary:
2024-01-15 10:35:22 - agents.software_engineer.shared_libraries.callbacks - INFO - [software_engineer]   Total model calls: 15
2024-01-15 10:35:22 - agents.software_engineer.shared_libraries.callbacks - INFO - [software_engineer]   Total tool calls: 42
2024-01-15 10:35:22 - agents.software_engineer.shared_libraries.callbacks - INFO - [software_engineer]   Total tokens used: 8750
2024-01-15 10:35:22 - agents.software_engineer.shared_libraries.callbacks - INFO - [software_engineer]   Errors encountered: 2
2024-01-15 10:35:22 - agents.software_engineer.shared_libraries.callbacks - INFO - [software_engineer]   Project type: python
2024-01-15 10:35:22 - agents.software_engineer.shared_libraries.callbacks - INFO - [software_engineer] Session cleanup completed
2024-01-15 10:35:22 - agents.software_engineer.shared_libraries.callbacks - INFO - [software_engineer] Agent lifecycle: SESSION_END
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
4. **Test agent lifecycle callbacks (NEW)**

## Benefits

### For Development
- **Debugging**: See exactly what the agent is doing
- **Performance**: Identify slow operations
- **Usage**: Track token consumption and costs
- **Session Analysis**: Understand agent behavior patterns

### For Production
- **Monitoring**: Track agent health and performance
- **Analytics**: Understand usage patterns
- **Troubleshooting**: Diagnose issues quickly
- **Session Management**: Monitor agent lifecycle and resource usage

### For Optimization
- **Bottlenecks**: Identify slow tools or models
- **Efficiency**: Optimize token usage
- **Reliability**: Monitor error rates
- **Project Insights**: Understand how agents interact with different project types

## Integration with DevOps Agent

The enhanced callbacks can leverage the DevOps agent's telemetry system when available:

- **Structured Metrics**: Consistent metric collection
- **OpenTelemetry**: Distributed tracing support
- **Performance Analytics**: Advanced monitoring capabilities
- **Agent Session Tracking**: Cross-session correlation and analysis

## Migration Guide

If you're upgrading from the previous four-callback system:

1. **Update callback creation**: The functions now return 6 callbacks instead of 4
2. **Add agent callbacks**: Include `before_agent_callback` and `after_agent_callback` in your agent configuration
3. **Update tests**: Ensure your tests account for the new agent lifecycle callbacks
4. **Review logs**: You'll now see additional agent session logs providing session-level insights

### Example Migration

**Before:**
```python
(
    before_model_callback,
    after_model_callback,
    before_tool_callback,
    after_tool_callback,
) = create_telemetry_callbacks("my_agent")
```

**After:**
```python
# The function now returns a dictionary
callbacks = create_telemetry_callbacks("my_agent")
# And you would pass them to the agent like this:
# my_agent = Agent(
#     ...
#     before_agent_callback=callbacks["before_agent"],
#     after_agent_callback=callbacks["after_agent"],
#     before_model_callback=callbacks["before_model"],
#     after_model_callback=callbacks["after_model"],
#     before_tool_callback=callbacks["before_tool"],
#     after_tool_callback=callbacks["after_tool"],
# )
```

The agent callbacks provide valuable session-level telemetry that complements the existing model and tool callbacks, giving you complete visibility into agent behavior from session start to completion.
