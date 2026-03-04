from __future__ import annotations

from vibewriting.config import apply_paper_config
from vibewriting.config_paper import PaperConfig


def test_paper_config_output_formats_default() -> None:
    cfg = PaperConfig(topic="test")
    assert cfg.output_formats == ["latex"]


def test_apply_paper_config_joins_output_formats() -> None:
    cfg = PaperConfig(topic="test", output_formats=["latex", "docx"])
    settings = apply_paper_config(cfg)
    assert settings.output_formats == "latex,docx"


def test_apply_paper_config_reference_docx_and_csl() -> None:
    cfg = PaperConfig(
        topic="test",
        reference_docx_path="paper/templates/reference.docx",
        csl_path="paper/templates/citation.csl",
    )
    settings = apply_paper_config(cfg)
    assert settings.reference_docx_path == "paper/templates/reference.docx"
    assert settings.csl_path == "paper/templates/citation.csl"

