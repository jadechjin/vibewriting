"""Tests for incremental compilation module."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vibewriting.writing.incremental import (
    DRAFT_PREAMBLE,
    cleanup_draft,
    compile_single_section,
    generate_draft_main,
    write_draft_main,
)


# ── generate_draft_main ──

class TestGenerateDraftMain:
    def test_contains_preamble(self):
        """生成内容应包含完整 preamble。"""
        result = generate_draft_main("sections/introduction.tex")
        assert r"\documentclass[UTF8, a4paper, 12pt, zihao=-4]{ctexart}" in result
        assert r"\usepackage{amsmath}" in result
        assert r"\usepackage{booktabs}" in result
        assert r"\graphicspath{{figures/}}" in result

    def test_strips_tex_extension(self):
        r"""输入带 .tex 后缀时，\input{} 中自动去除。"""
        result = generate_draft_main("sections/introduction.tex")
        assert r"\input{sections/introduction}" in result
        assert r"\input{sections/introduction.tex}" not in result

    def test_no_tex_extension_works(self):
        r"""输入无 .tex 后缀时正常处理，\input{} 路径正确。"""
        result = generate_draft_main("sections/method")
        assert r"\input{sections/method}" in result

    def test_custom_title_in_output(self):
        r"""自定义标题出现在 \title{} 中。"""
        result = generate_draft_main("sections/intro.tex", title="My Custom Title")
        assert r"\title{My Custom Title}" in result

    def test_default_title(self):
        r"""默认标题为 Draft。"""
        result = generate_draft_main("sections/intro.tex")
        assert r"\title{Draft}" in result

    def test_contains_bibliography(self):
        """输出包含 bibliography 相关命令（默认 unsrtnat）。"""
        result = generate_draft_main("sections/intro.tex")
        assert r"\bibliographystyle{unsrtnat}" in result
        assert r"\bibliography{bib/references}" in result

    def test_custom_natbib_style(self):
        """自定义 natbib_style 参数化输出。"""
        result = generate_draft_main("sections/intro.tex", natbib_style="plainnat")
        assert r"\bibliographystyle{plainnat}" in result
        assert r"\bibliographystyle{unsrtnat}" not in result

    def test_contains_begin_end_document(self):
        """输出包含 begin/end document 块。"""
        result = generate_draft_main("sections/intro.tex")
        assert r"\begin{document}" in result
        assert r"\end{document}" in result

    def test_contains_maketitle(self):
        r"""输出包含 \maketitle。"""
        result = generate_draft_main("sections/intro.tex")
        assert r"\maketitle" in result


# ── write_draft_main ──

class TestWriteDraftMain:
    def test_writes_to_paper_dir(self, tmp_path):
        """文件写入到 paper_dir/draft_main.tex。"""
        draft_path = write_draft_main(tmp_path, "sections/intro.tex")
        assert draft_path == tmp_path / "draft_main.tex"
        assert draft_path.exists()

    def test_written_content_matches_generate(self, tmp_path):
        """读回内容与 generate_draft_main 一致。"""
        section = "sections/introduction.tex"
        title = "Test Title"
        draft_path = write_draft_main(tmp_path, section, title=title)
        written = draft_path.read_text(encoding="utf-8")
        expected = generate_draft_main(section, title=title)
        assert written == expected

    def test_returns_path_object(self, tmp_path):
        """返回值为 Path 对象。"""
        result = write_draft_main(tmp_path, "sections/method.tex")
        assert isinstance(result, Path)

    def test_overwrites_existing_file(self, tmp_path):
        """已存在的 draft_main.tex 被正确覆盖。"""
        draft = tmp_path / "draft_main.tex"
        draft.write_text("old content", encoding="utf-8")
        write_draft_main(tmp_path, "sections/new.tex", title="New")
        content = draft.read_text(encoding="utf-8")
        assert "old content" not in content
        assert "New" in content


# ── compile_single_section ──

class TestCompileSingleSection:
    def test_returns_false_when_latexmk_not_found(self, tmp_path):
        """latexmk 不可用时返回 (False, 'latexmk not found')。"""
        with patch("shutil.which", return_value=None):
            success, log = compile_single_section(tmp_path, "sections/intro.tex")
        assert success is False
        assert "latexmk not found" in log

    def test_returns_true_on_successful_compilation(self, tmp_path):
        """mock subprocess.run 返回 0 时，结果为 (True, ...)。"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Success output"
        mock_result.stderr = ""

        with patch("shutil.which", return_value="/usr/bin/latexmk"):
            with patch("subprocess.run", return_value=mock_result):
                success, log = compile_single_section(tmp_path, "sections/intro.tex")

        assert success is True
        assert "Success output" in log

    def test_returns_false_on_compilation_failure(self, tmp_path):
        """mock subprocess.run 返回非 0 时，结果为 (False, ...)。"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error output"

        with patch("shutil.which", return_value="/usr/bin/latexmk"):
            with patch("subprocess.run", return_value=mock_result):
                success, log = compile_single_section(tmp_path, "sections/intro.tex")

        assert success is False
        assert "Error output" in log

    def test_returns_false_on_timeout(self, tmp_path):
        """subprocess.TimeoutExpired → 返回 (False, '...timed out...')。"""
        with patch("shutil.which", return_value="/usr/bin/latexmk"):
            with patch(
                "subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="latexmk", timeout=120),
            ):
                success, log = compile_single_section(tmp_path, "sections/intro.tex")

        assert success is False
        assert "timed out" in log

    def test_writes_draft_main_before_compilation(self, tmp_path):
        """编译前应生成 draft_main.tex 文件。"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("shutil.which", return_value="/usr/bin/latexmk"):
            with patch("subprocess.run", return_value=mock_result):
                compile_single_section(tmp_path, "sections/intro.tex")

        assert (tmp_path / "draft_main.tex").exists()


# ── cleanup_draft ──

class TestCleanupDraft:
    def test_removes_draft_main_tex(self, tmp_path):
        """cleanup_draft 删除 draft_main.tex。"""
        draft = tmp_path / "draft_main.tex"
        draft.write_text("content", encoding="utf-8")
        cleanup_draft(tmp_path)
        assert not draft.exists()

    def test_no_error_when_file_not_exists(self, tmp_path):
        """draft_main.tex 不存在时不报错。"""
        cleanup_draft(tmp_path)  # Should not raise

    def test_removes_build_artifacts(self, tmp_path):
        """删除 build/ 目录中的 draft_main.* 文件。"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        artifact_pdf = build_dir / "draft_main.pdf"
        artifact_aux = build_dir / "draft_main.aux"
        artifact_pdf.write_bytes(b"fake pdf")
        artifact_aux.write_text("aux content", encoding="utf-8")

        cleanup_draft(tmp_path)

        assert not artifact_pdf.exists()
        assert not artifact_aux.exists()

    def test_does_not_remove_other_build_files(self, tmp_path):
        """不删除 build/ 中非 draft_main 的文件。"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        main_pdf = build_dir / "main.pdf"
        main_pdf.write_bytes(b"main pdf")

        cleanup_draft(tmp_path)

        assert main_pdf.exists()
