#!/usr/bin/env python3
"""
ClipboardGPT: A tool to process clipboard text using OpenAI's GPT models.
"""
import os
import sys
import argparse
import subprocess
import logging
import tomllib
from typing import Optional, Tuple, List, Dict, Any
from openai import OpenAI
import warnings

# Suppress plyer dbus warning on Linux
warnings.filterwarnings("ignore", message="The Python dbus package is not installed")
from plyer import notification
import pyperclip

# Load configuration
# Priority:
# 1. Environment variables
# 2. ~/.config/clipboardgpt/config.toml
# 3. Defaults

CONFIG_PATH = os.path.expanduser("~/.config/clipboardgpt/config.toml")


def config_manager_main():
    """Interactive configuration manager"""
    print(f"ClipboardGPT Configuration Manager")
    print(f"Config file: {CONFIG_PATH}")

    while True:
        # Reload config
        current_config = {}
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "rb") as f:
                    current_config = tomllib.load(f)
            except Exception:
                pass

        print("\n--- Main Menu ---")
        print("1. Edit General Settings (API Key, Name, Model)")
        print("2. Manage Prompts")
        print("3. Exit")

        choice = input("Select an option: ").strip()

        if choice == "1":
            setup_config()
        elif choice == "2":
            manage_prompts(current_config)
        elif choice == "3":
            sys.exit(0)
        else:
            print("Invalid option.")


def manage_prompts(current_config):
    """Sub-menu for managing prompts"""
    while True:
        prompts = current_config.get("prompts", {})
        print("\n--- Manage Prompts ---")
        print("1. List Prompts")
        print("2. Add New Prompt")
        print("3. Edit Existing Prompt")
        print("4. Delete Prompt")
        print("5. Back to Main Menu")

        choice = input("Select an option: ").strip()

        if choice == "1":
            print("\nCurrent Prompts:")
            for k, v in prompts.items():
                print(f"  - {k}: {v[:50]}..." if len(v) > 50 else f"  - {k}: {v}")

        elif choice == "2":
            key = input("Enter new prompt key (e.g., 'summarize'): ").strip()
            if not key:
                print("Key cannot be empty.")
                continue
            if key in prompts:
                print(f"Prompt '{key}' already exists. Use Edit instead.")
                continue

            print("Enter prompt text (press Enter twice to finish):")
            lines = []
            while True:
                line = input()
                if not line and lines and not lines[-1]:
                    break
                lines.append(line)
            value = "\n".join(lines).strip()

            prompts[key] = value
            save_prompts(current_config, prompts)
            print(f"Prompt '{key}' added.")

        elif choice == "3":
            key = input("Enter prompt key to edit: ").strip()
            if key not in prompts:
                print(f"Prompt '{key}' not found.")
                continue

            print(f"Current text for '{key}':")
            print(prompts[key])
            print(
                "\nEnter new text (press Enter twice to finish, or just Enter to keep current):"
            )
            lines = []
            while True:
                line = input()
                if not line and lines and not lines[-1]:
                    break
                lines.append(line)
            value = "\n".join(lines).strip()

            if value:
                prompts[key] = value
                save_prompts(current_config, prompts)
                print(f"Prompt '{key}' updated.")
            else:
                print("No changes made.")

        elif choice == "4":
            key = input("Enter prompt key to delete: ").strip()
            if key not in prompts:
                print(f"Prompt '{key}' not found.")
                continue

            confirm = input(f"Are you sure you want to delete '{key}'? (y/N): ").lower()
            if confirm == "y":
                del prompts[key]
                save_prompts(current_config, prompts)
                print(f"Prompt '{key}' deleted.")

        elif choice == "5":
            break


def save_prompts(config_data, prompts):
    """Helper to save prompts back to config file"""
    # Update the config object
    config_data["prompts"] = prompts

    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            # Write general settings
            if "openai_api_key" in config_data:
                f.write(f'openai_api_key = "{config_data["openai_api_key"]}"\n')
            if "name" in config_data:
                f.write(f'name = "{config_data["name"]}"\n')
            if "model" in config_data:
                f.write(f'model = "{config_data["model"]}"\n')

            # Write prompts
            f.write("\n[prompts]\n")
            for k, v in prompts.items():
                # Escape triple quotes if necessary, though simple replacement is usually enough for config files
                safe_v = v.replace('"""', '\\"\\"\\"')
                f.write(f'{k} = """{safe_v}"""\n')

    except Exception as e:
        print(f"Failed to save config: {e}")


def setup_config():
    """Interactive configuration setup"""
    print(f"Setting up configuration at {CONFIG_PATH}")

    existing_config = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "rb") as f:
                existing_config = tomllib.load(f)
        except Exception:
            pass

    # Get existing values
    default_api_key = existing_config.get("openai_api_key", "")
    default_name = existing_config.get("name", "")
    default_model = existing_config.get("model", "gpt-4o")

    # Mask API key for display
    if default_api_key and len(default_api_key) > 8:
        display_key = f"{default_api_key[:4]}...{default_api_key[-4:]}"
    else:
        display_key = default_api_key

    # API Key
    prompt_key = (
        f"Enter your OpenAI API Key [{display_key}]: "
        if display_key
        else "Enter your OpenAI API Key: "
    )
    api_key = input(prompt_key).strip()
    if not api_key:
        if default_api_key:
            api_key = default_api_key
        else:
            print("API Key is required.")
            sys.exit(1)

    # Name
    prompt_name = f"Enter your Name (for ReplyGPT context) [{default_name}]: "
    name = input(prompt_name).strip()
    if not name:
        name = default_name

    # Model
    prompt_model = f"Enter Model [{default_model}]: "
    model = input(prompt_model).strip()
    if not model:
        model = default_model

    # Prompts
    prompts = existing_config.get("prompts", {})
    default_grammar = prompts.get(
        "grammar",
        "Fix grammar in the following text in the language that is is provided and rewrite it to make more sense if it is too confusing. REPLY ONLY with the improved text and nothing else:",
    )
    default_reply = prompts.get(
        "reply",
        "Write a response to the following message. Reply ONLY with the response and nothing else in the original language:",
    )

    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(f'openai_api_key = "{api_key}"\n')
            if name:
                f.write(f'name = "{name}"\n')
            f.write(f'model = "{model}"\n')

            f.write("\n[prompts]\n")
            f.write(f'grammar = """{default_grammar}"""\n')
            f.write(f'reply = """{default_reply}"""\n')

            # Preserve custom prompts
            for k, v in prompts.items():
                if k not in ["grammar", "reply"]:
                    f.write(f'{k} = """{v}"""\n')

        print(f"Configuration saved to {CONFIG_PATH}")
        print("You can now run clipboardgpt.")
    except Exception as e:
        print(f"Failed to write config: {e}")
        sys.exit(1)
    sys.exit(0)


def migrate_legacy_env():
    """Migrate legacy .env files to config.toml"""
    config_dir = os.path.dirname(CONFIG_PATH)
    if os.path.exists(CONFIG_PATH):
        return

    package_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(package_dir))

    env_locations = [
        os.path.join(os.getcwd(), ".env"),
        os.path.expanduser("~/.config/clipboardgpt/.env"),
        os.path.join(repo_root, ".env"),
    ]

    env_vars = {}
    found_path = None

    for env_path in env_locations:
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            env_vars[key] = value
                found_path = env_path
                break
            except Exception:
                continue

    if found_path and env_vars:
        print(f"Migrating legacy configuration from {found_path} to {CONFIG_PATH}...")
        os.makedirs(config_dir, exist_ok=True)
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                if "OPENAI_API_KEY" in env_vars:
                    f.write(f'openai_api_key = "{env_vars["OPENAI_API_KEY"]}"\n')
                if "NAME" in env_vars:
                    f.write(f'name = "{env_vars["NAME"]}"\n')
                if "MODEL" in env_vars:
                    f.write(f'model = "{env_vars["MODEL"]}"\n')
            print("Migration successful.")
        except Exception as e:
            print(f"Migration failed: {e}")


migrate_legacy_env()
config = {}

if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, "rb") as f:
            config = tomllib.load(f)
    except Exception as e:
        print(f"Warning: Failed to load config file at {CONFIG_PATH}: {e}")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or config.get("openai_api_key")

# get home dir
home = os.path.expanduser("~")
log_dir = os.path.join(home, "log")
os.makedirs(log_dir, exist_ok=True)
logfile = os.path.join(log_dir, "replygpt.log")

# log to file and to console
# File handler gets DEBUG logs
file_handler = logging.FileHandler(logfile, mode="a")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)

# Console handler gets INFO logs
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(message)s"))

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[file_handler, console_handler],
)

# Silence noisy libraries
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


class ClipboardGPT:
    """
    Main class for ClipboardGPT functionality.
    """

    def __init__(self, handler_type, config=None):
        self.type = handler_type
        self.config = config
        self.system_prompt = self.get_system_prompt_from_type(handler_type)
        self.model = "gpt-4o"
        self.app_name = self.get_app_name_from_type(handler_type)
        self.logger = logging.getLogger(self.app_name + __class__.__name__)
        if OPENAI_API_KEY:
            # Set a reasonable timeout (e.g., 30 seconds) to prevent indefinite hanging
            self.client = OpenAI(api_key=OPENAI_API_KEY, timeout=30.0)
        else:
            self.client = None

    def get_app_name_from_type(self, handler_type):
        """Get app name based on handler type"""
        return f"{handler_type.capitalize()}GPT"

    def get_system_prompt_from_type(self, handler_type):
        """Get system prompt based on handler type"""
        # Check config for custom prompts
        if self.config and "prompts" in self.config:
            if handler_type in self.config["prompts"]:
                return self.config["prompts"][handler_type]

        # Fallback for backward compatibility if config isn't updated yet
        defaults = {
            "grammar": "Fix grammar in the following text in the language that is is provided and rewrite it to make more sense if it is too confusing. REPLY ONLY with the improved text and nothing else:",
            "reply": "Write a response to the following message. Reply ONLY with the response and nothing else in the original language:",
        }

        if handler_type in defaults:
            return defaults[handler_type]

        # If not found in config or defaults
        raise ValueError(
            f"Handler type '{handler_type}' not found in config [prompts]. Please run --setup to add it."
        )

    def get_selected_text(self):
        """Get selected text"""
        self.logger.debug("Getting selected text")
        try:
            self.logger.debug("Trying xsel")
            result = subprocess.run(
                ["xsel", "-o"], stdout=subprocess.PIPE, text=True, check=False
            )
            self.logger.debug(
                "xsel returned: %s",
                result.stdout[:50] + "..." if result.stdout else "empty",
            )
            return result.stdout.strip()
        except FileNotFoundError:
            self.logger.debug("xsel not found")
            pass

        try:
            self.logger.debug("Trying xclip")
            result = subprocess.run(
                ["xclip", "-out", "-selection", "primary"],
                stdout=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.logger.debug(
                "xclip returned: %s",
                result.stdout[:50] + "..." if result.stdout else "empty",
            )
            return result.stdout.strip()
        except FileNotFoundError:
            print("Error: 'xsel' or 'xclip' not found.")
            print("Please install one of them to use the selection feature.")
            print("  sudo apt install xsel")
            print("  or")
            print("  sudo apt install xclip")
            sys.exit(1)

    def get_clipboard_text(self):
        """Get text from clipboard"""
        return pyperclip.paste()

    def set_model(self, model):
        """Set model"""
        # check if string starts with gpt-
        if not model.startswith("gpt-"):
            raise ValueError("Model must start with gpt-")
        self.model = model

    def get_gpt_response(
        self,
        prompt: str,
        model: Optional[str] = None,
        systemprompt: Optional[str] = None,
    ):
        """Get response from GPT"""
        systemprompt = systemprompt or self.system_prompt
        model = model or self.model
        messages: List[Dict[str, Any]] = [{"role": "user", "content": prompt}]
        if systemprompt:
            messages.insert(0, {"role": "system", "content": systemprompt})
        model_engine = model
        if not self.client:
            raise ValueError("OpenAI Client not initialized. Check API Key.")

        self.logger.debug("Sending request to OpenAI model: %s", model_engine)
        try:
            response = self.client.chat.completions.create(model=model_engine, messages=messages)  # type: ignore
            self.logger.debug("Received response from OpenAI")
            message = response.choices[0].message.content
            return message
        except Exception as e:
            self.logger.error("Error calling OpenAI: %s", e)
            raise e

    def show_notification(self, message, timeout=5):
        """Show notification"""
        self.logger.debug("Showing notification: %s", message)
        notification.notify(  # type: ignore
            title=self.app_name,
            message=message,
            app_name=self.app_name,
            timeout=timeout,  # Duration in seconds
        )
        self.logger.debug("Notification function returned")

    def get_title_and_medium_from_active_window(self) -> Tuple[str, str]:
        """function that returns the medium (email,chat,etc) from the window title) using xdotool"""
        chat_names = [
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
        ]
        email_names = [
            "gmail",
            "outlook",
            "thunderbird",
            "evolution",
            "kmail",
            "mail",
            "email",
        ]
        try:
            window_title = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                stdout=subprocess.PIPE,
                text=True,
                check=False,
            ).stdout
        except FileNotFoundError:
            self.logger.warning("xdotool not found, cannot detect window title")
            return "", "unknown"

        self.logger.debug("title: %s", window_title)
        for chat_name in chat_names:
            if chat_name in window_title.lower():
                return window_title, "chat"
        for email_name in email_names:
            if email_name in window_title.lower():
                return window_title, "email"
        return window_title, "unknown"


def main(args_list=None):
    """Main entry point"""
    if "--setup" in sys.argv:
        setup_config()
        sys.exit(0)

    try:
        parser = argparse.ArgumentParser(description="Get GPT Response")
        parser.add_argument(
            "--type",
            default="grammar",
            help="Type of response (grammar, reply, or custom key in config)",
        )
        parser.add_argument(
            "--source",
            choices=["selection"],
            default="selection",
            help="Source of input text (selection)",
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
            help="Model to use (gpt-4 or gpt-3.5-turbo)",
        )
        args = parser.parse_args(args_list)

        # Ensure API key is present
        if not OPENAI_API_KEY:
            print("Error: OPENAI_API_KEY not found.")
            print("Please set it in your environment or in the config file.")
            print("Or run with --setup to configure.")
            sys.exit(1)

        clipboardgpt = ClipboardGPT(args.type, config=config)
        clipboardgpt.logger.info("Starting main with args: %s", args)
        text = ""
        if args.source == "selection":
            text = clipboardgpt.get_selected_text()
            clipboardgpt.logger.debug("Got text length: %d", len(text))
        # compose prompt
        PROMPT = ""
        title, medium = clipboardgpt.get_title_and_medium_from_active_window()

        # Format system prompt with variables if available
        try:
            clipboardgpt.system_prompt = clipboardgpt.system_prompt.format(
                name=config.get("name", ""),
                medium=medium,
                window_title=title,
                clipboard_text=text,
            )
        except KeyError:
            # Ignore formatting errors if keys are missing in the prompt string
            pass

        if medium in ("chat", "email"):
            PROMPT += f"medium: {medium}\n"
            PROMPT += f"window name: {title}\n"
        if args.context != "":
            PROMPT += f"context: {args.context}\n"
        PROMPT += f"text (retain original language): {text}\n"
        PROMPT = PROMPT.strip()
        if text:
            clipboardgpt.logger.debug("Showing waiting notification")
            clipboardgpt.show_notification(
                f"waiting on chatgpt ({args.model})...", timeout=3
            )
            clipboardgpt.logger.debug("Calling get_gpt_response")
            gpt_response = clipboardgpt.get_gpt_response(PROMPT, args.model)
            clipboardgpt.logger.debug(
                "Got response length: %d", len(gpt_response) if gpt_response else 0
            )

            clipboardgpt.logger.debug("Showing response notification")
            clipboardgpt.show_notification(f"{gpt_response}")

            if gpt_response:
                clipboardgpt.logger.debug("Copying to clipboard")
                pyperclip.copy(gpt_response)
                clipboardgpt.logger.debug("Copied to clipboard")
    except Exception as e:
        logging.getLogger("ClipboardGPT").exception("Unhandled exception:")
        try:
            notification.notify(
                title="ClipboardGPT Error",
                message=str(e),
                app_name="ClipboardGPT",
                timeout=10,
            )
        except Exception:
            pass
        raise e


if __name__ == "__main__":
    main()
