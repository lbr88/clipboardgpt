#!/usr/bin/env python3
"""ClipboardGPT: A tool to process clipboard text using OpenAI's GPT models."""

import argparse
import logging
import os
import re
import subprocess
import sys
import tomllib
import warnings
from datetime import datetime
from typing import Any, Optional

from openai import OpenAI

# Suppress plyer dbus warning on Linux - must be before plyer import
warnings.filterwarnings("ignore", message="The Python dbus package is not installed")

from plyer import notification  # noqa: E402 pylint: disable=wrong-import-position
import pyperclip  # noqa: E402 pylint: disable=wrong-import-position

# pylint: disable=wrong-import-position
from clipboardgpt.constants import CONFIG_PATH, DEFAULT_PROMPTS

# pylint: enable=wrong-import-position


def _load_config() -> dict[str, Any]:
    """Load configuration from file."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "rb") as file:
                return tomllib.load(file)
        except (OSError, tomllib.TOMLDecodeError) as err:
            print(f"Warning: Failed to load config file at {CONFIG_PATH}: {err}")
    return {}


def _save_config(config_data: dict[str, Any]) -> None:
    """Save configuration to file."""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as file:
        if "openai_api_key" in config_data:
            file.write(f'openai_api_key = "{config_data["openai_api_key"]}"\n')
        if "name" in config_data:
            file.write(f'name = "{config_data["name"]}"\n')
        if "model" in config_data:
            file.write(f'model = "{config_data["model"]}"\n')
        if "menu_command" in config_data:
            file.write(f'menu_command = "{config_data["menu_command"]}"\n')

        if "prompts" in config_data:
            for prompt_name, prompt_data in config_data["prompts"].items():
                file.write(f"\n[prompts.{prompt_name}]\n")
                if isinstance(prompt_data, dict):
                    if "system" in prompt_data:
                        safe = prompt_data["system"].replace('"""', '\\"\\"\\"')
                        file.write(f'system = """{safe}"""\n')
                    if "user" in prompt_data:
                        safe = prompt_data["user"].replace('"""', '\\"\\"\\"')
                        file.write(f'user = """{safe}"""\n')
                else:
                    # Legacy format - just a string
                    safe = str(prompt_data).replace('"""', '\\"\\"\\"')
                    file.write(f'system = """{safe}"""\n')
                    file.write('user = "{text}"\n')


def _migrate_legacy_env() -> None:
    """Migrate legacy .env files to config.toml."""
    if os.path.exists(CONFIG_PATH):
        return

    found_path, env_vars = _find_legacy_env_file()
    if not found_path or not env_vars:
        return

    print(f"Migrating legacy configuration from {found_path} to {CONFIG_PATH}...")
    try:
        new_config: dict[str, Any] = {"prompts": {}}
        if "OPENAI_API_KEY" in env_vars:
            new_config["openai_api_key"] = env_vars["OPENAI_API_KEY"]
        if "NAME" in env_vars:
            new_config["name"] = env_vars["NAME"]
        if "MODEL" in env_vars:
            new_config["model"] = env_vars["MODEL"]
        _save_config(new_config)
        print("Migration successful.")
    except OSError as err:
        print(f"Migration failed: {err}")


def _migrate_legacy_prompts(config: dict[str, Any]) -> bool:
    """Migrate legacy prompt format (string) to new format (dict with system/user).

    Args:
        config: The loaded configuration.

    Returns:
        True if migration was performed, False otherwise.
    """
    prompts = config.get("prompts", {})
    if not prompts:
        return False

    migrated = False
    for prompt_name, prompt_data in prompts.items():
        if isinstance(prompt_data, str):
            # Legacy format: string is the system prompt
            prompts[prompt_name] = {
                "system": prompt_data,
                "user": "{text}",
            }
            migrated = True

    if migrated:
        print("Migrating legacy prompt format to new system/user format...")
        _save_config(config)
        print("Prompt migration successful.")

    return migrated


def _reset_default_prompts(config: dict[str, Any]) -> None:
    """Reset default prompts to latest versions.

    Updates the config file with the latest default prompts while preserving
    custom prompts and other settings.

    Args:
        config: The current configuration.
    """
    if "prompts" not in config:
        config["prompts"] = {}

    updated = []
    for prompt_name, prompt_data in DEFAULT_PROMPTS.items():
        config["prompts"][prompt_name] = prompt_data
        updated.append(prompt_name)

    _save_config(config)
    print(f"Reset default prompts: {', '.join(updated)}")
    print("Custom prompts have been preserved.")


def _find_legacy_env_file() -> tuple[Optional[str], dict[str, str]]:
    """Find and parse legacy .env file if it exists."""
    package_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(package_dir))

    env_locations = [
        os.path.join(os.getcwd(), ".env"),
        os.path.expanduser("~/.config/clipboardgpt/.env"),
        os.path.join(repo_root, ".env"),
    ]

    for env_path in env_locations:
        if os.path.exists(env_path):
            env_vars = _parse_env_file(env_path)
            if env_vars:
                return env_path, env_vars
    return None, {}


def _parse_env_file(env_path: str) -> dict[str, str]:
    """Parse a .env file and return key-value pairs."""
    env_vars: dict[str, str] = {}
    try:
        with open(env_path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    return env_vars


def _setup_logging() -> None:
    """Configure logging to file and console."""
    home = os.path.expanduser("~")
    log_dir = os.path.join(home, "log")
    os.makedirs(log_dir, exist_ok=True)
    logfile = os.path.join(log_dir, "clipboardgpt.log")

    file_handler = logging.FileHandler(logfile, mode="a")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, console_handler])

    # Silence noisy libraries
    for lib in ("openai", "httpx", "httpcore"):
        logging.getLogger(lib).setLevel(logging.WARNING)


# --- Template Engine (imported from utils for shared access) ---

from clipboardgpt.utils import (
    render_template,
)  # noqa: E402 pylint: disable=wrong-import-position


# --- Menu System ---


def show_menu(options: list[str], config: dict[str, Any]) -> Optional[str]:
    """Show a menu using rofi or dmenu and return selected option.

    Args:
        options: List of options to display.
        config: App configuration (may contain menu_command).

    Returns:
        Selected option or None if cancelled.
    """
    menu_cmd = config.get("menu_command", "rofi -dmenu -p 'ClipboardGPT'")

    # Try rofi first, fall back to dmenu
    if "rofi" in menu_cmd:
        if not _command_exists("rofi"):
            menu_cmd = "dmenu -p 'ClipboardGPT'"

    if "dmenu" in menu_cmd and not _command_exists("dmenu"):
        logging.getLogger("ClipboardGPT").error(
            "Neither rofi nor dmenu found. Install one or set menu_command in config."
        )
        return None

    try:
        result = subprocess.run(
            menu_cmd,
            shell=True,
            input="\n".join(options),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except OSError as err:
        logging.getLogger("ClipboardGPT").error("Menu command failed: %s", err)

    return None


def _command_exists(cmd: str) -> bool:
    """Check if a command exists in PATH."""
    try:
        subprocess.run(
            ["which", cmd], capture_output=True, check=True  # noqa: S603 S607
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_available_prompts(config: dict[str, Any]) -> list[str]:
    """Get list of available prompt types from config and defaults.

    Args:
        config: App configuration.

    Returns:
        List of prompt type names.
    """
    prompts: set[str] = set()

    # Add from config
    config_prompts = config.get("prompts", {})
    prompts.update(config_prompts.keys())

    # Add defaults
    prompts.update(DEFAULT_PROMPTS.keys())

    return sorted(prompts)


# --- Prompt Resolution ---


def get_prompt_templates(prompt_type: str, config: dict[str, Any]) -> tuple[str, str]:
    """Get system and user templates for a prompt type.

    Args:
        prompt_type: The prompt type name.
        config: App configuration.

    Returns:
        Tuple of (system_template, user_template).

    Raises:
        ValueError: If prompt type not found.
    """
    # Check config first
    config_prompts = config.get("prompts", {})
    if prompt_type in config_prompts:
        prompt_data = config_prompts[prompt_type]
        if isinstance(prompt_data, dict):
            return (
                prompt_data.get("system", ""),
                prompt_data.get("user", "{text}"),
            )
        # Legacy format - string is system prompt
        return str(prompt_data), "{text}"

    # Check defaults
    if prompt_type in DEFAULT_PROMPTS:
        prompt_data = DEFAULT_PROMPTS[prompt_type]
        return prompt_data["system"], prompt_data["user"]

    raise ValueError(
        f"Prompt type '{prompt_type}' not found. "
        f"Available: {', '.join(get_available_prompts(config))}"
    )


# --- Main Class ---


class ClipboardGPT:  # pylint: disable=too-many-instance-attributes
    """Main class for ClipboardGPT functionality."""

    def __init__(self, handler_type: str, app_config: Optional[dict[str, Any]] = None):
        """Initialize ClipboardGPT.

        Args:
            handler_type: Type of handler (grammar, reply, or custom).
            app_config: Configuration dictionary.
        """
        self.type = handler_type
        self.config = app_config or {}
        self.model = self.config.get("model", "gpt-4o")
        self.app_name = f"{handler_type.capitalize()}GPT"
        self.logger = logging.getLogger(f"{self.app_name}.{self.__class__.__name__}")

        # Get templates
        self.system_template, self.user_template = get_prompt_templates(
            handler_type, self.config
        )

        api_key = os.getenv("OPENAI_API_KEY") or self.config.get("openai_api_key")
        if api_key:
            self.client: Optional[OpenAI] = OpenAI(api_key=api_key, timeout=30.0)
        else:
            self.client = None

    def get_selected_text(self) -> str:
        """Get selected text using xsel or xclip."""
        self.logger.debug("Getting selected text")
        text = self._try_xsel() or self._try_xclip()
        return text

    def _try_xsel(self) -> str:
        """Try to get selected text using xsel."""
        try:
            self.logger.debug("Trying xsel")
            result = subprocess.run(
                ["xsel", "-o"], stdout=subprocess.PIPE, text=True, check=False
            )
            if result.stdout:
                self.logger.debug("xsel returned: %s...", result.stdout[:50])
            return result.stdout.strip()
        except FileNotFoundError:
            self.logger.debug("xsel not found")
            return ""

    def _try_xclip(self) -> str:
        """Try to get selected text using xclip."""
        try:
            self.logger.debug("Trying xclip")
            result = subprocess.run(
                ["xclip", "-out", "-selection", "primary"],
                stdout=subprocess.PIPE,
                text=True,
                check=False,
            )
            if result.stdout:
                self.logger.debug("xclip returned: %s...", result.stdout[:50])
            return result.stdout.strip()
        except FileNotFoundError:
            self.logger.error("Neither xsel nor xclip found")
            return ""

    def get_window_info(self) -> tuple[str, str]:
        """Get active window title and detected app type.

        Returns:
            Tuple of (window_title, app_type).
        """
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                stdout=subprocess.PIPE,
                text=True,
                check=False,
            )
            window_title = result.stdout.strip()
        except FileNotFoundError:
            self.logger.warning("xdotool not found")
            return "", "unknown"

        self.logger.debug("Window title: %s", window_title)
        return window_title, self._detect_app_type(window_title)

    def _detect_app_type(self, window_title: str) -> str:
        """Detect application type from window title."""
        chat_names = (
            "teams",
            "mattermost",
            "slack",
            "discord",
            "whatsapp",
            "signal",
            "telegram",
            "zoom",
            "linkedin",
            "msteams",
            "skype",
            "irc",
            "irccloud",
            "element",
            "matrix",
            "rocketchat",
            "zulip",
            "gitter",
        )
        email_names = (
            "gmail",
            "outlook",
            "thunderbird",
            "evolution",
            "kmail",
            "mail",
            "email",
            "protonmail",
            "fastmail",
            "mutt",
            "neomutt",
            "aerc",
        )
        terminal_names = (
            "terminal",
            "konsole",
            "gnome-terminal",
            "xterm",
            "urxvt",
            "rxvt",
            "alacritty",
            "kitty",
            "terminator",
            "tilix",
            "st",
            "foot",
            "wezterm",
            "hyper",
            "iterm",
            "tmux",
            "screen",
            "zsh",
            "bash",
            "fish",
        )
        browser_names = (
            "firefox",
            "chrome",
            "chromium",
            "brave",
            "vivaldi",
            "opera",
            "edge",
            "safari",
            "qutebrowser",
        )
        editor_names = (
            "code",
            "vscode",
            "visual studio code",
            "vim",
            "nvim",
            "neovim",
            "emacs",
            "sublime",
            "atom",
            "jetbrains",
            "intellij",
            "pycharm",
            "webstorm",
            "goland",
            "rider",
            "clion",
            "phpstorm",
            "rubymine",
            "notepad",
            "gedit",
            "kate",
        )

        window_lower = window_title.lower()
        for name in chat_names:
            if name in window_lower:
                return "chat"
        for name in email_names:
            if name in window_lower:
                return "email"
        for name in terminal_names:
            if name in window_lower:
                return "terminal"
        for name in editor_names:
            if name in window_lower:
                return "editor"
        for name in browser_names:
            if name in window_lower:
                return "browser"
        return "unknown"

    def build_prompts(self, text: str, context: str = "") -> tuple[str, str]:
        """Build system and user prompts using templates.

        Args:
            text: The selected text.
            context: Optional context string.

        Returns:
            Tuple of (system_prompt, user_prompt).
        """
        window_title, app_type = self.get_window_info()

        # Build variable dictionary
        now = datetime.now()
        variables = {
            "text": text,
            "context": context,
            "window_title": window_title,
            "app": app_type if app_type != "unknown" else "",
            "name": self.config.get("name", ""),
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "year": now.strftime("%Y"),
        }

        system_prompt = render_template(self.system_template, variables)
        user_prompt = render_template(self.user_template, variables)

        return system_prompt, user_prompt

    def get_gpt_response(
        self,
        user_prompt: str,
        system_prompt: str,
        model: Optional[str] = None,
    ) -> Optional[str]:
        """Get response from GPT.

        Args:
            user_prompt: The user prompt.
            system_prompt: The system prompt.
            model: Model to use (optional).

        Returns:
            The GPT response or None.

        Raises:
            ValueError: If client is not initialized.
        """
        model = model or self.model

        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        if not self.client:
            raise ValueError("OpenAI Client not initialized. Check API Key.")

        self.logger.debug("Sending request to OpenAI model: %s", model)
        try:
            response = self.client.chat.completions.create(
                model=model, messages=messages  # type: ignore
            )
            self.logger.debug("Received response from OpenAI")
            return response.choices[0].message.content
        except Exception as err:  # pylint: disable=broad-exception-caught
            self.logger.error("Error calling OpenAI: %s", err)
            raise

    def show_notification(self, message: str, timeout: int = 5) -> None:
        """Show desktop notification."""
        self.logger.debug("Showing notification: %s", message[:50])
        notification.notify(  # type: ignore
            title=self.app_name,
            message=message,
            app_name=self.app_name,
            timeout=timeout,
        )


# --- Main Entry Point ---


def _create_arg_parser() -> argparse.ArgumentParser:
    """Create and return the argument parser."""
    parser = argparse.ArgumentParser(description="Process text with GPT")
    parser.add_argument(
        "--type",
        "-t",
        default=None,
        help="Prompt type (grammar, reply, or custom). Shows menu if not specified.",
    )
    parser.add_argument(
        "--context",
        "-c",
        type=str,
        default="",
        help="Additional context for the prompt",
    )
    parser.add_argument(
        "--model",
        "-m",
        default=None,
        help="Model to use (default: from config or gpt-4o)",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List available prompt types and exit",
    )
    parser.add_argument(
        "--menu",
        action="store_true",
        help="Show menu to select prompt type (default when --type not given)",
    )
    parser.add_argument(
        "--reset-prompts",
        action="store_true",
        help="Reset default prompts to latest versions and exit",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run AI-evaluated tests on prompts and exit",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output (use with --test)",
    )
    return parser


def _handle_error(err: Exception) -> None:
    """Handle and notify about errors."""
    logging.getLogger("ClipboardGPT").exception("Unhandled exception:")
    try:
        notification.notify(  # type: ignore[misc]
            title="ClipboardGPT Error",
            message=str(err),
            app_name="ClipboardGPT",
            timeout=10,
        )
    except Exception:  # pylint: disable=broad-exception-caught
        pass


def main(  # pylint: disable=too-many-locals
    args_list: Optional[list[str]] = None,
) -> None:
    """Main entry point."""
    _migrate_legacy_env()
    _setup_logging()
    logger = logging.getLogger("ClipboardGPT")

    app_config = _load_config()
    _migrate_legacy_prompts(app_config)
    api_key = os.getenv("OPENAI_API_KEY") or app_config.get("openai_api_key")

    parser = _create_arg_parser()
    args = parser.parse_args(args_list)

    # Handle --list
    if args.list:
        prompts = get_available_prompts(app_config)
        print("Available prompt types:")
        for prompt_type in prompts:
            print(f"  - {prompt_type}")
        return

    # Handle --reset-prompts
    if args.reset_prompts:
        _reset_default_prompts(app_config)
        return

    # Handle --test
    if args.test:
        # pylint: disable=import-outside-toplevel
        from clipboardgpt.test_prompts import run_tests

        sys.exit(run_tests(app_config, verbose=args.verbose))

    # Check API key
    if not api_key:
        print("Error: OPENAI_API_KEY not found.")
        print("Please set it in your environment or run clipboardgpt-config.")
        sys.exit(1)

    # Determine prompt type - show menu if not specified
    prompt_type = args.type
    if prompt_type is None or args.menu:
        available = get_available_prompts(app_config)
        prompt_type = show_menu(available, app_config)
        if not prompt_type:
            logger.info("No prompt type selected, exiting")
            return

    try:
        gpt = ClipboardGPT(prompt_type, app_config=app_config)
        logger.info("Using prompt type: %s", prompt_type)

        text = gpt.get_selected_text()
        if not text:
            logger.warning("No text selected")
            gpt.show_notification("No text selected", timeout=3)
            return

        logger.debug("Got text length: %d", len(text))

        # Build prompts using templates
        system_prompt, user_prompt = gpt.build_prompts(text, args.context)
        logger.debug(
            "System prompt: %s...", system_prompt[:100] if system_prompt else ""
        )
        logger.debug("User prompt: %s...", user_prompt[:100])

        # Get model
        model = args.model or app_config.get("model", "gpt-4o")

        # Process
        gpt.show_notification(f"Processing with {model}...", timeout=3)
        response = gpt.get_gpt_response(user_prompt, system_prompt, model)

        if response:
            logger.debug("Got response length: %d", len(response))
            gpt.show_notification(response)
            pyperclip.copy(response)
            logger.debug("Copied to clipboard")

    except Exception as err:  # pylint: disable=broad-exception-caught
        _handle_error(err)
        raise


if __name__ == "__main__":
    main()
