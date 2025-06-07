# DevOps Agent Logging Configuration

The DevOps Agent uses an intelligent logging system that automatically adjusts based on the execution context to provide the best user experience.

## Logging Modes

### Interactive Mode (Default)
When running the agent interactively (e.g., `./run.sh`), the logging system automatically:
- **Reduces console noise** by filtering out verbose system logs
- **Shows only warnings and errors** from noisy libraries (httpx, openlit, chromadb, etc.)
- **Preserves user-relevant information** like tool execution status and model usage
- **Maintains full logging** in log files for debugging

### Non-Interactive Mode
When running in scripts or CI/CD pipelines, the logging system:
- **Shows full console output** for debugging and monitoring
- **Includes all INFO level logs** for comprehensive visibility
- **Maintains structured logging** for log aggregation systems

## Environment Variables

Control logging behavior with these environment variables:

### `DEVOPS_AGENT_INTERACTIVE`
- **Default**: `true` (auto-detected)
- **Values**: `true`, `false`, `1`, `0`, `yes`, `no`
- **Purpose**: Force interactive or non-interactive logging mode

```bash
# Force interactive mode (quiet console)
export DEVOPS_AGENT_INTERACTIVE=true
./run.sh

# Force non-interactive mode (verbose console)
export DEVOPS_AGENT_INTERACTIVE=false
./run.sh
```

### `DEVOPS_AGENT_QUIET`
- **Default**: `false`
- **Values**: `true`, `false`, `1`, `0`, `yes`, `no`
- **Purpose**: Completely disable console logging (logs only to files)

```bash
# Silent mode - no console output except agent responses
export DEVOPS_AGENT_QUIET=true
./run.sh
```

## Auto-Detection Logic

The system automatically detects the execution context:

1. **Environment Variables**: Checks `DEVOPS_AGENT_INTERACTIVE` and `DEVOPS_AGENT_QUIET`
2. **TTY Detection**: Uses `sys.stdin.isatty()` to detect interactive terminals
3. **Python Shell**: Checks for `sys.ps1` (Python interactive shell)

## Filtered Loggers in Interactive Mode

These loggers are automatically quieted during interactive sessions:
- `httpx` - HTTP request logs
- `openlit` - OpenLIT instrumentation logs  
- `chromadb` - ChromaDB database logs
- `opentelemetry` - OpenTelemetry tracing logs
- `google_genai` - Google GenAI client logs
- `google_adk` - Google ADK framework logs
- `devops.components.context_management` - Context management internals
- `devops.tools.rag_components` - RAG system internals

## Log Files

All logs are always written to files regardless of console settings:

- **Location**: `devops_agent.log` (current directory)
- **Format**: Structured JSON with correlation IDs and OpenTelemetry traces
- **Level**: DEBUG (captures everything)
- **Rotation**: Manual (consider implementing log rotation for production)

## Correlation Tracking

Every log entry includes:
- **Correlation ID**: Unique identifier for request tracking
- **Trace ID**: OpenTelemetry trace identifier
- **Span ID**: OpenTelemetry span identifier
- **Operation Context**: Current operation being performed
- **User Session**: User session identifier

## Examples

### Development (Interactive)
```bash
# Clean console output, full file logging
./run.sh
```

### CI/CD Pipeline (Non-Interactive)
```bash
# Full console output for monitoring
export DEVOPS_AGENT_INTERACTIVE=false
./run.sh
```

### Silent Automation
```bash
# No console output, only file logging
export DEVOPS_AGENT_QUIET=true
./run.sh > agent_output.log 2>&1
```

### Debug Mode
```bash
# Force verbose output even in interactive mode
export DEVOPS_AGENT_INTERACTIVE=false
./run.sh
```

## Telemetry Integration

The logging system integrates with the telemetry module:
- **OpenTelemetry Traces**: All operations are traced
- **Correlation IDs**: Link logs to telemetry data
- **Structured Data**: Consistent format for log aggregation
- **Performance Metrics**: Automatic operation timing

## Best Practices

1. **Use environment variables** to control logging in different environments
2. **Monitor log files** for detailed debugging information
3. **Set up log aggregation** in production environments
4. **Use correlation IDs** to trace requests across systems
5. **Configure log rotation** for long-running deployments

## Troubleshooting

### Too Much Console Output
```bash
export DEVOPS_AGENT_INTERACTIVE=true
# or
export DEVOPS_AGENT_QUIET=true
```

### Missing Debug Information
```bash
export DEVOPS_AGENT_INTERACTIVE=false
# Check devops_agent.log for full details
```

### No Console Output
```bash
unset DEVOPS_AGENT_QUIET
export DEVOPS_AGENT_INTERACTIVE=false
``` 