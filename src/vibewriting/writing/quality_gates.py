"""Quality gates for validating LaTeX section content.

Five gate checks:
1. Citation Coverage - by paragraph type
2. Asset Coverage - figure/table references
3. Claim Traceability - %% CLAIM_ID annotations
4. Cross-ref Integrity - \\label/\\ref consistency
5. Terminology Consistency - glossary/symbol compliance
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class GateResult:
    """Result of a single quality gate check."""

    gate_name: str
    passed: bool
    score: float  # 0.0 - 1.0
    details: list[str] = field(default_factory=list)
    section_id: str = ""


@dataclass
class GateReport:
    """Aggregate report from all quality gates."""

    results: list[GateResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def summary(self) -> str:
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        return f"{passed}/{total} gates passed"


# ──────────────────────────────────────────────
# Compiled regex patterns
# ──────────────────────────────────────────────

_CITE_RE = re.compile(r"\\cite[pt]\{([^}]+)\}")
_REF_RE = re.compile(r"\\(?:eq)?ref\{([^}]+)\}")
_LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
_CLAIM_RE = re.compile(r"%%\s*CLAIM_ID:\s*(EC-\d{4}-\d{3})")
_NO_CITE_RE = re.compile(r"%%\s*NO_CITE:")


# ──────────────────────────────────────────────
# Internal parsers
# ──────────────────────────────────────────────

def _parse_paragraphs(tex_content: str) -> list[str]:
    """Split LaTeX content into paragraphs by blank lines.

    Preserves comment lines within paragraphs.
    Strips leading/trailing whitespace from each paragraph.
    Returns non-empty paragraphs only.
    """
    if not tex_content.strip():
        return []
    raw_paragraphs = re.split(r"\n\s*\n", tex_content)
    return [p.strip() for p in raw_paragraphs if p.strip()]


def _extract_citations(tex_content: str) -> list[str]:
    r"""Extract all citation keys from \citep{} and \citet{} commands.

    Handles multiple keys: \citep{key1, key2} -> ["key1", "key2"]
    """
    keys: list[str] = []
    for match in _CITE_RE.finditer(tex_content):
        raw_keys = match.group(1)
        for key in raw_keys.split(","):
            stripped = key.strip()
            if stripped:
                keys.append(stripped)
    return keys


def _extract_refs(tex_content: str) -> set[str]:
    r"""Extract all referenced labels from \ref{} and \eqref{} commands."""
    return {m.group(1) for m in _REF_RE.finditer(tex_content)}


def _extract_labels(tex_content: str) -> set[str]:
    r"""Extract all defined labels from \label{} commands."""
    return {m.group(1) for m in _LABEL_RE.finditer(tex_content)}


def _extract_claim_annotations(tex_content: str) -> list[str]:
    """Extract all CLAIM_ID values from %% CLAIM_ID: EC-XXXX-XXX annotations."""
    return _CLAIM_RE.findall(tex_content)


def _is_no_cite_exempt(paragraph: str) -> bool:
    """Check if a paragraph has a %% NO_CITE exemption annotation."""
    return bool(_NO_CITE_RE.search(paragraph))


# ──────────────────────────────────────────────
# Gate 1: Citation Coverage
# ──────────────────────────────────────────────

def check_citation_coverage(
    tex_content: str,
    section_id: str,
    section_type: Literal[
        "introduction", "related-work", "method",
        "experiments", "conclusion", "appendix",
    ],
) -> GateResult:
    """Check citation coverage by paragraph type.

    Strategy:
    - introduction/related-work: recommend (score = ratio, pass if > 0)
    - method/experiments: require (pass if score >= 0.5)
    - conclusion/appendix: always pass
    - Paragraphs with %% NO_CITE are exempted
    """
    if section_type in ("conclusion", "appendix"):
        return GateResult(
            gate_name="citation_coverage",
            passed=True,
            score=1.0,
            details=["Section type does not require citations."],
            section_id=section_id,
        )

    paragraphs = _parse_paragraphs(tex_content)
    if not paragraphs:
        score = 0.0
        details = ["No paragraphs found."]
        passed = section_type in ("introduction", "related-work") and False
        if section_type in ("introduction", "related-work"):
            passed = score > 0
        else:
            passed = score >= 0.5
        return GateResult(
            gate_name="citation_coverage",
            passed=passed,
            score=score,
            details=details,
            section_id=section_id,
        )

    eligible: list[str] = []
    for para in paragraphs:
        if not _is_no_cite_exempt(para):
            eligible.append(para)

    if not eligible:
        return GateResult(
            gate_name="citation_coverage",
            passed=True,
            score=1.0,
            details=["All paragraphs are NO_CITE exempt."],
            section_id=section_id,
        )

    cited_count = sum(
        1 for para in eligible if _extract_citations(para)
    )
    score = cited_count / len(eligible)
    details: list[str] = [
        f"{cited_count}/{len(eligible)} eligible paragraphs have citations."
    ]

    if section_type in ("introduction", "related-work"):
        passed = score > 0
        if not passed:
            details.append("Recommendation: add citations to at least one paragraph.")
    else:
        passed = score >= 0.5
        if not passed:
            details.append(
                f"Required: >= 50% paragraph citation coverage; got {score:.0%}."
            )

    return GateResult(
        gate_name="citation_coverage",
        passed=passed,
        score=score,
        details=details,
        section_id=section_id,
    )


# ──────────────────────────────────────────────
# Gate 2: Asset Coverage
# ──────────────────────────────────────────────

def check_asset_coverage(
    tex_content: str,
    section_id: str,
    section_type: str,
    expected_asset_ids: list[str],
) -> GateResult:
    """Check figure/table reference coverage.

    - experiments section: must have at least 1 \\ref{fig:} or \\ref{tab:}
    - Other sections: pass with any refs
    """
    refs = _extract_refs(tex_content)
    fig_tab_refs = {r for r in refs if r.startswith("fig:") or r.startswith("tab:")}

    details: list[str] = []
    missing: list[str] = []

    if expected_asset_ids:
        for asset_id in expected_asset_ids:
            if asset_id not in refs:
                missing.append(asset_id)
        if missing:
            details.append(f"Missing asset refs: {', '.join(missing)}")

    if section_type == "experiments":
        passed = len(fig_tab_refs) >= 1
        score = 1.0 if passed else 0.0
        if not passed:
            details.append(
                "experiments section must reference at least one figure or table."
            )
        else:
            details.append(f"Found {len(fig_tab_refs)} figure/table reference(s).")
        return GateResult(
            gate_name="asset_coverage",
            passed=passed,
            score=score,
            details=details,
            section_id=section_id,
        )

    if expected_asset_ids and missing:
        score = (len(expected_asset_ids) - len(missing)) / len(expected_asset_ids)
        passed = len(missing) == 0
    else:
        score = 1.0
        passed = True
        if fig_tab_refs:
            details.append(f"Found {len(fig_tab_refs)} figure/table reference(s).")

    return GateResult(
        gate_name="asset_coverage",
        passed=passed,
        score=score,
        details=details,
        section_id=section_id,
    )


# ──────────────────────────────────────────────
# Gate 3: Claim Traceability
# ──────────────────────────────────────────────

def check_claim_traceability(
    tex_content: str,
    section_id: str,
    expected_claim_ids: list[str],
) -> GateResult:
    """Check CLAIM_ID annotation coverage.

    - Extract %% CLAIM_ID annotations
    - Compare with expected claim_ids
    - score = found / expected
    - Pass if score >= 0.3 (at least 30% of expected claims annotated)
    """
    if not expected_claim_ids:
        return GateResult(
            gate_name="claim_traceability",
            passed=True,
            score=1.0,
            details=["No expected claims specified."],
            section_id=section_id,
        )

    found_claims = set(_extract_claim_annotations(tex_content))
    expected_set = set(expected_claim_ids)
    matched = found_claims & expected_set

    score = len(matched) / len(expected_set)
    details: list[str] = [
        f"{len(matched)}/{len(expected_set)} expected claims annotated."
    ]
    missing = expected_set - found_claims
    if missing:
        details.append(f"Missing claim annotations: {', '.join(sorted(missing))}")

    passed = score >= 0.3

    return GateResult(
        gate_name="claim_traceability",
        passed=passed,
        score=score,
        details=details,
        section_id=section_id,
    )


# ──────────────────────────────────────────────
# Gate 4: Cross-ref Integrity
# ──────────────────────────────────────────────

def check_cross_references(
    tex_content: str,
    section_id: str,
    all_labels: set[str],
) -> GateResult:
    """Check LaTeX cross-reference integrity.

    - Find \\ref{} to labels not in all_labels (dangling refs)
    - Find \\label{} in current section not referenced anywhere
    - Pass if no dangling refs (unreferenced labels are just warnings)
    """
    refs = _extract_refs(tex_content)
    local_labels = _extract_labels(tex_content)

    dangling = refs - all_labels
    unreferenced = local_labels - refs

    details: list[str] = []
    if dangling:
        details.append(f"Dangling refs (undefined labels): {', '.join(sorted(dangling))}")
    if unreferenced:
        details.append(f"Warning: labels defined but not referenced locally: {', '.join(sorted(unreferenced))}")

    passed = len(dangling) == 0
    score = 1.0 if passed else max(0.0, 1.0 - len(dangling) / max(len(refs), 1))

    if passed and not details:
        details.append("All cross-references are valid.")

    return GateResult(
        gate_name="cross_ref_integrity",
        passed=passed,
        score=score,
        details=details,
        section_id=section_id,
    )


# ──────────────────────────────────────────────
# Gate 5: Terminology Consistency
# ──────────────────────────────────────────────

_EMPH_RE = re.compile(r"\\(?:textbf|emph)\{([^}]+)\}")


def _extract_emphasized_terms(tex_content: str) -> list[str]:
    r"""Extract terms inside \textbf{} or \emph{} commands."""
    return [m.group(1).strip() for m in _EMPH_RE.finditer(tex_content)]


def check_terminology_consistency(
    tex_content: str,
    section_id: str,
    glossary_terms: dict[str, str],
    symbol_entries: dict[str, str],
    other_sections_terms: dict[str, dict[str, str]] | None = None,
) -> GateResult:
    """Check terminology and symbol usage consistency.

    Checks:
    1. Ghost term detection: glossary terms not used in this section -> warning in details
    2. Undefined term detection: \\textbf{}/\\emph{} terms not in glossary -> warning in details
    3. Cross-section inconsistency: same term used differently across sections

    - passed = True for warnings (ghost/undefined terms are warning-level)
    - score = computed based on warning count
    - details records all findings
    """
    details: list[str] = []
    warnings: list[str] = []

    # Check 1: Ghost terms - glossary terms not used in this section
    for term in glossary_terms:
        if term.lower() in tex_content.lower():
            details.append(f"Term '{term}' found in section.")
        else:
            warning = f"Warning: ghost term '{term}' in glossary but not used in this section."
            details.append(warning)
            warnings.append(warning)

    # Check 2: Undefined terms - emphasized terms not in glossary
    emphasized = _extract_emphasized_terms(tex_content)
    glossary_lower = {t.lower() for t in glossary_terms}
    for emph_term in emphasized:
        if emph_term.lower() not in glossary_lower:
            warning = f"Warning: emphasized term '{emph_term}' not defined in glossary."
            details.append(warning)
            warnings.append(warning)

    # Check 3: Symbol usage
    for symbol in symbol_entries:
        escaped = re.escape(symbol)
        if re.search(escaped, tex_content):
            details.append(f"Symbol '{symbol}' found in section.")

    # Check 4: Cross-section term inconsistency (if other sections provided)
    if other_sections_terms:
        for other_section_id, other_terms in other_sections_terms.items():
            for term, definition in other_terms.items():
                if term in glossary_terms and glossary_terms[term] != definition:
                    warning = (
                        f"Warning: term '{term}' has inconsistent definition "
                        f"between this section and '{other_section_id}'."
                    )
                    details.append(warning)
                    warnings.append(warning)

    # passed is True (warnings don't fail the gate, only report them)
    passed = True
    total_checks = max(len(glossary_terms) + len(symbol_entries), 1)
    score = max(0.0, 1.0 - len(warnings) / total_checks)

    if not details:
        details.append("No terminology issues detected.")

    return GateResult(
        gate_name="terminology_consistency",
        passed=passed,
        score=score,
        details=details,
        section_id=section_id,
    )


# ──────────────────────────────────────────────
# Aggregate
# ──────────────────────────────────────────────

def run_all_gates(
    tex_content: str,
    section_id: str,
    section_type: str,
    expected_claim_ids: list[str] | None = None,
    expected_asset_ids: list[str] | None = None,
    all_labels: set[str] | None = None,
    glossary_terms: dict[str, str] | None = None,
    symbol_entries: dict[str, str] | None = None,
) -> GateReport:
    """Run all quality gates and return aggregate report."""
    results: list[GateResult] = []

    valid_section_types = {
        "introduction", "related-work", "method",
        "experiments", "conclusion", "appendix",
    }
    normalized_type = section_type if section_type in valid_section_types else "appendix"

    results.append(
        check_citation_coverage(tex_content, section_id, normalized_type)  # type: ignore[arg-type]
    )

    results.append(
        check_asset_coverage(
            tex_content,
            section_id,
            section_type,
            expected_asset_ids or [],
        )
    )

    results.append(
        check_claim_traceability(
            tex_content,
            section_id,
            expected_claim_ids or [],
        )
    )

    results.append(
        check_cross_references(
            tex_content,
            section_id,
            all_labels or set(),
        )
    )

    results.append(
        check_terminology_consistency(
            tex_content,
            section_id,
            glossary_terms or {},
            symbol_entries or {},
        )
    )

    return GateReport(results=results)
