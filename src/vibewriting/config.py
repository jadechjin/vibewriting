"""Project configuration with Pydantic Settings."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # paper-search
    serpapi_api_key: str = ""

    # LLM
    llm_provider: str = ""
    llm_model: str = ""
    llm_base_url: str = ""
    openai_api_key: str = ""

    # Dify
    dify_api_base_url: str = ""
    dify_api_key: str = ""
    dify_dataset_id: str = ""

    # Paths
    project_root: Path = PROJECT_ROOT
    data_dir: Path = PROJECT_ROOT / "data"
    output_dir: Path = PROJECT_ROOT / "output"
    paper_dir: Path = PROJECT_ROOT / "paper"

    model_config = {"env_file": str(PROJECT_ROOT / ".env"), "extra": "ignore"}

    @property
    def dify_available(self) -> bool:
        return bool(self.dify_api_base_url and self.dify_api_key and self.dify_dataset_id)


settings = Settings()
