"""LaTeX log file parser with error classification."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class ErrorKind(Enum):
    MISSING_PACKAGE = "missing_package"
    UNDEFINED_REFERENCE = "undefined_reference"
    SYNTAX_ERROR = "syntax_error"
    MISSING_FILE = "missing_file"
    ENCODING_ERROR = "encoding_error"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class LatexError:
    line_number: int | None
    file_path: str | None
    error_type: str
    message: str
    context_lines: list[str] = field(default_factory=list)


_ERROR_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^! LaTeX Error: File `(.+?)' not found", re.MULTILINE), "file_not_found"),
    (re.compile(r"^! LaTeX Error: (.+)$", re.MULTILINE), "latex_error"),
    (re.compile(r"^! Undefined control sequence\.", re.MULTILINE), "undefined_control"),
    (re.compile(r"^! Missing (.+)\.", re.MULTILINE), "missing_token"),
    (re.compile(r"^! I can't find file `(.+?)'", re.MULTILINE), "cant_find_file"),
    (re.compile(r"^! Package (.+?) Error: (.+)$", re.MULTILINE), "package_error"),
    (re.compile(r"^! (.+)$", re.MULTILINE), "generic_error"),
]

_FILE_LINE_PATTERN = re.compile(r"^(\.?/?.+?\.\w+):(\d+):", re.MULTILINE)
_INPUT_FILE_PATTERN = re.compile(r"\(([^\s()]+\.\w+)")

_CLASSIFY_RULES: list[tuple[re.Pattern[str], ErrorKind]] = [
    (re.compile(r"File `.+?' not found|can't find file", re.IGNORECASE), ErrorKind.MISSING_FILE),
    (re.compile(r"Package .+? Error|! LaTeX Error:.*package", re.IGNORECASE), ErrorKind.MISSING_PACKAGE),
    (re.compile(r"Undefined control sequence|Undefined reference", re.IGNORECASE), ErrorKind.UNDEFINED_REFERENCE),
    (re.compile(r"Missing \$|Missing \\|Missing {|Missing }", re.IGNORECASE), ErrorKind.SYNTAX_ERROR),
    (re.compile(r"encoding|codec|unicode|utf-?8|byte sequence", re.IGNORECASE), ErrorKind.ENCODING_ERROR),
]


def classify_error(error: LatexError) -> ErrorKind:
    text = f"{error.error_type} {error.message}"
    for pattern, kind in _CLASSIFY_RULES:
        if pattern.search(text):
            return kind
    return ErrorKind.UNKNOWN


def _find_file_context(log_content: str, match_start: int) -> tuple[str | None, int | None]:
    preceding = log_content[:match_start]
    file_line_matches = list(_FILE_LINE_PATTERN.finditer(preceding))
    if file_line_matches:
        last = file_line_matches[-1]
        return last.group(1), int(last.group(2))
    file_matches = list(_INPUT_FILE_PATTERN.finditer(preceding[-500:]))
    if file_matches:
        return file_matches[-1].group(1), None
    return None, None


def parse_log(log_content: str) -> list[LatexError]:
    errors: list[LatexError] = []
    seen_positions: set[int] = set()

    for pattern, error_type in _ERROR_PATTERNS:
        for match in pattern.finditer(log_content):
            if match.start() in seen_positions:
                continue
            seen_positions.add(match.start())

            message = match.group(0).lstrip("! ").strip()
            file_path, line_number = _find_file_context(log_content, match.start())

            line_match = re.search(r"l\.(\d+)", log_content[match.start():match.start() + 300])
            if line_match:
                line_number = int(line_match.group(1))

            errors.append(LatexError(
                line_number=line_number,
                file_path=file_path,
                error_type=error_type,
                message=message,
            ))

    return errors


def extract_error_context(log_content: str, error: LatexError, window: int = 5) -> str:
    lines = log_content.splitlines()
    target = error.message

    for i, line in enumerate(lines):
        if target in line or (error.error_type in line and "!" in line):
            start = max(0, i - window)
            end = min(len(lines), i + window + 1)
            return "\n".join(lines[start:end])

    return ""
