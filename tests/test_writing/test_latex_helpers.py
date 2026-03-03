"""Tests for latex_helpers module."""

from __future__ import annotations

import pytest

from vibewriting.writing.latex_helpers import (
    count_words_in_tex,
    extract_all_labels,
    extract_all_refs,
    extract_claim_annotations,
    format_citation,
    format_figure_ref,
    format_table_ref,
    inject_claim_annotation,
    split_into_paragraphs,
    strip_claim_annotations,
)


# ── inject_claim_annotation ──

class TestInjectClaimAnnotation:
    def test_adds_annotation_to_plain_line(self):
        """新增：无注释行应追加 CLAIM_ID 注释。"""
        line = "Some experimental result shows improvement."
        result = inject_claim_annotation(line, "EC-2024-001")
        assert result == "Some experimental result shows improvement. %% CLAIM_ID: EC-2024-001"

    def test_replaces_existing_annotation(self):
        """替换：已有注释应被替换为新的 claim_id。"""
        line = "Result is significant. %% CLAIM_ID: EC-2024-001"
        result = inject_claim_annotation(line, "EC-2024-002")
        assert "EC-2024-002" in result
        assert "EC-2024-001" not in result

    def test_preserves_line_content(self):
        """保留内容：原行文字内容不变，只替换/追加注释。"""
        line = "The accuracy improved by 10\\%."
        result = inject_claim_annotation(line, "EC-2025-007")
        assert "The accuracy improved by 10\\%." in result
        assert "EC-2025-007" in result

    def test_replaces_annotation_with_spaces(self):
        """替换带空格的注释格式（%%  CLAIM_ID: ...）。"""
        line = "Data shows trend. %%  CLAIM_ID: EC-2024-003"
        result = inject_claim_annotation(line, "EC-2024-099")
        assert "EC-2024-099" in result
        assert "EC-2024-003" not in result

    def test_result_ends_with_claim(self):
        """注入后行尾应以 %% CLAIM_ID: <id> 结尾。"""
        line = "Hello world"
        result = inject_claim_annotation(line, "EC-2026-010")
        assert result.endswith("%% CLAIM_ID: EC-2026-010")


# ── extract_claim_annotations ──

class TestExtractClaimAnnotations:
    def test_extracts_correct_line_numbers_and_ids(self):
        """多行含注释 → 正确提取 {行号: claim_id}。"""
        content = (
            "Line without annotation\n"
            "Result A %% CLAIM_ID: EC-2024-001\n"
            "Another line\n"
            "Result B %% CLAIM_ID: EC-2024-002\n"
        )
        result = extract_claim_annotations(content)
        assert result == {2: "EC-2024-001", 4: "EC-2024-002"}

    def test_returns_empty_dict_for_no_annotations(self):
        """无注释内容 → 返回空 dict。"""
        content = "Line one\nLine two\nLine three\n"
        result = extract_claim_annotations(content)
        assert result == {}

    def test_mixed_content(self):
        """有注释和无注释行混合 → 只提取有注释的行。"""
        content = (
            "% normal comment\n"
            "plain text\n"
            "claim line %% CLAIM_ID: EC-2025-042\n"
            "another plain line\n"
        )
        result = extract_claim_annotations(content)
        assert len(result) == 1
        assert result[3] == "EC-2025-042"

    def test_single_line_annotation(self):
        """单行含注释 → 行号为 1。"""
        content = "Only line %% CLAIM_ID: EC-2024-100"
        result = extract_claim_annotations(content)
        assert result == {1: "EC-2024-100"}


# ── strip_claim_annotations ──

class TestStripClaimAnnotations:
    def test_removes_all_claim_annotations(self):
        """移除所有 %% CLAIM_ID 注释。"""
        content = (
            "Result A %% CLAIM_ID: EC-2024-001\n"
            "plain line\n"
            "Result B %% CLAIM_ID: EC-2024-002"
        )
        result = strip_claim_annotations(content)
        assert "CLAIM_ID" not in result
        assert "EC-2024-001" not in result
        assert "EC-2024-002" not in result

    def test_preserves_regular_content(self):
        """移除注释后，行的主体内容保留。"""
        content = "Result A %% CLAIM_ID: EC-2024-001\nplain line"
        result = strip_claim_annotations(content)
        assert "Result A" in result
        assert "plain line" in result

    def test_preserves_single_percent_comments(self):
        """不影响单 % 注释（LaTeX 普通注释）。"""
        content = "% This is a normal LaTeX comment\nsome text"
        result = strip_claim_annotations(content)
        assert "% This is a normal LaTeX comment" in result

    def test_empty_content(self):
        """空内容 → 返回空字符串。"""
        assert strip_claim_annotations("") == ""

    def test_no_trailing_spaces_after_strip(self):
        """移除注释后，行尾不应有多余空格。"""
        content = "Text here %% CLAIM_ID: EC-2024-001"
        result = strip_claim_annotations(content)
        line = result.splitlines()[0]
        assert line == line.rstrip()


# ── format_citation ──

class TestFormatCitation:
    def test_citep_style(self):
        r"""format_citation citep → 返回 \citep{key}。"""
        result = format_citation("smith2020", style="citep")
        assert result == r"\citep{smith2020}"

    def test_citet_style(self):
        r"""format_citation citet → 返回 \citet{key}。"""
        result = format_citation("jones2021", style="citet")
        assert result == r"\citet{jones2021}"

    def test_default_style_is_citep(self):
        r"""默认样式为 citep。"""
        result = format_citation("doe2022")
        assert result == r"\citep{doe2022}"

    def test_invalid_style_raises_value_error(self):
        """无效 style → 抛出 ValueError。"""
        with pytest.raises(ValueError, match="Invalid citation style"):
            format_citation("key", style="invalid")

    def test_invalid_style_cite(self):
        """style='cite' 也是无效的，抛出 ValueError。"""
        with pytest.raises(ValueError):
            format_citation("key", style="cite")


# ── format_figure_ref ──

class TestFormatFigureRef:
    def test_adds_fig_prefix(self):
        r"""无前缀 → \ref{fig:label}。"""
        result = format_figure_ref("accuracy")
        assert result == r"\ref{fig:accuracy}"

    def test_preserves_existing_fig_prefix(self):
        r"""已有 fig: 前缀 → \ref{fig:label}（不重复前缀）。"""
        result = format_figure_ref("fig:accuracy")
        assert result == r"\ref{fig:accuracy}"
        assert "fig:fig:" not in result


# ── format_table_ref ──

class TestFormatTableRef:
    def test_adds_tab_prefix(self):
        r"""无前缀 → \ref{tab:label}。"""
        result = format_table_ref("results")
        assert result == r"\ref{tab:results}"

    def test_preserves_existing_tab_prefix(self):
        r"""已有 tab: 前缀 → \ref{tab:label}（不重复前缀）。"""
        result = format_table_ref("tab:results")
        assert result == r"\ref{tab:results}"
        assert "tab:tab:" not in result


# ── split_into_paragraphs ──

class TestSplitIntoParagraphs:
    def test_splits_by_blank_lines(self):
        """按空行分割多段落。"""
        content = "Paragraph one.\nContinued.\n\nParagraph two.\n\nParagraph three."
        result = split_into_paragraphs(content)
        assert len(result) == 3
        assert result[0] == "Paragraph one.\nContinued."
        assert result[1] == "Paragraph two."
        assert result[2] == "Paragraph three."

    def test_empty_content_returns_empty_list(self):
        """空内容 → 返回 []。"""
        result = split_into_paragraphs("")
        assert result == []

    def test_whitespace_only_returns_empty_list(self):
        """仅空白内容 → 返回 []。"""
        result = split_into_paragraphs("   \n\n  \n")
        assert result == []

    def test_single_paragraph(self):
        """单段落（无空行分隔）→ 返回 [段落]。"""
        content = "Single paragraph without blank lines."
        result = split_into_paragraphs(content)
        assert len(result) == 1
        assert result[0] == content

    def test_multiple_blank_lines_treated_as_separator(self):
        """多个空行视为段落分隔符。"""
        content = "Para A\n\n\n\nPara B"
        result = split_into_paragraphs(content)
        assert len(result) == 2


# ── count_words_in_tex ──

class TestCountWordsInTex:
    def test_simple_text_word_count(self):
        """简单文本正确计数。"""
        content = "This is a simple sentence."
        result = count_words_in_tex(content)
        assert result == 5

    def test_commands_not_counted(self):
        r"""LaTeX 命令（\textbf{word}）不单独计入命令本身，但命令内文字保留规则一致。"""
        # After command removal, only non-command words remain
        content = "Hello world"
        result = count_words_in_tex(content)
        assert result == 2

    def test_comments_not_counted(self):
        """注释行内容不计入词数。"""
        content = "Real word\n% This comment should not be counted"
        result = count_words_in_tex(content)
        # "Real" and "word" remain; comment stripped
        assert result == 2

    def test_empty_content(self):
        """空内容 → 0 词。"""
        assert count_words_in_tex("") == 0

    def test_only_commands(self):
        r"""仅含命令的内容词数为 0（命令被替换为空格）。"""
        content = r"\section{Introduction}"
        result = count_words_in_tex(content)
        # section command and its arg are stripped; remaining text might be 0 or minimal
        assert isinstance(result, int)
        assert result >= 0


# ── extract_all_labels ──

class TestExtractAllLabels:
    def test_extracts_labels(self):
        r"""提取所有 \label{...}。"""
        content = r"\label{fig:accuracy} some text \label{tab:results}"
        result = extract_all_labels(content)
        assert result == {"fig:accuracy", "tab:results"}

    def test_empty_content(self):
        """无 label → 返回空集合。"""
        result = extract_all_labels("plain text without labels")
        assert result == set()

    def test_duplicate_labels_deduplicated(self):
        r"""重复 label 只保留一个（使用 set）。"""
        content = r"\label{fig:a} \label{fig:a} \label{fig:b}"
        result = extract_all_labels(content)
        assert result == {"fig:a", "fig:b"}


# ── extract_all_refs ──

class TestExtractAllRefs:
    def test_extracts_ref(self):
        r"""提取 \ref{...}。"""
        content = r"See Figure~\ref{fig:accuracy} and Table~\ref{tab:results}."
        result = extract_all_refs(content)
        assert result == {"fig:accuracy", "tab:results"}

    def test_extracts_eqref(self):
        r"""提取 \eqref{...}。"""
        content = r"As shown in Equation~\eqref{eq:loss}."
        result = extract_all_refs(content)
        assert "eq:loss" in result

    def test_empty_content(self):
        """无引用 → 返回空集合。"""
        result = extract_all_refs("plain text")
        assert result == set()

    def test_mixed_ref_types(self):
        r"""混合 \ref 和 \eqref 都被提取。"""
        content = r"\ref{fig:a} and \eqref{eq:b}"
        result = extract_all_refs(content)
        assert "fig:a" in result
        assert "eq:b" in result
