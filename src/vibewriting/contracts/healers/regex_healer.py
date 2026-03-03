"""Rule-based JSON healer using regex patterns.

Fixes common JSON errors produced by LLMs:
- Unclosed quotes
- Illegal escape sequences
- Markdown code block wrappers
- Trailing commas before closing brackets
- Single quotes instead of double quotes
"""

from __future__ import annotations

import re


def strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers."""
    text = text.strip()
    text = re.sub(r"^```(?:json|JSON)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def fix_trailing_commas(text: str) -> str:
    """Remove trailing commas before ] or }."""
    return re.sub(r",\s*([}\]])", r"\1", text)


def fix_single_quotes(text: str) -> str:
    """Replace single-quoted JSON keys/values with double quotes.

    Only handles simple cases where single quotes wrap alphanumeric content.
    """
    return re.sub(r"'([^']*)'", r'"\1"', text)


def fix_illegal_escapes(text: str) -> str:
    """Fix invalid JSON escape sequences inside string literals.

    Rules:
    - Keep valid escapes unchanged (\\", \\\\, \\/, \\b, \\f, \\n, \\r, \\t, \\u)
    - Preserve existing double backslashes (e.g. \\\\d) as-is
    - Convert invalid single-backslash escapes (e.g. \\d) to \\\\d
    """
    valid_escapes = set('"\\bfnrtu/')
    result: list[str] = []
    i = 0
    in_string = False

    while i < len(text):
        ch = text[i]

        if ch == '"' and (i == 0 or text[i - 1] != "\\"):
            in_string = not in_string
            result.append(ch)
            i += 1
            continue

        if in_string and ch == "\\":
            # Check for double backslash: \\ -> preserve as \\
            if i + 1 < len(text) and text[i + 1] == "\\":
                result.append("\\\\")
                i += 2
                continue

            # Single backslash: validate following escape marker
            if i + 1 < len(text):
                next_ch = text[i + 1]
                if next_ch in valid_escapes:
                    # Valid escape sequence, keep the backslash
                    result.append("\\")
                else:
                    # Invalid escape, double the backslash to make it valid JSON
                    result.append("\\\\")
            else:
                # Trailing backslash at string end -> make it literal backslash
                result.append("\\\\")
            i += 1
            continue

        result.append(ch)
        i += 1

    return "".join(result)


def fix_unclosed_strings(text: str) -> str:
    """Attempt to close unclosed string literals at line boundaries."""
    lines = text.split("\n")
    fixed = []
    for line in lines:
        quote_count = line.count('"') - line.count('\\"')
        if quote_count % 2 != 0:
            line = line + '"'
        fixed.append(line)
    return "\n".join(fixed)


def heal(payload: str) -> str:
    """Apply all regex healing rules in sequence."""
    payload = strip_markdown_fences(payload)
    payload = fix_trailing_commas(payload)
    payload = fix_single_quotes(payload)
    payload = fix_illegal_escapes(payload)
    payload = fix_unclosed_strings(payload)
    return payload
