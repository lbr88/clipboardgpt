# Clipboard gpt
This tool is a simple clipboard manager that uses the Openai API to generate text based on the clipboard content.
## Demo
![Demo](https://raw.githubusercontent.com/lbr88/clipboardgpt/main/clipboardgpt-demo.gif)
## Prerequisites
- [uv](https://github.com/astral-sh/uv)
- `xsel` or `xclip` (for clipboard access)
- `xdotool` (for window title detection)

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

3. Configuration:
   The tool uses `~/.config/clipboardgpt/config.toml`.

   **Interactive Setup (Recommended):**
   Run the setup wizard to create your configuration file:
   ```bash
   grammargpt --setup
   ```
   
   **Automatic Migration:** If you have an old `.env` file, simply run `grammargpt` or `replygpt` once, and it will automatically migrate your settings to the new config file.

   **Manual Configuration:** Create `~/.config/clipboardgpt/config.toml`:
   ```toml
   openai_api_key = "your_openai_api_key"
   name = "your_name" # used for the replygpt to know who is talking
   model = "gpt-4o" # the model to use
   ```

4. Configure shortcuts in i3 or your window manager:
   ```config
   bindsym $mod+Ctrl+c exec replygpt
   bindsym $mod+c exec grammargpt
   ```

## Usage
1. Mark some text you want to reply to or grammar check
2. Press the shortcut from step 4 in the installation
3. Wait for the tooltip to appear with the generated text
4. The generated text is now copied to the clipboard
5. Paste the generated text