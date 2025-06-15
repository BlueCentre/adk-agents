# Markdown Rendering in Interruptible CLI

The `--interruptible` CLI mode now supports **markdown rendering** for agent responses! This makes the output much more readable and visually appealing.

## Features

### Headers
- `# Header 1` → 🔷 Header 1
- `## Header 2` → 🔸 Header 2  
- `### Header 3` → ▪️ Header 3

### Text Formatting
- `**bold text**` → [bold text]
- `*italic text*` → (italic text)
- `__bold text__` → [bold text]
- `_italic text_` → (italic text)

### Code
- `` `inline code` `` → `inline code`
- Code blocks with syntax highlighting:
```python
def hello():
    print("Hello, World!")
```
→ 💻 Code:
def hello():
    print("Hello, World!")

### Lists
- `- Item 1` → • Item 1
- `* Item 2` → • Item 2
- `+ Item 3` → • Item 3
- `1. Numbered` → 1️⃣ Numbered

### Other Elements
- `> Blockquote` → 💬 Blockquote
- `[Link](https://example.com)` → Link (https://example.com)
- `---` → ──────────────────────────────────────────────────

## Usage

### Toggle Markdown Rendering
- **Ctrl+M** - Toggle markdown rendering on/off
- Status bar shows 📝 when enabled, 📄 when disabled
- Enabled by default

### Example Agent Response
When an agent responds with markdown like:

```markdown
# Analysis Results

## Summary
The code analysis found **3 issues**:

1. Missing error handling
2. Unused variables
3. Performance bottleneck

### Recommendations
- Add `try/catch` blocks
- Remove unused code
- Optimize the `process_data()` function

> **Note**: These are suggestions, not requirements.
```

It will be rendered as:

```
🔷 Analysis Results

🔸 Summary
The code analysis found [3 issues]:

1️⃣ Missing error handling
2️⃣ Unused variables  
3️⃣ Performance bottleneck

▪️ Recommendations
• Add `try/catch` blocks
• Remove unused code
• Optimize the `process_data()` function

💬 [Note]: These are suggestions, not requirements.
```

## Benefits

✅ **Better readability** - Structured content with visual hierarchy  
✅ **Emoji indicators** - Quick visual scanning of content types  
✅ **Terminal-friendly** - Works well in any terminal environment  
✅ **Toggle-able** - Can be disabled if plain text is preferred  
✅ **Preserves functionality** - All CLI features still work normally

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+M | Toggle markdown rendering |
| Ctrl+T | Toggle theme (dark/light) |
| Ctrl+C | Interrupt agent |
| Ctrl+L | Clear output |
| Ctrl+D | Exit |

The markdown rendering makes agent responses much more pleasant to read while maintaining the powerful interruptible CLI functionality! 