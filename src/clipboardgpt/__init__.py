#!/usr/bin/env python3
"""ClipboardGPT: A tool to process clipboard text using OpenAI's GPT models."""

import argparse
import logging
import os
import subprocess
import sys
import tomllib
import warnings
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


def _find_legacy_env_file() -> tuple[Optional[str], dict[str, str]]:
    """Find and parse legacy .env file if it exists.

    Returns:
        Tuple of (path_found, env_vars_dict).
    """
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

        file.write("\n[prompts]\n")
        for key, value in config_data.get("prompts", {}).items():
            safe_v = value.replace('"""', '\\"\\"\\"')
            file.write(f'{key} = """{safe_v}"""\n')


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


def _setup_logging() -> None:
    """Configure logging to file and console."""
    home = os.path.expanduser("~")
    log_dir = os.path.join(home, "log")
    os.makedirs(log_dir, exist_ok=True)
    logfile = os.path.join(log_dir, "replygpt.log")

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


class ClipboardGPT:
    """Main class for ClipboardGPT functionality."""

    def __init__(self, handler_type: str, app_config: Optional[dict[str, Any]] = None):
        """Initialize ClipboardGPT.

        Args:
            handler_type: Type of handler (grammar, reply, or custom).
            app_config: Configuration dictionary.
        """
        self.type = handler_type
        self.config = app_config or {}
        self.model = "gpt-4o"
        self.app_name = f"{handler_type.capitalize()}GPT"
        self.logger = logging.getLogger(f"{self.app_name}.{self.__class__.__name__}")
        self.system_prompt = self._get_system_prompt(handler_type)

        api_key = os.getenv("OPENAI_API_KEY") or self.config.get("openai_api_key")
        if api_key:
            self.client: Optional[OpenAI] = OpenAI(api_key=api_key, timeout=30.0)
        else:
            self.client = None

    def _get_system_prompt(self, handler_type: str) -> str:
        """Get system prompt based on handler type."""
        prompts = self.config.get("prompts", {})
        if handler_type in prompts:
            return prompts[handler_type]

        if handler_type in DEFAULT_PROMPTS:
            return DEFAULT_PROMPTS[handler_type]

        raise ValueError(
            f"Handler type '{handler_type}' not found in config [prompts]. "
            "Please run clipboardgpt-config to add it."
        )

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
            print("Error: 'xsel' or 'xclip' not found.")
            print("Please install one of them to use the selection feature.")
            print("  sudo apt install xsel")
            print("  or")
            print("  sudo apt install xclip")
            sys.exit(1)

    def get_clipboard_text(self) -> str:
        """Get text from clipboard."""
        return pyperclip.paste()

    def set_model(self, model: str) -> None:
        """Set the GPT model to use."""
        if not model.startswith("gpt-"):
            raise ValueError("Model must start with gpt-")
        self.model = model

    def get_gpt_response(
        self,
        prompt: str,
        model: Optional[str] = None,
        systemprompt: Optional[str] = None,
    ) -> Optional[str]:
        """Get response from GPT.

        Args:
            prompt: The user prompt.
            model: Model to use (optional).
            systemprompt: System prompt override (optional).

        Returns:
            The GPT response or None.

        Raises:
            ValueError: If client is not initialized.
        """
        systemprompt = systemprompt or self.system_prompt
        model = model or self.model

        messages: list[dict[str, Any]] = []
        if systemprompt:
            messages.append({"role": "system", "content": systemprompt})
        messages.append({"role": "user", "content": prompt})

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
        self.logger.debug("Showing notification: %s", message)
        notification.notify(  # type: ignore
            title=self.app_name,
            message=message,
            app_name=self.app_name,
            timeout=timeout,
        )
        self.logger.debug("Notification function returned")

    def get_title_and_medium_from_active_window(self) -> tuple[str, str]:
        """Get medium (email, chat, etc) from the active window title using xdotool."""
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                stdout=subprocess.PIPE,
                text=True,
                check=False,
            )
            window_title = result.stdout
        except FileNotFoundError:
            self.logger.warning("xdotool not found, cannot detect window title")
            return "", "unknown"

        self.logger.debug("title: %s", window_title)
        return window_title, self._detect_medium(window_title)

    def _detect_medium(self, window_title: str) -> str:
        """Detect medium type from window title."""
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
        )
        email_names = (
            "gmail",
            "outlook",
            "thunderbird",
            "evolution",
            "kmail",
            "mail",
            "email",
        )

        window_lower = window_title.lower()
        for name in chat_names:
            if name in window_lower:
                return "chat"
        for name in email_names:
            if name in window_lower:
                return "email"
        return "unknown"


def _create_arg_parser() -> argparse.ArgumentParser:
    """Create and return the argument parser."""
    parser = argparse.ArgumentParser(description="Get GPT Response")
    parser.add_argument(
        "--type",
        default="grammar",
        help="Type of response (grammar, reply, or custom key in config)",
    )
    parser.add_argument(
        "--context",
        type=str,
        default="",
        help="Context of conversation",
    )
    parser.add_argument(
        "--model",
        choices=["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
        default="gpt-4o",
        help="Model to use",
    )
    return parser


def _build_prompt(text: str, title: str, medium: str, context: str) -> str:
    """Build the full prompt from components."""
    prompt_parts: list[str] = []
    if medium in ("chat", "email"):
        prompt_parts.append(f"medium: {medium}")
        prompt_parts.append(f"window name: {title}")
    if context:
        prompt_parts.append(f"context: {context}")
    prompt_parts.append(f"text (retain original language): {text}")
    return "\n".join(prompt_parts)


def _format_system_prompt(
    gpt_instance: ClipboardGPT,
    app_config: dict[str, Any],
    text: str,
    title: str,
    medium: str,
) -> None:
    """Format system prompt with variables if available."""
    try:
        gpt_instance.system_prompt = gpt_instance.system_prompt.format(
            name=app_config.get("name", ""),
            medium=medium,
            window_title=title,
            clipboard_text=text,
        )
    except KeyError:
        pass


def _process_text(
    gpt_instance: ClipboardGPT,
    full_prompt: str,
    model: str,
) -> None:
    """Process text and copy response to clipboard."""
    gpt_instance.logger.debug("Showing waiting notification")
    gpt_instance.show_notification(f"waiting on chatgpt ({model})...", timeout=3)
    gpt_instance.logger.debug("Calling get_gpt_response")

    gpt_response = gpt_instance.get_gpt_response(full_prompt, model)
    response_len = len(gpt_response) if gpt_response else 0
    gpt_instance.logger.debug("Got response length: %d", response_len)

    gpt_instance.logger.debug("Showing response notification")
    gpt_instance.show_notification(str(gpt_response))

    if gpt_response:
        gpt_instance.logger.debug("Copying to clipboard")
        pyperclip.copy(gpt_response)
        gpt_instance.logger.debug("Copied to clipboard")


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


def main(args_list: Optional[list[str]] = None) -> None:
    """Main entry point."""
    _migrate_legacy_env()
    _setup_logging()

    app_config = _load_config()
    api_key = os.getenv("OPENAI_API_KEY") or app_config.get("openai_api_key")

    parser = _create_arg_parser()
    args = parser.parse_args(args_list)

    if not api_key:
        print("Error: OPENAI_API_KEY not found.")
        print("Please set it in your environment or run clipboardgpt-config.")
        sys.exit(1)

    try:
        gpt_instance = ClipboardGPT(args.type, app_config=app_config)
        gpt_instance.logger.info("Starting main with args: %s", args)

        text = gpt_instance.get_selected_text()
        gpt_instance.logger.debug("Got text length: %d", len(text))

        title, medium = gpt_instance.get_title_and_medium_from_active_window()
        _format_system_prompt(gpt_instance, app_config, text, title, medium)
        full_prompt = _build_prompt(text, title, medium, args.context)

        if text:
            _process_text(gpt_instance, full_prompt, args.model)

    except Exception as err:  # pylint: disable=broad-exception-caught
        _handle_error(err)
        raise


if __name__ == "__main__":
    main()
