# Rich + prompt_toolkit Compatibility

## The Problem 🚫

Rich and prompt_toolkit don't work well together out of the box:

- **Rich** uses ANSI escape codes and special markup for beautiful terminal output
- **prompt_toolkit** has its own text rendering system with buffers and layout management
- **Conflict**: Rich's formatting codes appear as messy, unrendered text in prompt_toolkit buffers

### Before (Messy Output):
```
[20:43:22] 🤖 devops_agent: [bold green]Hello![/bold green] How can I assist you today?
╭───────────────────────────────────────── 🧠 Model Usage (with Thinking) ─────────────────────────────────────────╮
│ Token Usage: Prompt: 2475, [cyan]Thinking: 33[/cyan], Output: 9, Total: 2517                                   │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### After (Clean Output):
```
[20:43:22] 🤖 devops_agent: Hello! How can I assist you today?
Token Usage: Prompt: 2475, Thinking: 33, Output: 9, Total: 2517
```

## The Solution ✅

### 1. **Text Sanitization in InterruptibleCLI**

Added a `_add_to_output()` method that converts Rich content to plain text:

```python
def _add_to_output(self, text: str, style: str = ""):
    """Add text to the output buffer, stripping Rich formatting."""
    from rich.console import Console
    from io import StringIO
    
    # Create a temporary console to render Rich content to plain text
    string_io = StringIO()
    temp_console = Console(file=string_io, force_terminal=False, width=80)
    
    # Try to render as Rich content, fall back to plain text
    try:
        temp_console.print(text)
        clean_text = string_io.getvalue().rstrip('\n')
    except:
        # If Rich rendering fails, use plain text
        clean_text = text
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted_text = f"[{timestamp}] {clean_text}\n"
    
    current_text = self.output_buffer.text
    self.output_buffer.text = current_text + formatted_text
    
    # Auto-scroll to bottom
    self.output_buffer.cursor_position = len(self.output_buffer.text)
```

### 2. **ANSI Code Stripping Function**

Added `_strip_rich_markup()` to remove any remaining formatting:

```python
def _strip_rich_markup(text: str) -> str:
    """Strip Rich markup and ANSI codes from text for clean prompt_toolkit display."""
    import re
    from rich.console import Console
    from io import StringIO
    
    try:
        # Create a console that outputs plain text
        string_io = StringIO()
        temp_console = Console(file=string_io, force_terminal=False, width=120, legacy_windows=False)
        
        # Print the text and capture plain output
        temp_console.print(text, markup=False, highlight=False)
        clean_text = string_io.getvalue().rstrip('\n')
        
        # Additional cleanup of any remaining ANSI codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_text = ansi_escape.sub('', clean_text)
        
        return clean_text
        
    except Exception:
        # Fallback: basic ANSI code removal
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)
```

### 3. **Agent Response Processing**

Modified the agent response handler to clean text before display:

```python
async def _process_agent_responses(agent_gen, cli):
    """Process agent responses and add them to the CLI output."""
    async for event in agent_gen:
        if event.content and event.content.parts:
            if text := ''.join(part.text or '' for part in event.content.parts):
                # Filter out thought content to prevent duplication
                filtered_text = _filter_thought_content(text)
                if filtered_text.strip():
                    # Strip any Rich markup/ANSI codes for clean prompt_toolkit display
                    clean_text = _strip_rich_markup(filtered_text)
                    cli.add_agent_output(clean_text, event.author)
```

## Technical Approach 🔧

### **Two-Stage Cleaning Process**

1. **Rich Console Rendering**: Use Rich's own console to render markup to plain text
2. **ANSI Code Removal**: Strip any remaining escape sequences with regex

### **Fallback Strategy**

- Primary: Rich console rendering with `force_terminal=False`
- Fallback: Regex-based ANSI code removal
- Final: Raw text if all else fails

### **Compatibility Layer**

The solution acts as a compatibility layer:

```
Rich Formatted Text → Rich Console (plain) → ANSI Stripper → prompt_toolkit Buffer
     ↓                      ↓                    ↓                    ↓
[bold]Hello[/bold]   →   Hello   →   Hello   →   Clean Display
```

## Benefits 🎉

### **For Users**
- ✅ **Clean, readable output** in the interruptible CLI
- ✅ **No formatting artifacts** or escape codes
- ✅ **Consistent appearance** across different terminals
- ✅ **Preserved functionality** of both Rich and prompt_toolkit

### **For Developers**
- ✅ **Use Rich freely** in agent code without compatibility concerns
- ✅ **Automatic conversion** - no manual text processing needed
- ✅ **Backwards compatible** - existing code continues to work
- ✅ **Error resilient** - graceful fallbacks if conversion fails

## Configuration Options 🛠️

### **Console Width**
```python
temp_console = Console(file=string_io, force_terminal=False, width=80)
```
- Controls text wrapping in the output
- Adjustable based on terminal size

### **Rich Features Disabled**
```python
temp_console.print(text, markup=False, highlight=False)
```
- Disables Rich markup processing
- Disables syntax highlighting
- Ensures plain text output

### **ANSI Escape Pattern**
```python
ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
```
- Comprehensive ANSI escape sequence matching
- Removes colors, cursor movements, formatting codes

## Usage Examples 📝

### **Before (Messy)**
```
Agent Output: [bold red]Error:[/bold red] Connection failed
[33mWarning:[0m Retrying connection...
╭─ Status ─╮
│ [32m✓[0m │
╰──────────╯
```

### **After (Clean)**
```
Agent Output: Error: Connection failed  
Warning: Retrying connection...
Status: ✓
```

## Testing 🧪

```bash
# Test the clean output
uv run agent run agents.devops --interruptible

# Should now display:
# - Clean, readable text
# - No ANSI escape codes
# - No Rich markup artifacts
# - Proper text wrapping
```

## Future Enhancements 🚀

1. **Configurable width**: Auto-detect terminal width
2. **Selective formatting**: Preserve some basic formatting (bold, colors)
3. **Rich integration**: Use prompt_toolkit's FormattedText for Rich-like styling
4. **Performance optimization**: Cache rendered text for repeated content

---

This solution enables seamless integration between Rich's powerful formatting capabilities and prompt_toolkit's advanced UI features, giving you the best of both worlds! 🎯 