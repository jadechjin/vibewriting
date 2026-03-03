"""LLM-based JSON healer interface.

Provides a fallback healing mechanism when regex rules fail.
The actual LLM call is abstracted behind a callable to keep this
module testable without real API calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol


class ValidationErrorInfo:
    """Simplified validation error for prompt construction."""

    def __init__(self, path: str, message: str, schema_path: str = ""):
        self.path = path
        self.message = message
        self.schema_path = schema_path


class LLMBackend(Protocol):
    """Protocol for LLM call backends."""

    def __call__(self, prompt: str) -> str: ...


def _build_prompt(
    payload: str,
    errors: list[ValidationErrorInfo],
    schema_snippet: str = "",
) -> str:
    """Construct a repair prompt from the broken payload and errors."""
    error_lines = "\n".join(
        f"- Path: {e.path} | Error: {e.message}" for e in errors
    )
    return (
        "Fix the following JSON so it passes schema validation.\n"
        "Return ONLY the corrected JSON, no explanation.\n\n"
        f"Schema (relevant part):\n{schema_snippet}\n\n"
        f"Errors:\n{error_lines}\n\n"
        f"Broken JSON:\n{payload}"
    )


@dataclass
class HealResult:
    """Result of an LLM healing attempt."""

    healed_payload: str
    prompt_used: str
    success: bool


def heal(
    payload: str,
    errors: list[ValidationErrorInfo],
    llm_backend: LLMBackend,
    schema_snippet: str = "",
) -> HealResult:
    """Attempt to heal JSON payload using an LLM.

    Args:
        payload: The broken JSON string.
        errors: List of validation errors to include in the prompt.
        llm_backend: Callable that takes a prompt and returns the LLM response.
        schema_snippet: Optional relevant schema portion for context.

    Returns:
        HealResult with the healed payload and metadata.
    """
    prompt = _build_prompt(payload, errors, schema_snippet)
    try:
        response = llm_backend(prompt)
        # Strip markdown fences if the LLM wraps its response
        from .regex_healer import strip_markdown_fences

        cleaned = strip_markdown_fences(response)
        return HealResult(healed_payload=cleaned, prompt_used=prompt, success=True)
    except Exception:
        return HealResult(healed_payload=payload, prompt_used=prompt, success=False)
