"""Shared fixtures for literature tests."""

from __future__ import annotations

import pytest

from vibewriting.literature.models import RawLiteratureRecord
from vibewriting.models.evidence_card import EvidenceCard


@pytest.fixture
def sample_raw_record() -> RawLiteratureRecord:
    return RawLiteratureRecord(
        title="Attention Is All You Need",
        authors=["Vaswani", "Shazeer", "Parmar"],
        year=2017,
        doi="10.48550/arXiv.1706.03762",
        abstract="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.",
        source="paper-search",
    )


@pytest.fixture
def sample_raw_records() -> list[RawLiteratureRecord]:
    return [
        RawLiteratureRecord(
            title="Attention Is All You Need",
            authors=["Vaswani", "Shazeer", "Parmar"],
            year=2017,
            doi="10.48550/arXiv.1706.03762",
            source="paper-search",
        ),
        RawLiteratureRecord(
            title="BERT: Pre-training of Deep Bidirectional Transformers",
            authors=["Devlin", "Chang", "Lee", "Toutanova"],
            year=2019,
            doi="10.18653/v1/N19-1423",
            source="paper-search",
        ),
        RawLiteratureRecord(
            title="GPT-4 Technical Report",
            authors=["OpenAI"],
            year=2023,
            arxiv_id="2303.08774",
            source="paper-search",
        ),
    ]


@pytest.fixture
def sample_evidence_card() -> EvidenceCard:
    return EvidenceCard(
        claim_id="EC-2026-001",
        claim_text="Transformer architecture eliminates recurrence entirely.",
        supporting_quote="relying entirely on an attention mechanism",
        paraphrase=False,
        bib_key="vaswani2017attention",
        evidence_type="empirical",
        quality_score=8,
        tags=["transformer", "attention"],
        retrieval_source="paper-search",
        source_id="doi:10.48550/arXiv.1706.03762",
    )


@pytest.fixture
def sample_evidence_cards() -> list[EvidenceCard]:
    return [
        EvidenceCard(
            claim_id="EC-2026-001",
            claim_text="Transformer architecture eliminates recurrence entirely.",
            supporting_quote="relying entirely on an attention mechanism",
            bib_key="vaswani2017attention",
            evidence_type="empirical",
            quality_score=8,
            tags=["transformer"],
            retrieval_source="paper-search",
            source_id="doi:10.48550/arXiv.1706.03762",
        ),
        EvidenceCard(
            claim_id="EC-2026-002",
            claim_text="BERT achieves state-of-the-art on eleven NLP tasks.",
            supporting_quote="new state of the art on eleven NLP tasks",
            bib_key="devlin2019bert",
            evidence_type="empirical",
            quality_score=9,
            tags=["bert", "nlp"],
            retrieval_source="paper-search",
            source_id="doi:10.18653/v1/N19-1423",
        ),
    ]


# Mock MCP responses

@pytest.fixture
def mock_paper_search_results() -> dict:
    return {
        "results": [
            {
                "title": "Attention Is All You Need",
                "authors": ["Vaswani, A.", "Shazeer, N."],
                "year": 2017,
                "doi": "10.48550/arXiv.1706.03762",
                "abstract": "The dominant sequence transduction models...",
            },
            {
                "title": "BERT: Pre-training of Deep Bidirectional Transformers",
                "authors": ["Devlin, J.", "Chang, M."],
                "year": 2019,
                "doi": "10.18653/v1/N19-1423",
                "abstract": "We introduce a new language representation model...",
            },
        ],
        "bibtex": (
            "@article{vaswani2017attention,\n"
            "  title={Attention Is All You Need},\n"
            "  author={Vaswani, Ashish and Shazeer, Noam},\n"
            "  year={2017},\n"
            "}\n"
            "@article{devlin2019bert,\n"
            "  title={BERT: Pre-training of Deep Bidirectional Transformers},\n"
            "  author={Devlin, Jacob and Chang, Ming-Wei},\n"
            "  year={2019},\n"
            "}\n"
        ),
    }


@pytest.fixture
def mock_dify_results() -> list[dict]:
    return [
        {
            "content": "Transformers use self-attention mechanism...",
            "metadata": {"source": "knowledge-base", "score": 0.92},
        },
    ]
