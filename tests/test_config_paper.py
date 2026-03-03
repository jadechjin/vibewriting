"""Tests for src/vibewriting/config_paper.py.

Covers:
- Default field values
- topic required validation
- YAML loading (normal, empty, missing file)
- load_paper_config(None) returns default
- merge priority (overrides win)
- merge immutability (base not modified)
- Invalid value rejection (language, writing_mode)
- Serialization round-trip (save -> load)
- sections list customization
- data_dir optional None
- auto_approve default False
- merge_config empty overrides
- merge_config partial overrides
- save_paper_config creates parent directory
"""

from __future__ import annotations

import pytest

from pathlib import Path

from pydantic import ValidationError

from vibewriting.config_paper import (
    DEFAULT_SECTIONS,
    PaperConfig,
    load_paper_config,
    merge_config,
    save_paper_config,
)


# ---------------------------------------------------------------------------
# Default value tests
# ---------------------------------------------------------------------------


class TestPaperConfigDefaults:
    """Verify every field's default value matches the spec."""

    def test_language_default_is_zh(self):
        cfg = PaperConfig(topic="test")
        assert cfg.language == "zh"

    def test_document_class_default(self):
        cfg = PaperConfig(topic="test")
        assert cfg.document_class == "ctexart"

    def test_sections_default_is_chinese(self):
        cfg = PaperConfig(topic="test")
        assert cfg.sections == ["引言", "相关工作", "方法", "实验", "结论"]

    def test_sections_default_matches_constant(self):
        cfg = PaperConfig(topic="test")
        assert cfg.sections == DEFAULT_SECTIONS

    def test_literature_query_count_default(self):
        cfg = PaperConfig(topic="test")
        assert cfg.literature_query_count == 3

    def test_min_evidence_cards_default(self):
        cfg = PaperConfig(topic="test")
        assert cfg.min_evidence_cards == 5

    def test_data_dir_default_is_none(self):
        cfg = PaperConfig(topic="test")
        assert cfg.data_dir is None

    def test_random_seed_default(self):
        cfg = PaperConfig(topic="test")
        assert cfg.random_seed == 42

    def test_writing_mode_default(self):
        cfg = PaperConfig(topic="test")
        assert cfg.writing_mode == "multi"

    def test_enable_ai_disclosure_default_false(self):
        cfg = PaperConfig(topic="test")
        assert cfg.enable_ai_disclosure is False

    def test_enable_anonymize_default_false(self):
        cfg = PaperConfig(topic="test")
        assert cfg.enable_anonymize is False

    def test_natbib_style_default(self):
        cfg = PaperConfig(topic="test")
        assert cfg.natbib_style == "unsrtnat"

    def test_auto_approve_default_false(self):
        cfg = PaperConfig(topic="test")
        assert cfg.auto_approve is False

    def test_float_precision_default(self):
        cfg = PaperConfig(topic="test")
        assert cfg.float_precision == 6

    def test_dedup_threshold_default(self):
        cfg = PaperConfig(topic="test")
        assert cfg.dedup_threshold == 0.9

    def test_compile_max_retries_default(self):
        cfg = PaperConfig(topic="test")
        assert cfg.compile_max_retries == 5

    def test_compile_timeout_sec_default(self):
        cfg = PaperConfig(topic="test")
        assert cfg.compile_timeout_sec == 120


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------


class TestPaperConfigValidation:
    """Verify Pydantic validation rules."""

    def test_topic_is_required(self):
        with pytest.raises(ValidationError):
            PaperConfig()  # type: ignore[call-arg]

    def test_invalid_language_rejected(self):
        with pytest.raises(ValidationError):
            PaperConfig(topic="test", language="fr")  # type: ignore[arg-type]

    def test_invalid_writing_mode_rejected(self):
        with pytest.raises(ValidationError):
            PaperConfig(topic="test", writing_mode="batch")  # type: ignore[arg-type]

    def test_empty_sections_rejected(self):
        with pytest.raises(ValidationError):
            PaperConfig(topic="test", sections=[])

    def test_zero_literature_query_count_rejected(self):
        with pytest.raises(ValidationError):
            PaperConfig(topic="test", literature_query_count=0)

    def test_negative_literature_query_count_rejected(self):
        with pytest.raises(ValidationError):
            PaperConfig(topic="test", literature_query_count=-1)

    def test_zero_min_evidence_cards_rejected(self):
        with pytest.raises(ValidationError):
            PaperConfig(topic="test", min_evidence_cards=0)

    def test_valid_language_en(self):
        cfg = PaperConfig(topic="test", language="en")
        assert cfg.language == "en"

    def test_valid_writing_mode_single(self):
        cfg = PaperConfig(topic="test", writing_mode="single")
        assert cfg.writing_mode == "single"


# ---------------------------------------------------------------------------
# load_paper_config tests
# ---------------------------------------------------------------------------


class TestLoadPaperConfig:
    """Verify load_paper_config behavior."""

    def test_none_path_returns_default_config(self):
        cfg = load_paper_config(None)
        assert cfg.topic == "untitled"

    def test_none_path_has_correct_defaults(self):
        cfg = load_paper_config(None)
        assert cfg.language == "zh"
        assert cfg.sections == DEFAULT_SECTIONS

    def test_missing_file_returns_default_not_raises(self, tmp_path: Path):
        missing = tmp_path / "does_not_exist.yaml"
        cfg = load_paper_config(missing)
        assert cfg.topic == "untitled"

    def test_missing_file_does_not_raise(self, tmp_path: Path):
        missing = tmp_path / "nonexistent" / "config.yaml"
        # Should not raise FileNotFoundError
        cfg = load_paper_config(missing)
        assert isinstance(cfg, PaperConfig)

    def test_load_normal_yaml_file(self, tmp_path: Path):
        config_file = tmp_path / "paper_config.yaml"
        config_file.write_text(
            "topic: 深度学习综述\nlanguage: zh\n",
            encoding="utf-8",
        )
        cfg = load_paper_config(config_file)
        assert cfg.topic == "深度学习综述"
        assert cfg.language == "zh"

    def test_load_yaml_with_all_fields(self, tmp_path: Path):
        config_file = tmp_path / "paper_config.yaml"
        config_file.write_text(
            "topic: NLP\nlanguage: en\nwriting_mode: single\nauto_approve: true\n",
            encoding="utf-8",
        )
        cfg = load_paper_config(config_file)
        assert cfg.topic == "NLP"
        assert cfg.language == "en"
        assert cfg.writing_mode == "single"
        assert cfg.auto_approve is True

    def test_load_empty_yaml_returns_default(self, tmp_path: Path):
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("", encoding="utf-8")
        cfg = load_paper_config(config_file)
        assert cfg.topic == "untitled"

    def test_load_yaml_sections_customized(self, tmp_path: Path):
        config_file = tmp_path / "paper_config.yaml"
        config_file.write_text(
            "topic: test\nsections:\n  - 背景\n  - 核心方法\n  - 讨论\n",
            encoding="utf-8",
        )
        cfg = load_paper_config(config_file)
        assert cfg.sections == ["背景", "核心方法", "讨论"]

    def test_load_yaml_data_dir_none(self, tmp_path: Path):
        config_file = tmp_path / "paper_config.yaml"
        config_file.write_text(
            "topic: test\ndata_dir: null\n",
            encoding="utf-8",
        )
        cfg = load_paper_config(config_file)
        assert cfg.data_dir is None

    def test_load_yaml_data_dir_set(self, tmp_path: Path):
        config_file = tmp_path / "paper_config.yaml"
        config_file.write_text(
            "topic: test\ndata_dir: /data/raw\n",
            encoding="utf-8",
        )
        cfg = load_paper_config(config_file)
        assert cfg.data_dir == "/data/raw"


# ---------------------------------------------------------------------------
# merge_config tests
# ---------------------------------------------------------------------------


class TestMergeConfig:
    """Verify merge_config immutability and priority."""

    def test_overrides_win_over_base(self):
        base = PaperConfig(topic="original", language="zh")
        result = merge_config(base, {"language": "en"})
        assert result.language == "en"

    def test_base_not_modified_after_merge(self):
        base = PaperConfig(topic="original", language="zh")
        merge_config(base, {"language": "en"})
        assert base.language == "zh"

    def test_base_topic_not_modified(self):
        base = PaperConfig(topic="original")
        merge_config(base, {"topic": "overridden"})
        assert base.topic == "original"

    def test_returns_new_object(self):
        base = PaperConfig(topic="test")
        result = merge_config(base, {"topic": "new"})
        assert result is not base

    def test_empty_overrides_returns_equivalent_config(self):
        base = PaperConfig(topic="test", language="en", random_seed=99)
        result = merge_config(base, {})
        assert result.topic == "test"
        assert result.language == "en"
        assert result.random_seed == 99

    def test_partial_overrides_preserves_other_fields(self):
        base = PaperConfig(topic="test", language="zh", random_seed=99)
        result = merge_config(base, {"random_seed": 7})
        assert result.topic == "test"
        assert result.language == "zh"
        assert result.random_seed == 7

    def test_merge_sections_override(self):
        base = PaperConfig(topic="test")
        result = merge_config(base, {"sections": ["引言", "结论"]})
        assert result.sections == ["引言", "结论"]
        assert base.sections == DEFAULT_SECTIONS

    def test_merge_auto_approve_override(self):
        base = PaperConfig(topic="test", auto_approve=False)
        result = merge_config(base, {"auto_approve": True})
        assert result.auto_approve is True
        assert base.auto_approve is False


# ---------------------------------------------------------------------------
# save_paper_config tests
# ---------------------------------------------------------------------------


class TestSavePaperConfig:
    """Verify save_paper_config and round-trip serialization."""

    def test_save_creates_file(self, tmp_path: Path):
        cfg = PaperConfig(topic="test save")
        out_path = tmp_path / "output.yaml"
        save_paper_config(cfg, out_path)
        assert out_path.exists()

    def test_save_creates_parent_directories(self, tmp_path: Path):
        cfg = PaperConfig(topic="nested")
        nested_path = tmp_path / "a" / "b" / "c" / "config.yaml"
        save_paper_config(cfg, nested_path)
        assert nested_path.exists()

    def test_round_trip_topic(self, tmp_path: Path):
        cfg = PaperConfig(topic="往返测试")
        out_path = tmp_path / "rt.yaml"
        save_paper_config(cfg, out_path)
        loaded = load_paper_config(out_path)
        assert loaded.topic == "往返测试"

    def test_round_trip_all_fields(self, tmp_path: Path):
        cfg = PaperConfig(
            topic="完整往返",
            language="en",
            document_class="article",
            sections=["引言", "结论"],
            literature_query_count=5,
            min_evidence_cards=10,
            data_dir="/data",
            random_seed=123,
            writing_mode="single",
            enable_ai_disclosure=True,
            enable_anonymize=True,
            natbib_style="abbrvnat",
            auto_approve=True,
        )
        out_path = tmp_path / "full_rt.yaml"
        save_paper_config(cfg, out_path)
        loaded = load_paper_config(out_path)
        assert loaded.topic == "完整往返"
        assert loaded.language == "en"
        assert loaded.document_class == "article"
        assert loaded.sections == ["引言", "结论"]
        assert loaded.literature_query_count == 5
        assert loaded.min_evidence_cards == 10
        assert loaded.data_dir == "/data"
        assert loaded.random_seed == 123
        assert loaded.writing_mode == "single"
        assert loaded.enable_ai_disclosure is True
        assert loaded.enable_anonymize is True
        assert loaded.natbib_style == "abbrvnat"
        assert loaded.auto_approve is True

    def test_round_trip_data_dir_none(self, tmp_path: Path):
        cfg = PaperConfig(topic="null-dir", data_dir=None)
        out_path = tmp_path / "null_dir.yaml"
        save_paper_config(cfg, out_path)
        loaded = load_paper_config(out_path)
        assert loaded.data_dir is None

    def test_saved_file_is_utf8_readable(self, tmp_path: Path):
        cfg = PaperConfig(topic="中文主题测试")
        out_path = tmp_path / "utf8.yaml"
        save_paper_config(cfg, out_path)
        content = out_path.read_text(encoding="utf-8")
        assert "中文主题测试" in content


# ---------------------------------------------------------------------------
# apply_paper_config tests
# ---------------------------------------------------------------------------


class TestApplyPaperConfig:
    """Verify apply_paper_config bridges PaperConfig to Settings."""

    def test_apply_overrides_random_seed(self):
        from vibewriting.config import apply_paper_config

        pc = PaperConfig(topic="test", random_seed=99)
        result = apply_paper_config(pc)
        assert result.random_seed == 99

    def test_apply_overrides_float_precision(self):
        from vibewriting.config import apply_paper_config

        pc = PaperConfig(topic="test", float_precision=3)
        result = apply_paper_config(pc)
        assert result.float_precision == 3

    def test_apply_overrides_compile_max_retries(self):
        from vibewriting.config import apply_paper_config

        pc = PaperConfig(topic="test", compile_max_retries=10)
        result = apply_paper_config(pc)
        assert result.compile_max_retries == 10

    def test_apply_does_not_modify_original_settings(self):
        from vibewriting.config import apply_paper_config, settings

        original_seed = settings.random_seed
        pc = PaperConfig(topic="test", random_seed=999)
        apply_paper_config(pc)
        assert settings.random_seed == original_seed

    def test_apply_returns_settings_instance(self):
        from vibewriting.config import Settings, apply_paper_config

        pc = PaperConfig(topic="test")
        result = apply_paper_config(pc)
        assert isinstance(result, Settings)

    def test_apply_default_config_returns_settings(self):
        from vibewriting.config import apply_paper_config, settings

        pc = PaperConfig(topic="test")
        result = apply_paper_config(pc)
        assert result.random_seed == settings.random_seed
