"""AI usage disclosure generation for academic papers."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_EN_TEMPLATE = (
    "This paper was prepared with the assistance of artificial intelligence tools. "
    "The AI was used to support literature review, data analysis, and drafting. "
    "All content has been reviewed, verified, and approved by the authors, "
    "who take full responsibility for the final manuscript."
)

DEFAULT_ZH_TEMPLATE = (
    "本文在撰写过程中使用了人工智能辅助工具。"
    "AI 被用于辅助文献综述、数据分析和初稿撰写。"
    "所有内容均经作者审阅、核实并最终确认，"
    "作者对最终稿件承担全部责任。"
)

_TEMPLATES: dict[str, str] = {
    "default": DEFAULT_EN_TEMPLATE,
    "zh": DEFAULT_ZH_TEMPLATE,
}


class DisclosureConfig(BaseModel):
    """Configuration for AI usage disclosure."""

    model_config = ConfigDict(extra="forbid")

    enable: bool = False
    template: str = "default"
    placement: Literal["appendix", "acknowledgments"] = "acknowledgments"


def generate_disclosure_text(config: DisclosureConfig, paper_state: dict) -> str:
    """Generate disclosure text based on config and paper state.

    Returns empty string when disclosure is disabled.
    """
    if not config.enable:
        return ""

    return _TEMPLATES.get(config.template, _TEMPLATES["default"])


def inject_disclosure(paper_dir: Path, config: DisclosureConfig, text: str) -> Path:
    """Write disclosure text to a LaTeX section file.

    Returns the path of the written file.
    """
    output = paper_dir / "sections" / "ai_disclosure.tex"
    output.parent.mkdir(parents=True, exist_ok=True)

    if not text:
        output.write_text("", encoding="utf-8")
        return output

    if config.placement == "appendix":
        latex = (
            "\\section*{AI Usage Disclosure}\n"
            f"{text}\n"
        )
    else:
        latex = (
            "\\subsection*{AI Usage Disclosure}\n"
            f"{text}\n"
        )

    output.write_text(latex, encoding="utf-8")
    return output
