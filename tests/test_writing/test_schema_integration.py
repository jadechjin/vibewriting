"""Tests for Phase 4 schema integration: PaperState, Glossary, SymbolTable."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import jsonschema
import pytest

from vibewriting.contracts.integrity import validate_referential_integrity
from vibewriting.contracts.schema_export import SCHEMAS_DIR, export_schemas
from vibewriting.contracts.validator import validate_contract
from vibewriting.models import Glossary, PaperState, SectionState, SymbolTable


# ---------------------------------------------------------------------------
# 1. Schema 导出成功
# ---------------------------------------------------------------------------


class TestSchemaExport:
    def test_export_schemas_returns_paths(self, tmp_path: Path):
        """export_schemas() 不报错，返回文件路径列表。"""
        paths = export_schemas(output_dir=tmp_path)
        assert isinstance(paths, list)
        assert len(paths) > 0
        for p in paths:
            assert isinstance(p, Path)
            assert p.exists()

    def test_export_includes_new_models(self, tmp_path: Path):
        """export_schemas() 输出包含三个新 schema 文件。"""
        paths = export_schemas(output_dir=tmp_path)
        names = {p.name for p in paths}
        assert "paperstate.schema.json" in names
        assert "glossary.schema.json" in names
        assert "symboltable.schema.json" in names


# ---------------------------------------------------------------------------
# 2. 新 Schema 文件存在
# ---------------------------------------------------------------------------


class TestSchemaFilesExist:
    def test_paperstate_schema_exists(self):
        """paperstate.schema.json 文件存在于 schemas 目录。"""
        path = SCHEMAS_DIR / "paperstate.schema.json"
        assert path.exists(), f"paperstate.schema.json not found at {path}"

    def test_glossary_schema_exists(self):
        """glossary.schema.json 文件存在于 schemas 目录。"""
        path = SCHEMAS_DIR / "glossary.schema.json"
        assert path.exists(), f"glossary.schema.json not found at {path}"

    def test_symboltable_schema_exists(self):
        """symboltable.schema.json 文件存在于 schemas 目录。"""
        path = SCHEMAS_DIR / "symboltable.schema.json"
        assert path.exists(), f"symboltable.schema.json not found at {path}"


# ---------------------------------------------------------------------------
# 3. Schema 内容有效 JSON
# ---------------------------------------------------------------------------


class TestSchemaJsonValidity:
    def test_paperstate_schema_valid_json(self):
        """paperstate.schema.json 可解析为有效 JSON。"""
        path = SCHEMAS_DIR / "paperstate.schema.json"
        content = path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert isinstance(parsed, dict)
        assert "properties" in parsed or "title" in parsed

    def test_glossary_schema_valid_json(self):
        """glossary.schema.json 可解析为有效 JSON。"""
        path = SCHEMAS_DIR / "glossary.schema.json"
        content = path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert isinstance(parsed, dict)

    def test_symboltable_schema_valid_json(self):
        """symboltable.schema.json 可解析为有效 JSON。"""
        path = SCHEMAS_DIR / "symboltable.schema.json"
        content = path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert isinstance(parsed, dict)


# ---------------------------------------------------------------------------
# 4. PaperState 通过 schema 验证
# ---------------------------------------------------------------------------


class TestPaperStateSchemaValidation:
    def test_paperstate_passes_jsonschema(self):
        """创建 PaperState 实例 -> model_dump() -> jsonschema.validate 通过。"""
        paper_state = PaperState(
            paper_id="PAPER-2026-001",
            title="Test Paper",
            topic="machine learning",
        )
        schema_path = SCHEMAS_DIR / "paperstate.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        data = json.loads(paper_state.model_dump_json())
        jsonschema.validate(instance=data, schema=schema)

    def test_paperstate_with_sections_passes_jsonschema(self):
        """含 sections 的 PaperState 通过 jsonschema 验证。"""
        section = SectionState(
            section_id="SEC-001",
            title="Introduction",
            tex_file="sections/introduction.tex",
            claim_ids=["EC-2026-001"],
            asset_ids=["ASSET-2026-001"],
        )
        paper_state = PaperState(
            paper_id="PAPER-2026-001",
            title="Test Paper",
            topic="deep learning",
            sections=[section],
        )
        schema_path = SCHEMAS_DIR / "paperstate.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        data = json.loads(paper_state.model_dump_json())
        jsonschema.validate(instance=data, schema=schema)


# ---------------------------------------------------------------------------
# 5. Glossary 通过 schema 验证
# ---------------------------------------------------------------------------


class TestGlossarySchemaValidation:
    def test_glossary_empty_passes_jsonschema(self):
        """空 Glossary 通过 jsonschema 验证。"""
        glossary = Glossary()
        schema_path = SCHEMAS_DIR / "glossary.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        data = json.loads(glossary.model_dump_json())
        jsonschema.validate(instance=data, schema=schema)

    def test_glossary_with_entries_passes_jsonschema(self):
        """含词条的 Glossary 通过 jsonschema 验证。"""
        glossary = Glossary().add_term(
            "neural network",
            "A computational model inspired by biological neural networks.",
            section_id="SEC-001",
        )
        schema_path = SCHEMAS_DIR / "glossary.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        data = json.loads(glossary.model_dump_json())
        jsonschema.validate(instance=data, schema=schema)


# ---------------------------------------------------------------------------
# 6. SymbolTable 通过 schema 验证
# ---------------------------------------------------------------------------


class TestSymbolTableSchemaValidation:
    def test_symboltable_empty_passes_jsonschema(self):
        """空 SymbolTable 通过 jsonschema 验证。"""
        table = SymbolTable()
        schema_path = SCHEMAS_DIR / "symboltable.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        data = json.loads(table.model_dump_json())
        jsonschema.validate(instance=data, schema=schema)

    def test_symboltable_with_entries_passes_jsonschema(self):
        """含符号的 SymbolTable 通过 jsonschema 验证。"""
        table = SymbolTable().add_symbol(
            r"\alpha",
            "learning rate",
            section_id="SEC-002",
        )
        schema_path = SCHEMAS_DIR / "symboltable.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        data = json.loads(table.model_dump_json())
        jsonschema.validate(instance=data, schema=schema)


# ---------------------------------------------------------------------------
# 7. validate_contract 集成
# ---------------------------------------------------------------------------


class TestValidateContractIntegration:
    def test_validate_contract_paperstate(self):
        """使用 validate_contract(payload, 'paperstate') 成功验证。"""
        paper_state = PaperState(
            paper_id="PAPER-2026-002",
            title="Contract Test Paper",
            topic="natural language processing",
        )
        payload = json.loads(paper_state.model_dump_json())
        result = validate_contract(payload, "paperstate")
        assert result.data["paper_id"] == "PAPER-2026-002"
        assert result.heal_rounds == 0

    def test_validate_contract_glossary(self):
        """使用 validate_contract(payload, 'glossary') 成功验证。"""
        glossary = Glossary().add_term("transformer", "A self-attention based model.")
        payload = json.loads(glossary.model_dump_json())
        result = validate_contract(payload, "glossary")
        assert "entries" in result.data

    def test_validate_contract_symboltable(self):
        """使用 validate_contract(payload, 'symboltable') 成功验证。"""
        table = SymbolTable().add_symbol(r"\theta", "model parameters")
        payload = json.loads(table.model_dump_json())
        result = validate_contract(payload, "symboltable")
        assert "entries" in result.data


# ---------------------------------------------------------------------------
# 8. 引用完整性集成 - 无违规
# ---------------------------------------------------------------------------


class TestReferentialIntegrityValid:
    def test_no_violations_when_refs_consistent(self):
        """paper_state + evidence_cards + asset_manifest 一致时，无违规。"""
        paper_state = PaperState(
            paper_id="PAPER-2026-003",
            title="Integrity Test Paper",
            topic="computer vision",
            sections=[
                SectionState(
                    section_id="SEC-001",
                    title="Introduction",
                    tex_file="sections/introduction.tex",
                    claim_ids=["EC-2026-001"],
                    asset_ids=["ASSET-2026-001"],
                )
            ],
        )
        evidence_cards = [{"claim_id": "EC-2026-001", "content": "test claim"}]
        asset_manifest = [{"asset_id": "ASSET-2026-001", "type": "figure"}]

        violations = validate_referential_integrity(
            paper_state=json.loads(paper_state.model_dump_json()),
            evidence_cards=evidence_cards,
            asset_manifest=asset_manifest,
        )
        assert violations == []

    def test_no_violations_empty_sections(self):
        """无 sections 的 paper_state 不产生违规。"""
        paper_state = PaperState(
            paper_id="PAPER-2026-004",
            title="Empty Sections Paper",
            topic="robotics",
        )
        violations = validate_referential_integrity(
            paper_state=json.loads(paper_state.model_dump_json()),
            evidence_cards=[],
            asset_manifest=[],
        )
        assert violations == []


# ---------------------------------------------------------------------------
# 9. 引用完整性检测违规
# ---------------------------------------------------------------------------


class TestReferentialIntegrityViolations:
    def test_detects_missing_claim_id(self):
        """claim_id 在 evidence_cards 中不存在时，检测到违规。"""
        paper_state = PaperState(
            paper_id="PAPER-2026-005",
            title="Violation Test Paper",
            topic="nlp",
            sections=[
                SectionState(
                    section_id="SEC-001",
                    title="Background",
                    tex_file="sections/background.tex",
                    claim_ids=["EC-2026-999"],  # 不存在
                )
            ],
        )
        violations = validate_referential_integrity(
            paper_state=json.loads(paper_state.model_dump_json()),
            evidence_cards=[],
            asset_manifest=[],
        )
        assert len(violations) == 1
        assert violations[0].missing_key == "EC-2026-999"
        assert violations[0].field == "claim_id"

    def test_detects_missing_asset_id(self):
        """asset_id 在 asset_manifest 中不存在时，检测到违规。"""
        paper_state = PaperState(
            paper_id="PAPER-2026-006",
            title="Asset Violation Paper",
            topic="cv",
            sections=[
                SectionState(
                    section_id="SEC-002",
                    title="Experiments",
                    tex_file="sections/experiments.tex",
                    asset_ids=["ASSET-9999-999"],  # 不存在
                )
            ],
        )
        violations = validate_referential_integrity(
            paper_state=json.loads(paper_state.model_dump_json()),
            evidence_cards=[],
            asset_manifest=[],
        )
        assert len(violations) == 1
        assert violations[0].missing_key == "ASSET-9999-999"
        assert violations[0].field == "asset_id"

    def test_detects_multiple_violations(self):
        """同时存在多个违规时，全部被检测到。"""
        paper_state = PaperState(
            paper_id="PAPER-2026-007",
            title="Multi Violation Paper",
            topic="ml",
            sections=[
                SectionState(
                    section_id="SEC-001",
                    title="Methods",
                    tex_file="sections/methods.tex",
                    claim_ids=["EC-2026-901", "EC-2026-902"],
                    asset_ids=["ASSET-2026-901"],
                )
            ],
        )
        violations = validate_referential_integrity(
            paper_state=json.loads(paper_state.model_dump_json()),
            evidence_cards=[],
            asset_manifest=[],
        )
        assert len(violations) == 3


# ---------------------------------------------------------------------------
# 10. 模型从 __init__.py 导入正确
# ---------------------------------------------------------------------------


class TestModuleImports:
    def test_import_paperstate(self):
        """PaperState 可从 vibewriting.models 正确导入。"""
        from vibewriting.models import PaperState as PS

        instance = PS(paper_id="PAPER-2026-999", title="Import Test", topic="test")
        assert instance.paper_id == "PAPER-2026-999"

    def test_import_glossary(self):
        """Glossary 可从 vibewriting.models 正确导入。"""
        from vibewriting.models import Glossary as G

        instance = G()
        assert isinstance(instance, G)

    def test_import_symboltable(self):
        """SymbolTable 可从 vibewriting.models 正确导入。"""
        from vibewriting.models import SymbolTable as ST

        instance = ST()
        assert isinstance(instance, ST)

    def test_import_section_state(self):
        """SectionState 可从 vibewriting.models 正确导入。"""
        from vibewriting.models import SectionState as SS

        instance = SS(
            section_id="SEC-001",
            title="Test",
            tex_file="sections/test.tex",
        )
        assert instance.section_id == "SEC-001"

    def test_all_exports_present(self):
        """models.__all__ 包含所有新增模型名称。"""
        import vibewriting.models as m

        all_names = set(m.__all__)
        assert "PaperState" in all_names
        assert "SectionState" in all_names
        assert "PaperMetrics" in all_names
        assert "Glossary" in all_names
        assert "GlossaryEntry" in all_names
        assert "SymbolTable" in all_names
        assert "SymbolEntry" in all_names
