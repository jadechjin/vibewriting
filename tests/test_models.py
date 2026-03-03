"""Tests for Pydantic data models.

Covers: round-trip serialization, bounds validation, extra='forbid',
and hypothesis-based property tests.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from vibewriting.models import (
    AssetBase,
    BaseEntity,
    Experiment,
    Figure,
    Paper,
    Section,
    Table,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _base_fields(**overrides):
    defaults = {
        "id": "test-001",
        "created_at": datetime(2026, 1, 1),
        "updated_at": datetime(2026, 1, 1),
        "tags": ["test"],
    }
    return {**defaults, **overrides}


def _asset_fields(**overrides):
    defaults = {
        **_base_fields(),
        "asset_id": "ASSET-2026-001",
        "kind": "figure",
        "path": "output/figures/fig1.pgf",
        "content_hash": "abc123",
        "semantic_description": "A test figure",
        "generator_version": "1.0.0",
    }
    return {**defaults, **overrides}


# ---------------------------------------------------------------------------
# T04: BaseEntity + AssetBase
# ---------------------------------------------------------------------------

class TestBaseEntity:
    def test_round_trip(self):
        entity = BaseEntity(**_base_fields())
        data = entity.model_dump()
        restored = BaseEntity(**data)
        assert entity == restored

    def test_defaults(self):
        entity = BaseEntity(id="x")
        assert isinstance(entity.created_at, datetime)
        assert entity.tags == []

    def test_extra_forbid(self):
        with pytest.raises(ValidationError, match="extra"):
            BaseEntity(id="x", unknown_field="bad")


class TestAssetBase:
    def test_round_trip(self):
        asset = AssetBase(**_asset_fields())
        data = asset.model_dump()
        restored = AssetBase(**data)
        assert asset == restored

    def test_asset_id_pattern_valid(self):
        AssetBase(**_asset_fields(asset_id="ASSET-2026-001"))
        AssetBase(**_asset_fields(asset_id="ASSET-9999-9999"))

    def test_asset_id_pattern_invalid(self):
        with pytest.raises(ValidationError, match="asset_id"):
            AssetBase(**_asset_fields(asset_id="bad-id"))

    def test_extra_forbid(self):
        with pytest.raises(ValidationError, match="extra"):
            AssetBase(**_asset_fields(extra_field="bad"))


# ---------------------------------------------------------------------------
# T05: Paper
# ---------------------------------------------------------------------------

class TestPaper:
    def _defaults(self, **overrides):
        base = {
            **_base_fields(),
            "title": "Test Paper",
            "authors": ["Author A"],
            "abstract": "Abstract text",
            "bib_key": "smith2026",
            "quality_score": 7.5,
        }
        return {**base, **overrides}

    def test_round_trip(self):
        paper = Paper(**self._defaults())
        data = paper.model_dump()
        restored = Paper(**data)
        assert paper == restored

    def test_bib_key_valid_patterns(self):
        for key in ["smith2026", "chen_2025:main", "A-B"]:
            Paper(**self._defaults(bib_key=key))

    def test_bib_key_invalid(self):
        with pytest.raises(ValidationError, match="bib_key"):
            Paper(**self._defaults(bib_key="has spaces"))

    def test_quality_score_bounds(self):
        Paper(**self._defaults(quality_score=0))
        Paper(**self._defaults(quality_score=10))
        with pytest.raises(ValidationError):
            Paper(**self._defaults(quality_score=-1))
        with pytest.raises(ValidationError):
            Paper(**self._defaults(quality_score=11))

    def test_extra_forbid(self):
        with pytest.raises(ValidationError, match="extra"):
            Paper(**self._defaults(bad="x"))


# ---------------------------------------------------------------------------
# T06: Experiment
# ---------------------------------------------------------------------------

class TestExperiment:
    def _defaults(self, **overrides):
        base = {
            **_base_fields(),
            "experiment_id": "exp-001",
            "config": {"lr": 0.01},
            "results": {"accuracy": 0.95},
            "data_fingerprint": "sha256:abc",
            "asset_ids": ["ASSET-2026-001"],
        }
        return {**base, **overrides}

    def test_round_trip(self):
        exp = Experiment(**self._defaults())
        data = exp.model_dump()
        restored = Experiment(**data)
        assert exp == restored

    def test_extra_forbid(self):
        with pytest.raises(ValidationError, match="extra"):
            Experiment(**self._defaults(bad="x"))


# ---------------------------------------------------------------------------
# T07: Figure
# ---------------------------------------------------------------------------

class TestFigure:
    def _defaults(self, **overrides):
        base = {
            **_asset_fields(kind="figure"),
            "chart_type": "line",
            "data_source": "data/raw/exp1.csv",
            "x_label": "Epoch",
            "y_label": "Loss",
        }
        return {**base, **overrides}

    def test_round_trip(self):
        fig = Figure(**self._defaults())
        data = fig.model_dump()
        restored = Figure(**data)
        assert fig == restored

    def test_kind_discriminator(self):
        fig = Figure(**self._defaults())
        assert fig.kind == "figure"

    def test_invalid_chart_type(self):
        with pytest.raises(ValidationError):
            Figure(**self._defaults(chart_type="pie"))

    def test_extra_forbid(self):
        with pytest.raises(ValidationError, match="extra"):
            Figure(**self._defaults(bad="x"))


# ---------------------------------------------------------------------------
# T08: Table
# ---------------------------------------------------------------------------

class TestTable:
    def _defaults(self, **overrides):
        base = {
            **_asset_fields(kind="table"),
            "columns": ["name", "value"],
            "row_count": 10,
            "template_name": "booktabs",
        }
        return {**base, **overrides}

    def test_round_trip(self):
        tbl = Table(**self._defaults())
        data = tbl.model_dump()
        restored = Table(**data)
        assert tbl == restored

    def test_kind_discriminator(self):
        tbl = Table(**self._defaults())
        assert tbl.kind == "table"

    def test_row_count_non_negative(self):
        Table(**self._defaults(row_count=0))
        with pytest.raises(ValidationError):
            Table(**self._defaults(row_count=-1))

    def test_extra_forbid(self):
        with pytest.raises(ValidationError, match="extra"):
            Table(**self._defaults(bad="x"))


# ---------------------------------------------------------------------------
# T09: Section
# ---------------------------------------------------------------------------

class TestSection:
    def _defaults(self, **overrides):
        base = {
            **_base_fields(),
            "section_id": "sec-intro",
            "title": "Introduction",
            "outline": ["Background", "Motivation"],
            "status": "draft",
            "claim_ids": ["EC-2026-001"],
            "asset_ids": ["ASSET-2026-001"],
            "citation_keys": ["smith2026"],
        }
        return {**base, **overrides}

    def test_round_trip(self):
        sec = Section(**self._defaults())
        data = sec.model_dump()
        restored = Section(**data)
        assert sec == restored

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            Section(**self._defaults(status="invalid"))

    def test_valid_statuses(self):
        for status in ("draft", "review", "complete"):
            Section(**self._defaults(status=status))

    def test_extra_forbid(self):
        with pytest.raises(ValidationError, match="extra"):
            Section(**self._defaults(bad="x"))


# ---------------------------------------------------------------------------
# Hypothesis PBT: round-trip for all models
# ---------------------------------------------------------------------------

try:
    from hypothesis import given, settings as hsettings
    from hypothesis import strategies as st

    _HAS_HYPOTHESIS = True
except ImportError:
    _HAS_HYPOTHESIS = False

if _HAS_HYPOTHESIS:
    _datetime_st = st.datetimes(
        min_value=datetime(2000, 1, 1),
        max_value=datetime(2099, 12, 31),
    )
    _ascii_text = st.text(
        alphabet=st.characters(whitelist_categories=("L", "N", "P")),
        min_size=1,
        max_size=50,
    )
    _bib_key_st = st.from_regex(r"^[a-zA-Z0-9_:\-]{1,30}$", fullmatch=True)

    @given(
        title=_ascii_text,
        bib_key=_bib_key_st,
        score=st.floats(min_value=0, max_value=10, allow_nan=False),
    )
    @hsettings(max_examples=50)
    def test_paper_pbt_round_trip(title, bib_key, score):
        paper = Paper(
            id="pbt",
            title=title,
            authors=["A"],
            abstract="abs",
            bib_key=bib_key,
            quality_score=score,
        )
        data = paper.model_dump()
        restored = Paper(**data)
        assert paper == restored

    @given(experiment_id=_ascii_text)
    @hsettings(max_examples=50)
    def test_experiment_pbt_round_trip(experiment_id):
        exp = Experiment(id="pbt", experiment_id=experiment_id)
        data = exp.model_dump()
        restored = Experiment(**data)
        assert exp == restored

    @given(section_id=_ascii_text, status=st.sampled_from(["draft", "review", "complete"]))
    @hsettings(max_examples=50)
    def test_section_pbt_round_trip(section_id, status):
        sec = Section(
            id="pbt",
            section_id=section_id,
            title="Test",
            status=status,
        )
        data = sec.model_dump()
        restored = Section(**data)
        assert sec == restored
