# Automatic Retry System for Model Requests

## Overview

The retry system provides automatic retry logic with exponential backoff for handling transient model API failures, specifically the `"No message in response"` error from LiteLLM.

**Key Feature**: The system works by **wrapping the model's `generate_content_async` method** with retry logic, ensuring that every model call automatically benefits from exponential backoff retry behavior.

## Problem Solved

When using LiteLLM with various model providers (especially Gemini), sometimes the API returns a successful HTTP response but with empty or missing message content, causing a `ValueError: "No message in response"`. This error is typically transient and can be resolved by retrying the request.

## How It Works

### Model Method Wrapping

The retry system integrates at the **model execution level** by:

1. **Capturing the original method**: Stores the original `model.generate_content_async` method
2. **Creating a retry wrapper**: Implements `generate_content_async_with_retry` that:
   - Calls the original method within a retry handler
   - Applies exponential backoff on `"No message in response"` errors
   - Maintains the same async generator interface
3. **Replacing the method**: Uses `object.__setattr__` to bypass Pydantic validation and replace the model's method
4. **Preserving interface**: The wrapped method maintains the exact same signature and behavior for successful calls

### Integration Points

The retry system integrates at multiple levels:

- **Model Level**: Direct method wrapping for actual retry execution
- **Callback Level**: `before_model` and `after_model` callbacks for state management
- **Agent Level**: Automatic integration for enhanced agents

### Code Flow

```python
# Original flow (without retry)
llm_request → model.generate_content_async() → response/error

# With retry system  
llm_request → generate_content_async_with_retry() → retry_handler() → original_method() → response (with retries on failure)
```

## Integration

### Automatic Integration (Enhanced Agent)

The enhanced software engineer agent automatically includes retry capabilities:

```python
from agents.software_engineer.enhanced_agent import create_enhanced_software_engineer_agent

# Agent automatically has retry capabilities enabled
agent = create_enhanced_software_engineer_agent()

# Model calls now automatically retry on "No message in response" errors
# No additional code needed - it's transparent to the user
```

### Manual Integration

For custom agents, you can add retry capabilities manually:

```python
from agents.software_engineer.shared_libraries.callbacks import create_retry_callbacks
from agents.software_engineer.enhanced_agent import add_retry_capabilities_to_agent

# Create retry callbacks
retry_callbacks = create_retry_callbacks(
    agent_name="my_agent",
    max_retries=3,
    base_delay=1.0,
    max_delay=8.0,
    backoff_multiplier=2.0
)

# Add retry capabilities to your agent (wraps the model method)
agent_with_retry = add_retry_capabilities_to_agent(agent, retry_callbacks["retry_handler"])

# Include callbacks in agent configuration
agent = Agent(
    # ... other configuration ...
    before_model_callback=[retry_callbacks["before_model"]],
    after_model_callback=[retry_callbacks["after_model"]],
)
```

## Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_retries` | 3 | Maximum number of retry attempts |
| `base_delay` | 1.0 | Initial delay between retries (seconds) |
| `max_delay` | 8.0 | Maximum delay between retries (seconds) |
| `backoff_multiplier` | 2.0 | Multiplier for exponential backoff |

## Delay Calculation

Delays are calculated using exponential backoff with jitter:

```python
delay = min(base_delay * (backoff_multiplier ** attempt), max_delay)
actual_delay = delay * (0.8 + 0.4 * random.random())  # ±20% jitter
```

Example with default settings:
- Attempt 1: ~1.0s (0.8-1.2s)
- Attempt 2: ~2.0s (1.6-2.4s)  
- Attempt 3: ~4.0s (3.2-4.8s)
- Attempt 4: ~8.0s (6.4-9.6s) - capped at max_delay

## Logging

The retry system provides detailed logging:

```
INFO - [agent_name] Creating retry callbacks with max_retries=3, base_delay=1.0s, max_delay=8.0s
INFO - [agent_name] Retry capabilities integrated - model calls now include automatic retry with exponential backoff
WARNING - [agent_name] Model request failed (attempt 1/4): No message in response. Retrying in 1.2s...
INFO - [agent_name] Model request succeeded on attempt 2
```

## Selective Retry Logic

The system only retries specific errors:

- **Retried**: `ValueError` with message `"No message in response"`
- **Not Retried**: All other exceptions (authentication, network, etc.)

This ensures that only transient model response issues are retried, not systematic problems.

## Technical Implementation

### Method Wrapping Process

```python
def add_retry_capabilities_to_agent(agent, retry_handler):
    # Get the model and store original method
    model = agent.model
    original_generate_content_async = model.generate_content_async
    
    # Create retry wrapper
    async def generate_content_async_with_retry(llm_request, stream=False):
        async def model_call():
            responses = []
            async for response in original_generate_content_async(llm_request, stream):
                responses.append(response)
            return responses
        
        responses = await retry_handler(model_call)
        for response in responses:
            yield response
    
    # Replace method using object.__setattr__ to bypass Pydantic validation
    object.__setattr__(model, 'generate_content_async', generate_content_async_with_retry)
    
    # Store references for debugging
    agent._retry_handler = retry_handler
    agent._original_generate_content_async = original_generate_content_async
```

### Pydantic Compatibility

The LiteLLM model classes use Pydantic validation, which prevents direct attribute assignment. The system uses `object.__setattr__` to bypass this validation safely.

## Performance Impact

- **Successful calls**: Minimal overhead (single function call wrapper)
- **Failed calls**: Adds delay only when retries are needed
- **Memory**: Stores references to original method and retry handler
- **Concurrency**: Each model call is retried independently

## Best Practices

1. **Use default configuration** for most cases
2. **Monitor retry rates** - high retry rates may indicate upstream issues
3. **Set appropriate timeouts** for your use case
4. **Consider retry budgets** for cost-sensitive applications
5. **Test with realistic failure scenarios**

## Troubleshooting

### Common Issues

**Q: Retries not happening**
- Verify the agent has `_retry_handler` attribute
- Check that model method name contains `with_retry`
- Ensure error message exactly matches `"No message in response"`

**Q: Too many retries**
- Reduce `max_retries` parameter
- Check for systematic API issues
- Monitor retry logs for patterns

**Q: Performance impact**
- Retries only occur on failures
- Successful calls have minimal overhead
- Consider reducing `max_retries` for faster failure responses

### Verification Commands

```python
# Check if agent has retry capabilities
assert hasattr(agent, '_retry_handler')
assert agent._retry_handler is not None

# Verify model method is wrapped
assert 'with_retry' in agent.model.generate_content_async.__name__

# Check original method is preserved
assert hasattr(agent, '_original_generate_content_async')
```

## Future Enhancements

- **Adaptive retry delays** based on error patterns
- **Circuit breaker** for persistent failures  
- **Retry budgets** and rate limiting
- **Custom retry predicates** for different error types
- **Metrics collection** for retry analytics 