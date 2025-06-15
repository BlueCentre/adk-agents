# Interruptible CLI for ADK Agents

The ADK now supports an enhanced **Interruptible CLI** that provides persistent input capabilities and the ability to interrupt long-running agent operations. This feature significantly improves the user experience by allowing real-time interaction with agents.

## Features

### 🎯 Persistent Input Pane
- **Always-available input**: Type commands while the agent is processing
- **Split-pane interface**: Output displayed above, input below
- **Real-time typing**: No need to wait for agent responses to complete

### ⚡ Agent Interruption
- **Ctrl+C interruption**: Stop long-running agent operations instantly
- **Graceful cancellation**: Agents receive cancellation signals cleanly
- **Immediate responsiveness**: Continue with new queries after interruption

### 🎨 Enhanced UI
- **Themed interface**: Dark and light themes with dynamic switching
- **Status indicators**: Real-time display of agent state
- **Visual feedback**: Clear indication when agent is thinking vs. ready
- **Keyboard shortcuts**: Comprehensive hotkey support

## Usage

### Command Line Options

```bash
# Enable interruptible CLI
uv run python -m src.wrapper.adk.cli.cli --agent agents.devops --interruptible

# With theme selection
uv run python -m src.wrapper.adk.cli.cli --agent agents.devops --interruptible --theme dark

# Regular CLI (original behavior)
uv run python -m src.wrapper.adk.cli.cli --agent agents.devops
```

### In-Application Commands

| Command | Description |
|---------|-------------|
| `help` | Show available commands and shortcuts |
| `clear` | Clear the output pane |
| `theme toggle` | Switch between light/dark themes |
| `theme dark/light` | Set specific theme |
| `exit`, `quit`, `bye` | Exit the CLI |

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Submit input (when agent not running) |
| `Alt+Enter` | Insert newline in input |
| `Ctrl+C` | Interrupt running agent |
| `Ctrl+D` | Exit application |
| `Ctrl+L` | Clear output pane |
| `Ctrl+T` | Toggle theme |

## Technical Architecture

### Split-Pane Layout

```
┌─────────────────────────────────────────┐
│          🤖 Agent Output                │
│                                         │
│  Agent responses appear here in         │
│  real-time as they're generated         │
│                                         │
│                                         │
├─────────────────────────────────────────┤
│          😎 User Input                  │
│                                         │
│  > Type your commands here...           │
│                                         │
├─────────────────────────────────────────┤
│ 🟢 Ready | Theme: 🌒 Dark | 10:30:45   │
└─────────────────────────────────────────┘
```

### Async Task Management

The interruptible CLI uses asyncio for concurrent operations:

- **Input handling**: Always responsive, even during agent processing
- **Agent execution**: Runs in separate tasks that can be cancelled
- **Output streaming**: Real-time display of agent responses
- **State management**: Thread-safe tracking of agent status

### Interruption Mechanism

When you press `Ctrl+C`:

1. **Detection**: Key binding captures the interrupt signal
2. **Task cancellation**: Current agent task receives `asyncio.CancelledError`
3. **Cleanup**: Agent resources are cleaned up gracefully
4. **Recovery**: System returns to ready state for new input

## Implementation Details

### Core Components

```python
class InterruptibleCLI:
    """CLI with persistent input pane and agent interruption capabilities."""
    
    def __init__(self, theme: Optional[UITheme] = None):
        # State management
        self.agent_running = False
        self.current_agent_task: Optional[asyncio.Task] = None
        
        # UI Components  
        self.input_buffer = Buffer(multiline=True)
        self.output_buffer = Buffer(read_only=True)
        self.status_buffer = Buffer(read_only=True)
```

### Key Methods

- `register_input_callback()`: Set handler for user input
- `register_interrupt_callback()`: Set handler for interruptions
- `add_agent_output()`: Stream agent responses to output pane
- `set_agent_task()`: Track current agent task for interruption

## Examples

### Basic Usage

```python
import asyncio
from src.wrapper.adk.cli.cli import run_cli

# Run with interruptible CLI
await run_cli(
    agent_module_name="agents.devops",
    interruptible=True,
    ui_theme="dark"
)
```

### Demo Script

```bash
# Run the demo
uv run python example_prompts/interruptible_cli_demo.py
```

## Benefits

### For Users
- **No waiting**: Continue typing while agent processes
- **Control**: Stop long operations when needed
- **Efficiency**: Better workflow with immediate responsiveness
- **Visibility**: Clear status of what the agent is doing

### For Developers
- **Better testing**: Interrupt long-running operations during development
- **Debugging**: Cleaner separation of input/output streams
- **Flexibility**: Choose between regular and interruptible modes
- **Extensibility**: Framework for advanced CLI features

## Compatibility

- **Backwards compatible**: Original CLI behavior preserved
- **Opt-in feature**: Use `--interruptible` flag to enable
- **Fallback support**: Gracefully falls back to regular CLI if needed
- **Terminal support**: Works with modern terminal emulators

## Future Enhancements

- **Multi-agent support**: Switch between different agents
- **Session management**: Save/restore interactive sessions
- **Plugin system**: Custom commands and shortcuts
- **Advanced layouts**: Configurable pane arrangements

---

The Interruptible CLI transforms the ADK agent interaction experience from a sequential question-answer pattern to a dynamic, responsive interface that puts users in control. 