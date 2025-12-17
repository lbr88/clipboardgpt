"""TUI configuration manager for ClipboardGPT."""

import os
import tomllib

from textual.app import App, ComposeResult
from textual.containers import (
    Container,
    Horizontal,
    Vertical,
    VerticalScroll,
    Center,
    Middle,
)
from textual.widgets import (
    Header,
    Footer,
    Input,
    Label,
    Button,
    ListView,
    ListItem,
    TextArea,
)
from textual.screen import Screen

from clipboardgpt.constants import CONFIG_PATH, DEFAULT_PROMPTS


class ConfigModel:
    """Manages configuration data loading and saving."""

    def __init__(self):
        """Initialize the config model with empty data."""
        self.data: dict = {"prompts": {}}
        self._ensure_config_exists()
        self.load()

    def _ensure_config_exists(self):
        """Create config file with defaults if it doesn't exist."""
        if not os.path.exists(CONFIG_PATH):
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            self.data = {
                "openai_api_key": "",
                "name": "",
                "model": "gpt-4o",
                "menu_command": "rofi -dmenu -p 'ClipboardGPT'",
                "prompts": dict(DEFAULT_PROMPTS),
            }
            self.save()

    def load(self):
        """Load configuration from disk and ensure defaults exist."""
        added_defaults = False
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "rb") as f:
                    self.data = tomllib.load(f)
            except (OSError, tomllib.TOMLDecodeError):
                pass

        if "prompts" not in self.data:
            self.data["prompts"] = {}

        for key, value in DEFAULT_PROMPTS.items():
            if key not in self.data["prompts"]:
                self.data["prompts"][key] = value
                added_defaults = True

        if added_defaults:
            self.save()

    def save(self) -> tuple[bool, str]:
        """Save configuration to disk.

        Returns:
            Tuple of (success, message).
        """
        try:
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                if "openai_api_key" in self.data:
                    f.write(f'openai_api_key = "{self.data["openai_api_key"]}"\n')
                if "name" in self.data:
                    f.write(f'name = "{self.data["name"]}"\n')
                if "model" in self.data:
                    f.write(f'model = "{self.data["model"]}"\n')
                if "menu_command" in self.data:
                    f.write(f'menu_command = "{self.data["menu_command"]}"\n')

                for prompt_name, prompt_data in self.data.get("prompts", {}).items():
                    f.write(f"\n[prompts.{prompt_name}]\n")
                    if isinstance(prompt_data, dict):
                        if "system" in prompt_data:
                            safe = prompt_data["system"].replace('"""', '\\"\\"\\"')
                            f.write(f'system = """{safe}"""\n')
                        if "user" in prompt_data:
                            safe = prompt_data["user"].replace('"""', '\\"\\"\\"')
                            f.write(f'user = """{safe}"""\n')
                    else:
                        # Legacy format - just a string
                        safe = str(prompt_data).replace('"""', '\\"\\"\\"')
                        f.write(f'system = """{safe}"""\n')
                        f.write('user = "{text}"\n')

            return True, "Saved successfully"
        except OSError as e:
            return False, str(e)


class GeneralSettings(Container):
    """Container for general settings form."""

    def compose(self) -> ComposeResult:
        """Compose the general settings form."""
        with VerticalScroll():
            yield Label("OpenAI API Key")
            yield Input(placeholder="sk-...", id="api_key", password=True)
            yield Label("Your Name (used in prompt templates as {name})")
            yield Input(placeholder="John Doe", id="user_name")
            yield Label("Default Model")
            yield Input(placeholder="gpt-4o", id="model", value="gpt-4o")
            yield Label("Menu Command (for i3/rofi/dmenu)")
            yield Input(
                placeholder="rofi -dmenu -p 'ClipboardGPT'",
                id="menu_command",
            )
            yield Button("Save General Settings", variant="primary", id="save_general")
            yield Label("", id="status_general")

    def on_mount(self):
        """Load current values when mounted."""
        model = self.app.model  # type: ignore[attr-defined]
        self.query_one("#api_key", Input).value = model.data.get("openai_api_key", "")
        self.query_one("#user_name", Input).value = model.data.get("name", "")
        self.query_one("#model", Input).value = model.data.get("model", "gpt-4o")
        self.query_one("#menu_command", Input).value = model.data.get(
            "menu_command", "rofi -dmenu -p 'ClipboardGPT'"
        )

    def on_button_pressed(self, event: Button.Pressed):
        """Handle save button press."""
        if event.button.id == "save_general":
            model = self.app.model  # type: ignore[attr-defined]
            model.data["openai_api_key"] = self.query_one("#api_key", Input).value
            model.data["name"] = self.query_one("#user_name", Input).value
            model.data["model"] = self.query_one("#model", Input).value
            model.data["menu_command"] = self.query_one("#menu_command", Input).value
            _, msg = model.save()
            self.query_one("#status_general", Label).update(msg)


class PromptEditor(Container):
    """Container for prompt editing interface with system/user templates."""

    def __init__(self, model: ConfigModel):
        """Initialize with a config model.

        Args:
            model: The configuration model to edit.
        """
        super().__init__()
        self.current_prompt_key: str | None = None
        self.model = model

    def compose(self) -> ComposeResult:
        """Compose the prompt editor layout."""
        prompt_items = []
        for key in self.model.data.get("prompts", {}):
            item = ListItem(Label(key))
            item.prompt_key = key  # type: ignore[attr-defined]
            prompt_items.append(item)

        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("Prompts", id="prompts_header")
                yield ListView(*prompt_items, id="prompt_list")
                with Horizontal(id="sidebar_buttons"):
                    yield Button("New", id="new_prompt", variant="success")
                    yield Button("Delete", variant="error", id="delete_prompt")

            with Vertical(id="editor_area"):
                yield Label("Prompt Name", id="key_label")
                yield Input(placeholder="e.g. summarize", id="prompt_key")
                yield Label("System Prompt (instructions for the AI)")
                yield TextArea(id="system_prompt")
                yield Label("User Prompt Template")
                yield Label(
                    "Variables: {text} {context} {window_title} {app} {name} {datetime} {date} {time} {year}",
                    id="template_help",
                )
                yield Label(
                    "Conditional: {?var}line only if var is set",
                    id="template_help2",
                )
                yield TextArea(id="user_prompt")
                yield Button("Save Prompt", variant="primary", id="save_prompt")
                yield Label("", id="status_prompt")

    async def reload_prompts_list(self):
        """Reload the prompts list from the model."""
        list_view = self.query_one("#prompt_list", ListView)
        await list_view.clear()
        for key in self.model.data.get("prompts", {}):
            item = ListItem(Label(key))
            item.prompt_key = key  # type: ignore[attr-defined]
            await list_view.append(item)

    def _get_prompt_data(self, key: str) -> tuple[str, str]:
        """Get system and user prompts for a key."""
        prompt_data = self.model.data["prompts"].get(key, {})
        if isinstance(prompt_data, dict):
            return prompt_data.get("system", ""), prompt_data.get("user", "{text}")
        # Legacy string format
        return str(prompt_data), "{text}"

    def on_list_view_selected(self, event: ListView.Selected):
        """Handle prompt selection from list."""
        key = getattr(event.item, "prompt_key", None)
        if key is None:
            return
        self.current_prompt_key = key
        self.query_one("#prompt_key", Input).value = key
        self.query_one("#prompt_key", Input).disabled = True

        system_prompt, user_prompt = self._get_prompt_data(key)
        self.query_one("#system_prompt", TextArea).text = system_prompt
        self.query_one("#user_prompt", TextArea).text = user_prompt
        self.query_one("#status_prompt", Label).update(f"Loaded: {key}")

    async def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses for new, save, and delete."""
        if event.button.id == "new_prompt":
            self._handle_new_prompt()
        elif event.button.id == "save_prompt":
            await self._handle_save_prompt()
        elif event.button.id == "delete_prompt":
            await self._handle_delete_prompt()

    def _handle_new_prompt(self):
        """Clear form for new prompt entry."""
        self.current_prompt_key = None
        self.query_one("#prompt_key", Input).value = ""
        self.query_one("#prompt_key", Input).disabled = False
        self.query_one("#system_prompt", TextArea).text = ""
        self.query_one("#user_prompt", TextArea).text = "{text}"
        self.query_one("#prompt_key", Input).focus()
        self.query_one("#status_prompt", Label).update(
            "Enter prompt name and templates"
        )

    async def _handle_save_prompt(self):
        """Save the current prompt."""
        key = self.query_one("#prompt_key", Input).value.strip()
        system_text = self.query_one("#system_prompt", TextArea).text
        user_text = self.query_one("#user_prompt", TextArea).text

        if not key:
            self.query_one("#status_prompt", Label).update("Error: Name is required")
            return

        if self.current_prompt_key and self.current_prompt_key != key:
            if self.current_prompt_key in self.model.data["prompts"]:
                del self.model.data["prompts"][self.current_prompt_key]

        self.model.data["prompts"][key] = {
            "system": system_text,
            "user": user_text or "{text}",
        }
        _, msg = self.model.save()
        self.query_one("#status_prompt", Label).update(msg)
        await self.reload_prompts_list()
        self.current_prompt_key = key
        self.query_one("#prompt_key", Input).disabled = True

    async def _handle_delete_prompt(self):
        """Delete the currently selected prompt."""
        if (
            self.current_prompt_key
            and self.current_prompt_key in self.model.data["prompts"]
        ):
            del self.model.data["prompts"][self.current_prompt_key]
            self.model.save()
            await self.reload_prompts_list()
            self.query_one("#prompt_key", Input).value = ""
            self.query_one("#system_prompt", TextArea).text = ""
            self.query_one("#user_prompt", TextArea).text = "{text}"
            self.current_prompt_key = None
            self.query_one("#status_prompt", Label).update("Prompt deleted.")


class GeneralSettingsScreen(Screen):
    """Screen for general settings."""

    def compose(self) -> ComposeResult:
        """Compose the general settings screen."""
        yield Header()
        yield GeneralSettings()
        yield Button("Back to Menu", id="back", variant="default")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed):
        """Handle back button press."""
        if event.button.id == "back":
            self.app.pop_screen()


class PromptEditorScreen(Screen):
    """Screen for prompt editing."""

    def __init__(self, model: ConfigModel):
        """Initialize with config model.

        Args:
            model: The configuration model to edit.
        """
        super().__init__()
        self.model = model

    def compose(self) -> ComposeResult:
        """Compose the prompt editor screen."""
        yield Header()
        yield PromptEditor(self.model)
        yield Button("Back to Menu", id="back", variant="default")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed):
        """Handle back button press."""
        if event.button.id == "back":
            self.app.pop_screen()


class ClipboardGPTConfigApp(App):
    """Main TUI application for ClipboardGPT configuration."""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("g", "general", "General Settings"),
        ("p", "prompts", "Manage Prompts"),
    ]

    CSS = """
    Screen {
        layout: vertical;
    }

    #menu_title {
        text-align: center;
        text-style: bold;
        margin-bottom: 2;
        width: 100%;
    }

    Center {
        width: 100%;
        height: 1fr;
    }

    Middle {
        width: 100%;
        height: auto;
    }

    #btn_general, #btn_prompts, #btn_quit {
        width: 40;
        margin: 1;
    }

    GeneralSettings {
        padding: 2;
        height: 1fr;
    }

    GeneralSettings Input {
        margin-bottom: 2;
    }

    GeneralSettings Label {
        margin-bottom: 1;
        color: $text-muted;
    }

    PromptEditor {
        height: 1fr;
    }

    #sidebar {
        width: 25%;
        min-width: 15;
        height: 100%;
        min-height: 15;
        background: $surface;
        border-right: solid $primary;
        padding: 1;
    }

    #prompts_header {
        text-align: center;
        background: $primary;
        color: $text;
        padding: 1;
        width: 100%;
        margin-bottom: 1;
    }

    #sidebar_buttons {
        height: 3;
        margin-top: 1;
    }

    #sidebar_buttons Button {
        width: 1fr;
        margin-right: 1;
    }

    #editor_area {
        width: 75%;
        height: 100%;
        min-height: 15;
        padding: 1;
    }

    #editor_area Label {
        margin-top: 1;
        color: $text-muted;
    }

    #template_help, #template_help2 {
        color: $text-disabled;
        text-style: italic;
        margin-top: 0;
        margin-bottom: 1;
    }

    ListView {
        height: 1fr;
        min-height: 5;
        border: solid $secondary;
        margin-bottom: 1;
    }

    #system_prompt {
        height: 6;
        min-height: 4;
        margin-bottom: 1;
        border: solid $secondary;
    }

    #user_prompt {
        height: 8;
        min-height: 5;
        margin-bottom: 1;
        border: solid $secondary;
    }

    #prompt_key {
        margin-bottom: 1;
    }

    #status_general, #status_prompt {
        margin-top: 1;
        color: $success;
    }

    #back {
        dock: bottom;
        width: 100%;
        height: 3;
    }
    """

    def __init__(self):
        """Initialize the application with config model."""
        super().__init__()
        self.model = ConfigModel()

    def compose(self) -> ComposeResult:
        """Compose the main menu."""
        yield Header()
        with Center():
            with Middle():
                yield Label("ClipboardGPT Configuration", id="menu_title")
                yield Button("General Settings", id="btn_general", variant="primary")
                yield Button("Manage Prompts", id="btn_prompts", variant="primary")
                yield Button("Quit", id="btn_quit", variant="error")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed):
        """Handle main menu button presses."""
        if event.button.id == "btn_general":
            self.push_screen(GeneralSettingsScreen())
        elif event.button.id == "btn_prompts":
            self.push_screen(PromptEditorScreen(self.model))
        elif event.button.id == "btn_quit":
            self.exit()

    async def action_quit(self):
        """Quit the application."""
        self.exit()

    async def action_general(self):
        """Open general settings screen."""
        self.push_screen(GeneralSettingsScreen())

    async def action_prompts(self):
        """Open prompts editor screen."""
        self.push_screen(PromptEditorScreen(self.model))


def main():
    """Entry point for the TUI application."""
    app = ClipboardGPTConfigApp()
    app.run()


if __name__ == "__main__":
    main()
