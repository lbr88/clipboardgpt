# ClipboardGPT

A clipboard manager that uses OpenAI's GPT to process selected text. Features a template system for custom prompts and integrates with i3/rofi for quick access.

## Demo
![Demo](https://raw.githubusercontent.com/lbr88/clipboardgpt/main/clipboardgpt-demo.gif)

## Prerequisites
- [uv](https://github.com/astral-sh/uv)
- `xsel` or `xclip` (for clipboard access)
- `xdotool` (for window title detection)
- `rofi` or `dmenu` (for prompt selection menu)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/lbr88/clipboardgpt.git
   cd clipboardgpt
   ```

2. Install the tool:
   ```bash
   uv tool install .
   ```
   *Note: Ensure `~/.local/bin` is in your `$PATH`.*

3. Configure the tool using the TUI:
   ```bash
   clipboardgpt-config
   ```
   
   Or manually create `~/.config/clipboardgpt/config.toml`:
   ```toml
   openai_api_key = "your_openai_api_key"
   name = "Your Name"
   model = "gpt-4o"
   menu_command = "rofi -dmenu -p 'ClipboardGPT'"
   ```

   **Automatic Migration:** Old `.env` files and legacy prompt formats are automatically migrated on first run.

## i3 Configuration

Add these keybindings to your i3 config (`~/.config/i3/config`):

```config
# Show rofi menu to select prompt type
bindsym $mod+g exec clipboardgpt

# Direct shortcuts for specific prompt types
bindsym $mod+Shift+g exec clipboardgpt -t grammar
bindsym $mod+Shift+r exec clipboardgpt -t reply
```

**Workflow:**
1. Select text in any application
2. Press `$mod+g` to open the prompt selection menu
3. Choose a prompt type (grammar, reply, or custom)
4. Wait for the notification with the result
5. Paste from clipboard (`Ctrl+v`)

## Usage

```bash
# Show menu to select prompt type (default)
clipboardgpt

# Use a specific prompt type directly
clipboardgpt -t grammar
clipboardgpt -t reply

# Add context to the prompt
clipboardgpt -t reply -c "be formal and professional"

# Use a different model
clipboardgpt -t grammar -m gpt-4-turbo

# List available prompt types
clipboardgpt --list
```

## Custom Prompts

Add custom prompts in the TUI (`clipboardgpt-config`) or directly in `config.toml`:

```toml
[prompts.translate]
system = "You are a translator. Translate text to English."
user = "{text}"

[prompts.summarize]
system = "Summarize the following text concisely."
user = """{?context}Focus on: {context}
Text: {text}"""

[prompts.code_review]
system = "You are a code reviewer. Review the code and suggest improvements."
user = """{?context}Language: {context}
Code:
{text}"""
```

### Template Variables

| Variable | Description |
|----------|-------------|
| `{text}` | The selected text |
| `{context}` | Additional context from `-c` flag |
| `{window_title}` | Active window title |
| `{app}` | Application type (chat, email, terminal, editor, browser) |
| `{name}` | Your name from config |

### Conditional Lines

Prefix a line with `{?variable}` to only include it when the variable is non-empty:

```toml
[prompts.reply]
system = "Write a response to the message."
user = \"\"\"{?app}This is a {app} conversation.
{?context}Context: {context}
{?name}Responding as: {name}
Message: {text}\"\"\"
```

If `app` is empty, the entire line is omitted.

## Menu Configuration

Customize the menu command in `config.toml`:

```toml
# Use rofi with custom theme
menu_command = "rofi -dmenu -p 'GPT' -theme ~/.config/rofi/clipboard.rasi"

# Use dmenu
menu_command = "dmenu -p 'ClipboardGPT'"

# Use wofi (Wayland)
menu_command = "wofi --dmenu --prompt 'ClipboardGPT'"
```