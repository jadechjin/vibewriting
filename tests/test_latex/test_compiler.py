"""Tests for LaTeX compiler module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

from vibewriting.latex.compiler import (
    compile_full,
    route_error,
    _is_auto_fixable,
)
from vibewriting.latex.log_parser import LatexError, ErrorKind, classify_error
from vibewriting.review.models import PatchReport


class TestCompileFull:
    def test_missing_main_tex(self, tmp_path: Path):
        success, msg = compile_full(tmp_path)
        assert success is False
        assert "main.tex not found" in msg

    @patch("vibewriting.latex.compiler.subprocess.run")
    def test_latexmk_not_found(self, mock_run, tmp_paper_dir: Path):
        mock_run.side_effect = FileNotFoundError("latexmk")
        success, msg = compile_full(tmp_paper_dir)
        assert success is False
        assert "latexmk not found" in msg

    @patch("vibewriting.latex.compiler.subprocess.run")
    def test_timeout(self, mock_run, tmp_paper_dir: Path):
        mock_run.side_effect = subprocess.TimeoutExpired("latexmk", 120)
        success, msg = compile_full(tmp_paper_dir)
        assert success is False
        assert "timed out" in msg

    def test_compile_full_no_halt_on_error(self, tmp_path: Path) -> None:
        """compile_full should not use -halt-on-error flag."""
        main_tex = tmp_path / "main.tex"
        main_tex.write_text("\\documentclass{article}\\begin{document}\\end{document}")

        with patch("vibewriting.latex.compiler.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            compile_full(tmp_path)

            called_cmd = mock_run.call_args[0][0]
            assert "-halt-on-error" not in called_cmd

    def test_latexmkrc_has_bibtex_use(self) -> None:
        """paper/latexmkrc should force BibTeX to run with $bibtex_use = 2."""
        latexmkrc = Path("f:/vibewriting/paper/latexmkrc")
        if latexmkrc.exists():
            content = latexmkrc.read_text(encoding="utf-8")
            assert "$bibtex_use" in content
            assert "2" in content


class TestRouteError:
    def test_route_missing_package(self):
        e = LatexError(None, None, "package_error", "Package foo Error: not found")
        result = route_error(e)
        assert "MANUAL" in result

    def test_route_syntax_error(self):
        e = LatexError(None, None, "missing_token", "Missing $ inserted")
        result = route_error(e)
        assert "AUTO" in result

    def test_route_unknown(self):
        e = LatexError(None, None, "generic_error", "Emergency stop")
        result = route_error(e)
        assert "SKIP" in result


class TestIsAutoFixable:
    def test_syntax_fixable(self):
        e = LatexError(None, None, "missing_token", "Missing $ inserted")
        assert _is_auto_fixable(e) is True

    def test_package_not_fixable(self):
        e = LatexError(None, None, "package_error", "Package hyperref Error")
        assert _is_auto_fixable(e) is False

    def test_unknown_not_fixable(self):
        e = LatexError(None, None, "generic_error", "Emergency stop")
        assert _is_auto_fixable(e) is False
