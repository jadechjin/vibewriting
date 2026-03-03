"""Shared fixtures for writing module tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from vibewriting.models.glossary import Glossary, SymbolTable
from vibewriting.models.paper_state import PaperMetrics, PaperState, SectionState


@pytest.fixture
def sample_section_states() -> list[SectionState]:
    """6 sample SectionState objects matching paper/sections/."""
    return [
        SectionState(
            section_id="introduction",
            title="引言",
            tex_file="sections/introduction.tex",
        ),
        SectionState(
            section_id="related-work",
            title="相关工作",
            tex_file="sections/related-work.tex",
        ),
        SectionState(
            section_id="method",
            title="方法",
            tex_file="sections/method.tex",
        ),
        SectionState(
            section_id="experiments",
            title="实验",
            tex_file="sections/experiments.tex",
        ),
        SectionState(
            section_id="conclusion",
            title="结论",
            tex_file="sections/conclusion.tex",
        ),
        SectionState(
            section_id="appendix",
            title="附录",
            tex_file="sections/appendix.tex",
        ),
    ]


@pytest.fixture
def sample_paper_state(sample_section_states: list[SectionState]) -> PaperState:
    """Sample PaperState in drafting phase."""
    return PaperState(
        paper_id="PS-2026-001",
        title="基于深度学习的文本生成研究",
        topic="深度学习文本生成",
        phase="drafting",
        sections=sample_section_states,
    )


@pytest.fixture
def sample_paper_metrics() -> PaperMetrics:
    """Sample PaperMetrics with typical mid-draft values."""
    return PaperMetrics(
        citation_coverage=0.75,
        claim_traceability=0.80,
        figure_coverage=0.60,
        cross_ref_integrity=True,
        terminology_consistency=False,
        total_claims=12,
        total_citations=8,
        total_figures_referenced=3,
        total_tables_referenced=2,
    )


@pytest.fixture
def sample_glossary() -> Glossary:
    """Sample Glossary with 3 terms."""
    g = Glossary()
    g = g.add_term("Transformer", "A neural network architecture based on self-attention", "introduction")
    g = g.add_term("BERT", "Bidirectional Encoder Representations from Transformers", "related-work")
    g = g.add_term("Fine-tuning", "Adapting a pre-trained model to a specific task", "method")
    return g


@pytest.fixture
def sample_symbol_table() -> SymbolTable:
    """Sample SymbolTable with 3 symbols."""
    st = SymbolTable()
    st = st.add_symbol(r"\alpha", "Learning rate", "method")
    st = st.add_symbol(r"\theta", "Model parameters", "method")
    st = st.add_symbol(r"\mathcal{L}", "Loss function", "experiments")
    return st


@pytest.fixture
def sample_tex_content() -> str:
    """Sample LaTeX section content with citations and claim annotations."""
    return r"""
\section{Introduction}

Deep learning has revolutionized natural language processing. %% NO_CITE: common knowledge

The Transformer architecture \citep{vaswani2017attention} introduced self-attention mechanisms
that achieve $O(n^2)$ complexity. %% CLAIM_ID: EC-2026-001

BERT \citep{devlin2019bert} demonstrated the effectiveness of bidirectional pre-training
for downstream tasks. %% CLAIM_ID: EC-2026-002

As shown in Figure~\ref{fig:architecture}, the model consists of multiple layers.
Table~\ref{tab:results} summarizes the experimental results.

\label{fig:architecture}
\label{tab:results}
"""


@pytest.fixture
def sample_tex_content_method() -> str:
    """Sample LaTeX method section with math and citations."""
    return r"""
\section{Method}

The proposed model follows the encoder-decoder paradigm \citep{vaswani2017attention}. %% CLAIM_ID: EC-2026-001

Let $\theta$ denote the model parameters and $\mathcal{L}$ the loss function.
The optimization objective is:
\begin{equation}
    \mathcal{L}(\theta) = -\sum_{t=1}^{T} \log p(y_t \mid y_{<t}, x; \theta)
    \label{eq:loss}
\end{equation}

The learning rate $\alpha$ is scheduled using a linear warmup strategy \citep{devlin2019bert}. %% CLAIM_ID: EC-2026-002

Figure~\ref{fig:architecture} illustrates the overall architecture.
"""


@pytest.fixture
def sample_evidence_cards() -> list[dict]:
    """Sample evidence card dicts for testing quality gates and outline generation."""
    return [
        {
            "claim_id": "EC-2026-001",
            "claim_text": "Transformer self-attention has O(n^2) complexity",
            "bib_key": "vaswani2017attention",
            "evidence_type": "theoretical",
            "tags": ["transformer", "attention", "complexity"],
            "quality_score": 9,
        },
        {
            "claim_id": "EC-2026-002",
            "claim_text": "BERT pre-training improves downstream tasks",
            "bib_key": "devlin2019bert",
            "evidence_type": "empirical",
            "tags": ["bert", "pre-training", "NLP"],
            "quality_score": 9,
        },
        {
            "claim_id": "EC-2026-003",
            "claim_text": "GPT uses autoregressive language modeling",
            "bib_key": "radford2019language",
            "evidence_type": "empirical",
            "tags": ["gpt", "language-model", "generation"],
            "quality_score": 8,
        },
    ]


@pytest.fixture
def sample_asset_manifest() -> list[dict]:
    """Sample asset manifest entries for testing figure/table references."""
    return [
        {
            "asset_id": "ASSET-2026-001",
            "kind": "figure",
            "path": "output/figures/architecture.pdf",
            "content_hash": "sha256:abc123",
            "semantic_description": "Model architecture diagram",
        },
        {
            "asset_id": "ASSET-2026-002",
            "kind": "table",
            "path": "output/tables/results.tex",
            "content_hash": "sha256:def456",
            "semantic_description": "Experimental results comparison table",
        },
    ]


@pytest.fixture
def tmp_paper_dir(tmp_path: Path) -> Path:
    """Temporary paper/ directory structure mirroring the real paper/ layout."""
    paper_dir = tmp_path / "paper"
    paper_dir.mkdir()
    (paper_dir / "sections").mkdir()
    (paper_dir / "bib").mkdir()
    (paper_dir / "figures").mkdir()
    (paper_dir / "build").mkdir()

    # Minimal bib file with the two standard test references
    bib_content = (
        "@article{vaswani2017attention,\n"
        "  title={Attention Is All You Need},\n"
        "  author={Vaswani, Ashish},\n"
        "  year={2017},\n"
        "}\n"
        "\n"
        "@article{devlin2019bert,\n"
        "  title={BERT: Pre-training of Deep Bidirectional Transformers},\n"
        "  author={Devlin, Jacob},\n"
        "  year={2019},\n"
        "}\n"
    )
    (paper_dir / "bib" / "references.bib").write_text(bib_content, encoding="utf-8")

    return paper_dir


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """Temporary output/ directory with pre-populated asset_manifest.json."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "figures").mkdir()
    (output_dir / "tables").mkdir()

    import json

    manifest = {
        "assets": [
            {
                "asset_id": "ASSET-2026-001",
                "kind": "figure",
                "path": "output/figures/architecture.pdf",
                "content_hash": "sha256:abc123",
                "semantic_description": "Model architecture diagram",
            },
            {
                "asset_id": "ASSET-2026-002",
                "kind": "table",
                "path": "output/tables/results.tex",
                "content_hash": "sha256:def456",
                "semantic_description": "Experimental results comparison table",
            },
        ]
    }
    (output_dir / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_dir
