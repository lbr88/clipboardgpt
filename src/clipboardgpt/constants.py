"""Shared constants for ClipboardGPT."""

import os

CONFIG_PATH = os.path.expanduser("~/.config/clipboardgpt/config.toml")

# New prompt format: each prompt has 'system' and 'user' templates
# Templates support {variable} substitution and {?var}conditional lines
# Available variables: {text}, {context}, {window_title}, {app}, {name}, {datetime}, {date}, {time}, {year}
DEFAULT_PROMPTS: dict[str, dict[str, str]] = {
    "grammar": {
        "system": (
            "Fix grammar, spelling, punctuation, and informal language.\n\n"
            "RULES:\n"
            "- Fix contractions like 'wanna'→'want to', 'gonna'→'going to', 'u'→'you'\n"
            "- Keep the SAME language (Danish stays Danish, etc.)\n"
            "- Do not translate or add information\n"
            "- Return ONLY the corrected text"
        ),
        "user": "{text}",
    },
    "reply": {
        "system": (
            "Write a response to the following message.\n\n"
            "{?datetime}Current date and time: {datetime}\n\n"
            "RULES:\n"
            "- Respond in the SAME LANGUAGE as the message\n"
            "- Match the tone and formality\n"
            "- Be concise\n"
            "- Return ONLY the response, nothing else"
        ),
        "user": "{text}",
    },
    "cli": {
        "system": (
            "You are a CLI expert. Return ONLY the shell command, "
            "no explanation, no markdown, no code blocks. "
            "Use && for multiple commands. Assume Linux/Unix."
        ),
        "user": "{text}",
    },
}
