"""Project configuration with Pydantic Settings."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from vibewriting.config_paper import PaperConfig

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables with VW_ prefix."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_prefix="VW_",
        extra="ignore",
    )

    # Dify
    dify_api_base_url: str = ""
    dify_api_key: str = ""
    dify_dataset_id: str = ""

    # Pipeline
    random_seed: int = 42
    float_precision: int = 6

    # Literature dedup
    dedup_threshold: float = 0.9

    # Compilation & quality (Phase 6)
    compile_max_retries: int = 5
    compile_timeout_sec: int = 120
    patch_window_lines: int = 10
    enable_layout_check: bool = False
    enable_ai_disclosure: bool = False
    crossref_api_email: str = ""

    # Paths (computed defaults, not from env)
    project_root: Path = PROJECT_ROOT
    data_dir: Path = PROJECT_ROOT / "data"
    output_dir: Path = PROJECT_ROOT / "output"
    paper_dir: Path = PROJECT_ROOT / "paper"

    @property
    def dify_available(self) -> bool:
        return bool(self.dify_api_base_url and self.dify_api_key and self.dify_dataset_id)


settings = Settings()


def apply_paper_config(paper_config: PaperConfig) -> Settings:
    """Create a new Settings instance with PaperConfig overrides applied.

    Priority: environment variables > paper_config.yaml > defaults.
    Only overrides fields whose env var is NOT set (still at default).

    Args:
        paper_config: PaperConfig loaded from YAML.

    Returns:
        New Settings instance with overrides applied.
    """
    overrides: dict = {}
    defaults = Settings.model_fields

    # Map PaperConfig fields to Settings fields (only overlapping ones)
    field_map = {
        "random_seed": "random_seed",
        "float_precision": "float_precision",
        "dedup_threshold": "dedup_threshold",
        "compile_max_retries": "compile_max_retries",
        "compile_timeout_sec": "compile_timeout_sec",
        "enable_ai_disclosure": "enable_ai_disclosure",
    }

    for pc_field, settings_field in field_map.items():
        pc_value = getattr(paper_config, pc_field, None)
        if pc_value is None:
            continue
        # Only override if Settings still has the default value
        # (meaning env var was NOT set)
        current = getattr(settings, settings_field)
        default_val = defaults[settings_field].default
        if current == default_val:
            overrides[settings_field] = pc_value

    if not overrides:
        return settings

    return settings.model_copy(update=overrides)
