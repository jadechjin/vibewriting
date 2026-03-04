"""Rendering pipeline utilities: format-neutral IR and multi-format exporters."""

from .docx_renderer import DocxRenderResult, render_docx_from_ir
from .ir import (
    DocumentIR,
    ParagraphBlockIR,
    SectionIR,
    build_document_ir_from_paper_state,
    load_document_ir,
    write_document_ir,
)
from .parity import build_parity_report, write_parity_report

__all__ = [
    "DocumentIR",
    "SectionIR",
    "ParagraphBlockIR",
    "build_document_ir_from_paper_state",
    "write_document_ir",
    "load_document_ir",
    "DocxRenderResult",
    "render_docx_from_ir",
    "build_parity_report",
    "write_parity_report",
]

