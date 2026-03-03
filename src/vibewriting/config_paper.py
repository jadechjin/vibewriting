"""Paper-level configuration using Pydantic BaseModel + YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, field_validator


DEFAULT_SECTIONS = [
    "引言",
    "相关工作",
    "方法",
    "实验",
    "结论",
]


class PaperConfig(BaseModel):
    topic: str
    language: Literal["zh", "en"] = "zh"
    document_class: str = "ctexart"
    sections: list[str] = DEFAULT_SECTIONS
    literature_query_count: int = 3
    min_evidence_cards: int = 5
    data_dir: str | None = None
    random_seed: int = 42
    writing_mode: Literal["single", "multi"] = "multi"
    enable_ai_disclosure: bool = False
    enable_anonymize: bool = False
    natbib_style: str = "unsrtnat"
    auto_approve: bool = False

    # Pipeline configuration (migrated from .env non-sensitive fields)
    float_precision: int = 6
    dedup_threshold: float = 0.9
    compile_max_retries: int = 5
    compile_timeout_sec: int = 120

    @field_validator("sections")
    @classmethod
    def sections_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("sections must not be empty")
        return v

    @field_validator("literature_query_count")
    @classmethod
    def query_count_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("literature_query_count must be >= 1")
        return v

    @field_validator("min_evidence_cards")
    @classmethod
    def min_cards_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("min_evidence_cards must be >= 1")
        return v


def load_paper_config(path: Path | None = None) -> PaperConfig:
    """Load paper configuration from YAML file.

    Args:
        path: Path to YAML config file. If None or file does not exist,
              returns default configuration with topic='untitled'.

    Returns:
        PaperConfig instance.
    """
    if path is None:
        return PaperConfig(topic="untitled")
    if not path.exists():
        return PaperConfig(topic="untitled")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not data:
        return PaperConfig(topic="untitled")
    return PaperConfig(**data)


def merge_config(base: PaperConfig, overrides: dict) -> PaperConfig:
    """Merge overrides into base config immutably.

    Args:
        base: Base PaperConfig (not modified).
        overrides: Dictionary of fields to override.

    Returns:
        New PaperConfig with overrides applied.
    """
    merged = base.model_dump()
    merged.update(overrides)
    return PaperConfig(**merged)


def save_paper_config(config: PaperConfig, path: Path) -> None:
    """Save paper configuration to YAML file.

    Creates parent directories if they do not exist.

    Args:
        config: PaperConfig to save.
        path: Destination path for the YAML file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    data = config.model_dump()
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
