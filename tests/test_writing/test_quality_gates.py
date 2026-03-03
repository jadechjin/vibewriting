"""Tests for vibewriting.writing.quality_gates module."""

from __future__ import annotations

import pytest

from vibewriting.writing.quality_gates import (
    GateReport,
    GateResult,
    _extract_citations,
    _extract_claim_annotations,
    _extract_labels,
    _extract_refs,
    _is_no_cite_exempt,
    _parse_paragraphs,
    check_asset_coverage,
    check_citation_coverage,
    check_claim_traceability,
    check_cross_references,
    check_terminology_consistency,
    run_all_gates,
)


# ──────────────────────────────────────────────
# Parser tests
# ──────────────────────────────────────────────

class TestParseParagraphs:
    def test_empty_content_returns_empty_list(self):
        assert _parse_paragraphs("") == []

    def test_whitespace_only_returns_empty_list(self):
        assert _parse_paragraphs("   \n\n  ") == []

    def test_multiple_paragraphs_split_by_blank_line(self):
        content = "First paragraph text.\n\nSecond paragraph text."
        result = _parse_paragraphs(content)
        assert len(result) == 2
        assert result[0] == "First paragraph text."
        assert result[1] == "Second paragraph text."

    def test_preserves_comment_lines_within_paragraphs(self):
        content = "Some text here.\n%% CLAIM_ID: EC-2026-001\nMore text."
        result = _parse_paragraphs(content)
        assert len(result) == 1
        assert "%% CLAIM_ID: EC-2026-001" in result[0]

    def test_multiple_blank_lines_still_splits_correctly(self):
        content = "Para one.\n\n\n\nPara two."
        result = _parse_paragraphs(content)
        assert len(result) == 2

    def test_single_paragraph_no_split(self):
        content = "Only one paragraph here."
        result = _parse_paragraphs(content)
        assert len(result) == 1
        assert result[0] == "Only one paragraph here."


class TestExtractCitations:
    def test_single_citep_key(self):
        content = r"See \citep{smith2020} for details."
        result = _extract_citations(content)
        assert result == ["smith2020"]

    def test_multiple_keys_in_citep(self):
        content = r"See \citep{smith2020, jones2021} for details."
        result = _extract_citations(content)
        assert result == ["smith2020", "jones2021"]

    def test_citet_key(self):
        content = r"\citet{brown2019} showed that..."
        result = _extract_citations(content)
        assert result == ["brown2019"]

    def test_no_citations_returns_empty_list(self):
        content = "No references here at all."
        result = _extract_citations(content)
        assert result == []

    def test_mixed_citep_and_citet(self):
        content = r"\citet{jones2021} and \citep{smith2020} both agree."
        result = _extract_citations(content)
        assert "jones2021" in result
        assert "smith2020" in result

    def test_keys_are_stripped_of_whitespace(self):
        content = r"\citep{ key1 , key2 }"
        result = _extract_citations(content)
        assert result == ["key1", "key2"]


class TestExtractRefs:
    def test_extracts_fig_ref(self):
        content = r"As shown in \ref{fig:results}, the accuracy improves."
        result = _extract_refs(content)
        assert "fig:results" in result

    def test_extracts_eqref(self):
        content = r"From \eqref{eq:loss}, we derive..."
        result = _extract_refs(content)
        assert "eq:loss" in result

    def test_extracts_multiple_refs(self):
        content = r"See \ref{fig:main} and \ref{tab:results}."
        result = _extract_refs(content)
        assert "fig:main" in result
        assert "tab:results" in result

    def test_no_refs_returns_empty_set(self):
        content = "No references at all."
        result = _extract_refs(content)
        assert result == set()


class TestExtractLabels:
    def test_extracts_single_label(self):
        content = r"\label{fig:overview} shows the system."
        result = _extract_labels(content)
        assert "fig:overview" in result

    def test_extracts_multiple_labels(self):
        content = r"\label{fig:a} and \label{tab:b}"
        result = _extract_labels(content)
        assert "fig:a" in result
        assert "tab:b" in result

    def test_no_labels_returns_empty_set(self):
        content = "No labels here."
        result = _extract_labels(content)
        assert result == set()


class TestExtractClaimAnnotations:
    def test_extracts_claim_id(self):
        content = "%% CLAIM_ID: EC-2026-001\nSome claim text."
        result = _extract_claim_annotations(content)
        assert result == ["EC-2026-001"]

    def test_extracts_multiple_claim_ids(self):
        content = (
            "%% CLAIM_ID: EC-2026-001\nFirst claim.\n\n"
            "%% CLAIM_ID: EC-2026-002\nSecond claim."
        )
        result = _extract_claim_annotations(content)
        assert "EC-2026-001" in result
        assert "EC-2026-002" in result

    def test_no_claim_ids_returns_empty_list(self):
        content = "Regular paragraph without claims."
        result = _extract_claim_annotations(content)
        assert result == []

    def test_handles_extra_spaces_in_annotation(self):
        content = "%%  CLAIM_ID:  EC-2026-005\nText."
        result = _extract_claim_annotations(content)
        assert "EC-2026-005" in result


class TestIsNoCiteExempt:
    def test_paragraph_with_no_cite_annotation_is_exempt(self):
        para = "%% NO_CITE: common knowledge\nWater boils at 100 degrees."
        assert _is_no_cite_exempt(para) is True

    def test_paragraph_without_no_cite_is_not_exempt(self):
        para = "This needs a citation \\citep{someone2020}."
        assert _is_no_cite_exempt(para) is False

    def test_plain_paragraph_is_not_exempt(self):
        para = "A simple statement that should be cited."
        assert _is_no_cite_exempt(para) is False


# ──────────────────────────────────────────────
# Gate 1: Citation Coverage
# ──────────────────────────────────────────────

class TestCheckCitationCoverage:
    def test_method_section_with_citations_passes(self):
        content = (
            r"We propose \citep{smith2020} as a baseline."
            "\n\n"
            r"The loss function \citep{jones2021} is computed as follows."
        )
        result = check_citation_coverage(content, "sec:method", "method")
        assert result.passed is True
        assert result.score >= 0.5

    def test_method_section_without_citations_fails(self):
        content = "We describe the methodology.\n\nThe algorithm proceeds as follows."
        result = check_citation_coverage(content, "sec:method", "method")
        assert result.passed is False
        assert result.score < 0.5

    def test_conclusion_section_always_passes(self):
        content = "In this work, we presented a novel approach."
        result = check_citation_coverage(content, "sec:conclusion", "conclusion")
        assert result.passed is True

    def test_appendix_section_always_passes(self):
        content = "Proof of Theorem 1 follows."
        result = check_citation_coverage(content, "sec:appendix", "appendix")
        assert result.passed is True

    def test_no_cite_exempt_paragraphs_are_excluded(self):
        content = (
            "%% NO_CITE: common knowledge\n"
            "Water boils at 100 degrees.\n\n"
            "%% NO_CITE: common knowledge\n"
            "The sky is blue."
        )
        result = check_citation_coverage(content, "sec:method", "method")
        assert result.passed is True

    def test_introduction_with_at_least_one_citation_passes(self):
        content = (
            r"Background: \citep{smith2020} provides context."
            "\n\n"
            "Second paragraph without citation."
        )
        result = check_citation_coverage(content, "sec:intro", "introduction")
        assert result.passed is True

    def test_introduction_without_any_citation_fails(self):
        content = "First paragraph.\n\nSecond paragraph."
        result = check_citation_coverage(content, "sec:intro", "introduction")
        assert result.passed is False

    def test_related_work_passes_with_citations(self):
        content = (
            r"Prior work \citep{jones2021} explored this."
            "\n\n"
            "Another paragraph without citation."
        )
        result = check_citation_coverage(content, "sec:related", "related-work")
        assert result.passed is True


# ──────────────────────────────────────────────
# Gate 2: Asset Coverage
# ──────────────────────────────────────────────

class TestCheckAssetCoverage:
    def test_experiments_with_fig_ref_passes(self):
        content = r"As shown in \ref{fig:accuracy}, performance improves."
        result = check_asset_coverage(content, "sec:exp", "experiments", [])
        assert result.passed is True

    def test_experiments_without_fig_or_tab_ref_fails(self):
        content = "We evaluated on standard benchmarks."
        result = check_asset_coverage(content, "sec:exp", "experiments", [])
        assert result.passed is False

    def test_experiments_with_tab_ref_passes(self):
        content = r"Results are shown in \ref{tab:comparison}."
        result = check_asset_coverage(content, "sec:exp", "experiments", [])
        assert result.passed is True

    def test_introduction_without_ref_passes(self):
        content = "We introduce a novel method for text generation."
        result = check_asset_coverage(content, "sec:intro", "introduction", [])
        assert result.passed is True

    def test_method_section_passes_without_refs(self):
        content = "The algorithm is defined as follows."
        result = check_asset_coverage(content, "sec:method", "method", [])
        assert result.passed is True


# ──────────────────────────────────────────────
# Gate 3: Claim Traceability
# ──────────────────────────────────────────────

class TestCheckClaimTraceability:
    def test_with_sufficient_claim_coverage_passes(self):
        content = (
            "%% CLAIM_ID: EC-2026-001\nFirst claim.\n\n"
            "%% CLAIM_ID: EC-2026-002\nSecond claim.\n\n"
            "%% CLAIM_ID: EC-2026-003\nThird claim."
        )
        expected = ["EC-2026-001", "EC-2026-002", "EC-2026-003"]
        result = check_claim_traceability(content, "sec:method", expected)
        assert result.passed is True
        assert result.score == 1.0

    def test_without_any_claim_ids_fails(self):
        content = "No claims annotated here."
        expected = ["EC-2026-001", "EC-2026-002", "EC-2026-003"]
        result = check_claim_traceability(content, "sec:method", expected)
        assert result.passed is False
        assert result.score == 0.0

    def test_empty_expected_claim_ids_passes_with_score_one(self):
        content = "Some section content without claims."
        result = check_claim_traceability(content, "sec:intro", [])
        assert result.passed is True
        assert result.score == 1.0

    def test_partial_coverage_above_threshold_passes(self):
        content = (
            "%% CLAIM_ID: EC-2026-001\nFirst claim.\n\n"
            "%% CLAIM_ID: EC-2026-002\nSecond claim."
        )
        expected = ["EC-2026-001", "EC-2026-002", "EC-2026-003", "EC-2026-004"]
        result = check_claim_traceability(content, "sec:method", expected)
        assert result.passed is True
        assert result.score == 0.5

    def test_partial_coverage_below_threshold_fails(self):
        content = "%% CLAIM_ID: EC-2026-001\nFirst claim."
        expected = [f"EC-2026-{i:03d}" for i in range(1, 11)]
        result = check_claim_traceability(content, "sec:method", expected)
        assert result.passed is False
        assert result.score < 0.3


# ──────────────────────────────────────────────
# Gate 4: Cross-ref Integrity
# ──────────────────────────────────────────────

class TestCheckCrossReferences:
    def test_no_dangling_refs_passes(self):
        content = r"See \ref{fig:main} for results."
        all_labels = {"fig:main", "tab:results"}
        result = check_cross_references(content, "sec:exp", all_labels)
        assert result.passed is True

    def test_dangling_ref_fails(self):
        content = r"See \ref{fig:missing} for results."
        all_labels = {"fig:main", "tab:results"}
        result = check_cross_references(content, "sec:exp", all_labels)
        assert result.passed is False
        assert any("fig:missing" in d for d in result.details)

    def test_unreferenced_label_passes_with_warning(self):
        content = r"\label{fig:local} This figure is not referenced."
        all_labels = {"fig:local"}
        result = check_cross_references(content, "sec:exp", all_labels)
        assert result.passed is True
        assert any("Warning" in d or "not referenced" in d for d in result.details)

    def test_no_refs_no_labels_passes(self):
        content = "Plain text without any LaTeX cross-references."
        all_labels: set[str] = set()
        result = check_cross_references(content, "sec:intro", all_labels)
        assert result.passed is True


# ──────────────────────────────────────────────
# Gate 5: Terminology Consistency
# ──────────────────────────────────────────────

class TestCheckTerminologyConsistency:
    def test_with_matching_terms_passes(self):
        content = "We use a transformer architecture for encoding."
        glossary = {"transformer": "A self-attention based neural network model"}
        result = check_terminology_consistency(content, "sec:method", glossary, {})
        assert result.passed is True

    def test_with_no_glossary_or_symbols_passes(self):
        content = "General text without terminology."
        result = check_terminology_consistency(content, "sec:intro", {}, {})
        assert result.passed is True

    def test_unused_glossary_term_generates_detail_but_passes(self):
        content = "This section does not mention the baseline method."
        glossary = {"attention": "A mechanism for weighting sequence elements"}
        result = check_terminology_consistency(content, "sec:method", glossary, {})
        assert result.passed is True
        assert any("attention" in d for d in result.details)

    def test_symbol_found_in_content_noted_in_details(self):
        content = r"The learning rate \alpha controls convergence."
        symbols = {r"\alpha": "learning rate"}
        result = check_terminology_consistency(content, "sec:method", {}, symbols)
        assert result.passed is True


# ──────────────────────────────────────────────
# Gate Report and run_all_gates
# ──────────────────────────────────────────────

class TestGateReport:
    def test_all_passed_true_when_all_gates_pass(self):
        results = [
            GateResult("gate_a", True, 1.0),
            GateResult("gate_b", True, 0.8),
        ]
        report = GateReport(results=results)
        assert report.all_passed is True

    def test_all_passed_false_when_any_gate_fails(self):
        results = [
            GateResult("gate_a", True, 1.0),
            GateResult("gate_b", False, 0.2),
        ]
        report = GateReport(results=results)
        assert report.all_passed is False

    def test_summary_format_is_correct(self):
        results = [
            GateResult("gate_a", True, 1.0),
            GateResult("gate_b", False, 0.2),
            GateResult("gate_c", True, 0.9),
        ]
        report = GateReport(results=results)
        assert report.summary == "2/3 gates passed"

    def test_summary_all_passed(self):
        results = [GateResult("gate_a", True, 1.0)]
        report = GateReport(results=results)
        assert report.summary == "1/1 gates passed"


class TestCheckTerminologyConsistencyEnhanced:
    def test_ghost_term_generates_warning_detail(self):
        """glossary 中的 term 在 tex 中未出现 -> warning in details."""
        content = "We use a basic model for prediction."
        glossary = {"attention": "A mechanism for weighting"}
        result = check_terminology_consistency(content, "sec:method", glossary, {})
        # 虽然 passed（warning 级别），但 details 中应包含 ghost term 信息
        assert any("ghost" in d.lower() or "not used" in d.lower() for d in result.details)

    def test_undefined_term_in_emph_warning(self):
        r"""\\emph{} 中的术语不在 glossary -> warning in details."""
        content = r"We introduce \emph{novel attention} mechanism."
        glossary = {}  # 空 glossary
        result = check_terminology_consistency(content, "sec:method", glossary, {})
        # warning 不影响 passed
        assert result.passed is True

    def test_all_terms_used_no_ghost_terms(self):
        content = "We use the transformer architecture with attention mechanism."
        glossary = {"transformer": "A model", "attention": "A mechanism"}
        result = check_terminology_consistency(content, "sec:method", glossary, {})
        assert result.passed is True
        assert result.score == 1.0

    def test_emph_term_not_in_glossary_generates_warning_detail(self):
        r"""\\emph{} 中的术语不在 glossary -> 出现 warning 并降低 score."""
        content = r"We propose \emph{adaptive learning} to handle distribution shift."
        glossary = {}
        result = check_terminology_consistency(content, "sec:method", glossary, {})
        assert result.passed is True
        assert any("adaptive learning" in d or "not defined" in d.lower() for d in result.details)

    def test_textbf_term_not_in_glossary_generates_warning_detail(self):
        r"""\\textbf{} 中的术语不在 glossary -> warning in details."""
        content = r"The \textbf{baseline model} is compared against ours."
        glossary = {}
        result = check_terminology_consistency(content, "sec:method", glossary, {})
        assert result.passed is True
        assert any("baseline model" in d or "not defined" in d.lower() for d in result.details)

    def test_score_reduces_with_ghost_terms(self):
        """ghost term 存在时 score 应小于 1.0."""
        content = "This section does not mention the transformer at all."
        glossary = {"attention": "A mechanism", "transformer": "A model"}
        result = check_terminology_consistency(content, "sec:method", glossary, {})
        assert result.passed is True
        assert result.score < 1.0

    def test_other_sections_terms_inconsistency_warning(self):
        """跨章节术语定义不一致时应产生 warning。"""
        content = "We use the transformer model."
        glossary = {"transformer": "A seq2seq model"}
        other_sections = {"sec:intro": {"transformer": "A different definition"}}
        result = check_terminology_consistency(
            content, "sec:method", glossary, {}, other_sections_terms=other_sections
        )
        assert result.passed is True
        assert any("inconsistent" in d.lower() for d in result.details)

    def test_no_issues_when_all_terms_consistent(self):
        """术语全部一致时无 inconsistency warning。"""
        content = "We use transformer and attention."
        glossary = {"transformer": "A model", "attention": "A mechanism"}
        other_sections = {"sec:intro": {"transformer": "A model"}}
        result = check_terminology_consistency(
            content, "sec:method", glossary, {}, other_sections_terms=other_sections
        )
        assert result.passed is True
        assert not any("inconsistent" in d.lower() for d in result.details)

    def test_backward_compatible_without_other_sections_terms(self):
        """旧签名（无 other_sections_terms）应仍可正常工作。"""
        content = "We use a transformer model."
        glossary = {"transformer": "A model"}
        result = check_terminology_consistency(content, "sec:method", glossary, {})
        assert result.passed is True


class TestRunAllGates:
    def test_returns_gate_report_with_five_results(self):
        content = (
            r"We propose \citep{smith2020} as the baseline."
            "\n\n"
            r"Results in \ref{fig:main} confirm our hypothesis."
            "\n"
            r"\label{fig:main}"
            "\n"
            "%% CLAIM_ID: EC-2026-001\nOur main claim."
        )
        report = run_all_gates(
            tex_content=content,
            section_id="sec:experiments",
            section_type="experiments",
            expected_claim_ids=["EC-2026-001"],
            expected_asset_ids=["fig:main"],
            all_labels={"fig:main"},
            glossary_terms={"baseline": "comparison model"},
            symbol_entries={},
        )
        assert isinstance(report, GateReport)
        assert len(report.results) == 5

    def test_all_passed_is_correct_on_valid_content(self):
        content = (
            r"We use \citep{smith2020} as our baseline."
            "\n\n"
            r"Performance is shown in \ref{fig:results}."
            "\n"
            r"\label{fig:results}"
            "\n"
            "%% CLAIM_ID: EC-2026-001\nMain claim here."
        )
        report = run_all_gates(
            tex_content=content,
            section_id="sec:experiments",
            section_type="experiments",
            expected_claim_ids=["EC-2026-001"],
            all_labels={"fig:results"},
        )
        assert isinstance(report, GateReport)
        gate_names = [r.gate_name for r in report.results]
        assert "citation_coverage" in gate_names
        assert "asset_coverage" in gate_names
        assert "claim_traceability" in gate_names
        assert "cross_ref_integrity" in gate_names
        assert "terminology_consistency" in gate_names

    def test_run_all_gates_with_empty_content(self):
        report = run_all_gates(
            tex_content="",
            section_id="sec:conclusion",
            section_type="conclusion",
        )
        assert isinstance(report, GateReport)
        assert len(report.results) == 5
