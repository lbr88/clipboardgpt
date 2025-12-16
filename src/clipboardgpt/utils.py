"""Utility functions for ClipboardGPT."""

import re


def _substitute_vars(text: str, variables: dict[str, str]) -> str:
    """Substitute {variable} placeholders in text."""

    def replacer(match: re.Match[str]) -> str:
        var_name = match.group(1)
        return variables.get(var_name, match.group(0))

    return re.sub(r"\{(\w+)\}", replacer, text)


def render_template(template: str, variables: dict[str, str]) -> str:
    """Render a template with variable substitution and conditional lines.

    Supports:
    - {variable} - simple substitution
    - {?var}line content - only include line if 'var' is non-empty

    Args:
        template: The template string.
        variables: Dictionary of variable name -> value.

    Returns:
        Rendered template string.
    """
    lines = template.split("\n")
    result_lines: list[str] = []

    for line in lines:
        # Check for conditional line: {?varname}rest of line
        match = re.match(r"^\{[?](\w+)\}(.*)$", line)
        if match:
            var_name = match.group(1)
            rest_of_line = match.group(2)
            # Only include if variable exists and is non-empty
            if variables.get(var_name):
                # Substitute variables in the rest of the line
                rendered = _substitute_vars(rest_of_line, variables)
                result_lines.append(rendered)
        else:
            # Regular line - substitute variables
            rendered = _substitute_vars(line, variables)
            result_lines.append(rendered)

    return "\n".join(result_lines)
