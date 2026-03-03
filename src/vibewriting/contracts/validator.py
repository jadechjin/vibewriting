"""Contract validation with self-healing loop.

Validates JSON payloads against schemas with a retry loop:
1. jsonschema.validate()
2. On failure -> regex healer
3. Still fails -> LLM healer
4. Max 3 retries, then raise ContractValidationError
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema

from .healers import llm_healer, regex_healer
from .healers.llm_healer import LLMBackend, ValidationErrorInfo

logger = logging.getLogger(__name__)

SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas"


class ContractValidationError(Exception):
    """Raised when payload cannot be healed within max retries."""

    def __init__(self, message: str, violations: list[str]):
        super().__init__(message)
        self.violations = violations


@dataclass
class ValidatedPayload:
    """Result of a successful validation."""

    data: dict[str, Any]
    heal_rounds: int = 0
    violation_counts: list[int] = field(default_factory=list)


def _load_schema(schema_name: str) -> dict[str, Any]:
    """Load a JSON Schema by name from the schemas directory."""
    path = SCHEMAS_DIR / f"{schema_name}.schema.json"
    if not path.exists():
        raise FileNotFoundError(f"Schema not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _collect_errors(payload: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """Collect all validation errors for a payload against a schema."""
    validator = jsonschema.Draft202012Validator(schema)
    return [e.message for e in validator.iter_errors(payload)]


def _to_error_infos(
    payload: dict[str, Any], schema: dict[str, Any]
) -> list[ValidationErrorInfo]:
    """Convert jsonschema errors to ValidationErrorInfo for LLM healer."""
    validator = jsonschema.Draft202012Validator(schema)
    return [
        ValidationErrorInfo(
            path=".".join(str(p) for p in e.absolute_path),
            message=e.message,
            schema_path=".".join(str(p) for p in e.absolute_schema_path),
        )
        for e in validator.iter_errors(payload)
    ]


def validate_contract(
    payload: str | dict[str, Any],
    schema_name: str,
    max_retries: int = 3,
    llm_backend: LLMBackend | None = None,
) -> ValidatedPayload:
    """Validate payload against a named schema with self-healing.

    Args:
        payload: JSON string or dict to validate.
        schema_name: Name of the schema (without .schema.json extension).
        max_retries: Maximum healing attempts (hard cap: 3).
        llm_backend: Optional LLM callable for fallback healing.

    Returns:
        ValidatedPayload on success.

    Raises:
        ContractValidationError: If healing fails after max_retries.
    """
    max_retries = min(max_retries, 3)
    schema = _load_schema(schema_name)

    # Parse string payload
    if isinstance(payload, str):
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            # Try regex healing on the raw string
            healed = regex_healer.heal(payload)
            try:
                data = json.loads(healed)
            except json.JSONDecodeError as exc:
                raise ContractValidationError(
                    f"Cannot parse payload as JSON: {exc}",
                    violations=[str(exc)],
                ) from exc
    else:
        data = payload

    violation_counts: list[int] = []

    for round_num in range(max_retries):
        errors = _collect_errors(data, schema)
        violation_counts.append(len(errors))

        if not errors:
            return ValidatedPayload(
                data=data,
                heal_rounds=round_num,
                violation_counts=violation_counts,
            )

        logger.info("Round %d: %d violations", round_num + 1, len(errors))

        # First try regex healing
        raw = json.dumps(data, ensure_ascii=False)
        healed_str = regex_healer.heal(raw)
        try:
            data = json.loads(healed_str)
        except json.JSONDecodeError:
            pass

        # Check if regex fixed it
        errors_after_regex = _collect_errors(data, schema)
        if not errors_after_regex:
            violation_counts.append(0)
            return ValidatedPayload(
                data=data,
                heal_rounds=round_num + 1,
                violation_counts=violation_counts,
            )

        # Try LLM healing if available
        if llm_backend is not None:
            error_infos = _to_error_infos(data, schema)
            schema_snippet = json.dumps(schema, indent=2)[:500]
            result = llm_healer.heal(
                json.dumps(data, ensure_ascii=False),
                error_infos,
                llm_backend,
                schema_snippet,
            )
            if result.success:
                try:
                    data = json.loads(result.healed_payload)
                except json.JSONDecodeError:
                    pass

    # Final check
    final_errors = _collect_errors(data, schema)
    violation_counts.append(len(final_errors))
    if not final_errors:
        return ValidatedPayload(
            data=data,
            heal_rounds=max_retries,
            violation_counts=violation_counts,
        )

    raise ContractValidationError(
        f"Validation failed after {max_retries} rounds: {len(final_errors)} violations remain",
        violations=final_errors,
    )
