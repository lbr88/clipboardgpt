#!/usr/bin/env python3
import os
import argparse
import subprocess
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
from plyer import notification
import pyperclip
import logging

# get home dir
home = os.path.expanduser("~")
logfile = os.path.join(home, "log", "replygpt.log")

# log to file and to console
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(logfile, mode="a"),
        logging.StreamHandler(),
    ],
)


class ClipboardGPT:
    def __init__(self, handler_type, config=None):
        self.type = handler_type
        self.config = config
        self.system_prompt = self.get_system_prompt_from_type(handler_type)
        self.model = "gpt-4o"
        self.app_name = self.get_app_name_from_type(handler_type)
        self.logger = logging.getLogger(self.app_name + __class__.__name__)

    def get_app_name_from_type(self, handler_type):
        """Get app name based on handler type"""
        match handler_type:
            case "reply":
                return "ReplyGPT"
            case "grammar":
                return "GrammarGPT"
        return "GPT"

    def get_system_prompt_from_type(self, handler_type):
        """Get system prompt based on handler type"""
        match handler_type:
            case "reply":
                return (
                    "Write a response to the following message. "
                    "Reply ONLY with the response and nothing "
                    "else in the original language:"
                )
            case "grammar":
                return (
                    "Fix grammar in the following text "
                    "in the language that is is provided "
                    "and rewrite it to make more sense if "
                    "it is too confusing. "
                    "REPLY ONLY with the improved text and nothing else:"
                )
        raise ValueError(f"Handler type {handler_type} not allowed")

    def get_selected_text(self):
        """Get selected text"""
        result = subprocess.run(
            ["xsel", "-o"], stdout=subprocess.PIPE, text=True, check=False
        )
        return result.stdout.strip()

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
        self, prompt: str, model: str = None, systemprompt: str = None
    ):
        """Get response from GPT"""
        systemprompt = systemprompt or self.system_prompt
        model = model or self.model
        messages = [{"role": "user", "content": prompt}]
        if systemprompt:
            messages.insert(0, {"role": "system", "content": systemprompt})
        model_engine = model
        response = client.chat.completions.create(model=model_engine, messages=messages)
        message = response.choices[0].message.content
        return message

    def show_notification(self, message, timeout=5):
        """Show notification"""
        notification.notify(
            title=self.app_name,
            message=message,
            app_name=self.app_name,
            timeout=timeout,  # Duration in seconds
        )

    def get_title_and_medium_from_active_window(self) -> str:
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
        window_title = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            stdout=subprocess.PIPE,
            text=True,
            check=False,
        ).stdout
        self.logger.debug("title: %s", window_title)
        for chat_name in chat_names:
            if chat_name in window_title.lower():
                return window_title, "chat"
        for email_name in email_names:
            if email_name in window_title.lower():
                return window_title, "email"
        return window_title, "unknown"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get GPT Response")
    parser.add_argument(
        "--type",
        choices=["grammar", "reply"],
        default="grammar",
        help="Type of response (grammar or reply)",
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
    args = parser.parse_args()
    clipboardgpt = ClipboardGPT(args.type)
    APP_NAME = clipboardgpt.app_name
    logger = logging.getLogger(APP_NAME)

    windowtitle, args.medium = clipboardgpt.get_title_and_medium_from_active_window()
    if args.source == "selection":
        text = clipboardgpt.get_selected_text()
    # compose prompt
    PROMPT = ""
    title, medium = clipboardgpt.get_title_and_medium_from_active_window()
    if medium == "chat" or medium == "email":
        PROMPT += f"medium: {medium}\n"
        PROMPT += f"window name: {title}\n"
    if args.context != "":
        PROMPT += f"context: {args.context}\n"
    PROMPT += f"text (retain original language): {text}\n"
    PROMPT = PROMPT.strip()
    if text:
        clipboardgpt.show_notification(
            f"waiting on chatgpt ({args.model})...", timeout=3
        )
        gpt_response = clipboardgpt.get_gpt_response(PROMPT, args.model)
        clipboardgpt.show_notification(f"{gpt_response}")
        pyperclip.copy(gpt_response)
