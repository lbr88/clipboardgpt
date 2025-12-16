"""Shared constants for ClipboardGPT."""

import os

CONFIG_PATH = os.path.expanduser("~/.config/clipboardgpt/config.toml")

DEFAULT_PROMPTS = {
    "grammar": (
        "Fix grammar in the following text in the language that is provided "
        "and rewrite it to make more sense if it is too confusing. "
        "REPLY ONLY with the improved text and nothing else:"
    ),
    "reply": (
        "Write a response to the following message. "
        "Reply ONLY with the response and nothing else in the original language:"
    ),
}
