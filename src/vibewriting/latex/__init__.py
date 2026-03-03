"""LaTeX compilation and asset management."""

from vibewriting.latex.compiler import compile_full, run_self_heal_loop, write_patch_reports
from vibewriting.latex.log_parser import ErrorKind, LatexError, classify_error, parse_log
from vibewriting.latex.patch_guard import PatchProposal

__all__ = [
    "ErrorKind",
    "LatexError",
    "PatchProposal",
    "classify_error",
    "compile_full",
    "parse_log",
    "run_self_heal_loop",
    "write_patch_reports",
]
