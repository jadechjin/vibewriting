"""Regenerate evidence cards in correct EvidenceCard format."""
import json
from pathlib import Path
from datetime import datetime, timezone


def make_card(claim_id, claim_text, bib_key, evidence_type, tags, paraphrase=True, quality=6):
    """Create a properly formatted evidence card dict."""
    return {
        "claim_id": claim_id,
        "claim_text": claim_text,
        "supporting_quote": "",
        "paraphrase": paraphrase,
        "bib_key": bib_key,
        "location": {},
        "evidence_type": evidence_type,
        "key_statistics": None,
        "methodology_notes": "",
        "quality_score": quality,
        "tags": tags,
        "retrieval_source": "manual",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source_id": "",
        "content_hash": None,
    }


cards = [
    make_card(
        "EC-2026-001",
        "MOF光催化产氢的首次报道出现在2010年，而MOF实现全分解水(OWS)的首次报道是2017年在MIL-53(Al)-NH2中掺入Ni2+作为助催化剂。",
        "chen2023mof_owsp_review", "survey",
        ["MOF", "overall_water_splitting", "history", "milestone"], quality=8,
    ),
    make_card(
        "EC-2026-002",
        "大多数MOF光催化研究集中于使用牺牲电子供体的H2生成，而非更困难的水氧化过程，实现无牺牲剂的全分解水仍是核心挑战。",
        "chen2023mof_owsp_review", "survey",
        ["MOF", "sacrificial_agent", "challenge", "water_oxidation"], quality=8,
    ),
    make_card(
        "EC-2026-003",
        "CFA-Zn MOF利用结晶学独立配体作为电子供体-受体对，引入Pt和Co3O4助催化剂后在可见光下产生H2和O2，稳定性超100小时，365nm处表观量子效率达3.09%。",
        "cfazn2025ows", "empirical",
        ["CFA-Zn", "overall_water_splitting", "visible_light", "quantum_efficiency"], quality=8,
    ),
    make_card(
        "EC-2026-004",
        "UiO-66(Zr)-NH2@MIL-88B(Fe)异质外延MOF-on-MOF结构通过Z-scheme机制实现太阳能驱动全分解水，3小时内H2和O2产量分别达690和279 umol/g。",
        "uio66_mil88b_2024", "empirical",
        ["MOF-on-MOF", "heteroepitaxial", "Z-scheme", "UiO-66", "MIL-88B"], quality=7,
    ),
    make_card(
        "EC-2026-005",
        "光电催化(PEC)产氢技术结合光催化和电催化优势，但MOF基PEC系统面临效率低和成本效益差的双重挑战。",
        "wang2025mof_pec_review", "survey",
        ["photoelectrocatalysis", "PEC", "MOF", "challenge"], quality=7,
    ),
    make_card(
        "EC-2026-006",
        "原始MOF材料存在严重的电荷复合和稳定性差的问题。通过构建Schottky、Type-II、Z-scheme和S-scheme异质结可有效改善光生载流子分离。",
        "zhang2025optimization_strategies", "survey",
        ["heterojunction", "charge_separation", "Schottky", "Z-scheme", "S-scheme"], quality=8,
    ),
    make_card(
        "EC-2026-007",
        "MOF衍生的RuO2/N,S-TiO2(RTTA)异质结在自来水中产氢速率达8190 umol/h/g，表观量子产率达10.0%。",
        "rtta2024heterojunction", "empirical",
        ["MOF-derived", "heterojunction", "HKUST-1", "MIL-125", "quantum_yield"], quality=8,
    ),
    make_card(
        "EC-2026-008",
        "MOF基复合材料通过配体功能化、金属掺杂、异质结构建和等离子耦合等策略增强光吸收和电荷分离。",
        "li2024mof_composites_h2", "survey",
        ["composite", "ligand_functionalization", "metal_doping", "plasmonic"], quality=7,
    ),
    make_card(
        "EC-2026-009",
        "Ce基MOF(Ce-BDC-DABCO)用于含盐水光催化产氢，最大产氢速率达420.8 mmol/h/g，约为未修饰Ce-BDC的4倍。",
        "coce_mof_2025", "empirical",
        ["Ce-MOF", "saline_water", "hydrogen_evolution"], quality=6,
    ),
    make_card(
        "EC-2026-010",
        "p型Ni-TBAPy MOF剥离的2D纳米带水还原活性提高164倍，最优H2产率98 umol/h，420nm处AQE达8.0%。",
        "ni_tbpy_2020", "empirical",
        ["Ni-MOF", "2D_nanobelts", "cocatalyst-free", "exfoliation"], quality=7,
    ),
    make_card(
        "EC-2026-011",
        "通过上转换材料拓展光响应范围、降低带隙、利用等离子共振和光热效应，可实现MOF材料全光谱响应光催化产氢。",
        "mof_fullspectrum_2025", "survey",
        ["full_spectrum", "upconversion", "bandgap_engineering", "plasmonic"], quality=7,
    ),
    make_card(
        "EC-2026-012",
        "合理设计的MOF基光催化剂可实现产氢耦合选择性氧化反应，包括苄醇氧化、苄胺偶联和5-HMF氧化等。",
        "lin2025coupled_oxidation", "survey",
        ["coupled_reaction", "selective_oxidation", "sacrificial_agent_free"], quality=7,
    ),
    make_card(
        "EC-2026-013",
        "MOF光催化产氢面临的主要挑战包括：光吸收范围窄、电荷复合严重、水稳定性差、量子效率低和规模化成本高。",
        "hassan2024emerging_trends", "survey",
        ["challenge", "light_absorption", "stability", "scalability"], quality=8,
    ),
    make_card(
        "EC-2026-014",
        "MOF与Ti3C2 MXene的复合材料中，MXene作为电子受体可有效促进光生电荷分离，同时提供额外催化活性位点。",
        "mxene_mof_2024", "survey",
        ["MXene", "Ti3C2", "composite", "electron_acceptor"], quality=6,
    ),
    make_card(
        "EC-2026-015",
        "基于MOFs的异质结构光催化剂通过内建电场定向传输光生电子；三元复合体系可同时延展光响应、促进电荷分离和防止光腐蚀。",
        "chen2024heterostructures_h2", "survey",
        ["heterostructure", "internal_electric_field", "ternary_composite"], quality=7,
    ),
    make_card(
        "EC-2026-016",
        "MOF基材料实现光催化全分解水的策略包括Z-scheme双半导体体系、助催化剂负载、配体工程和缺陷工程，但真正无牺牲剂的全分解水报道仍然稀少。",
        "mof_on_mof_owsp", "survey",
        ["overall_water_splitting", "Z-scheme", "cocatalyst", "ligand_engineering"], quality=7,
    ),
    make_card(
        "EC-2026-017",
        "MOF及其衍生纳米材料提供长期稳定性、高效电荷分离传输和宽光吸收等优势。异质外延MOF-on-MOF复合光催化剂是前沿方向。",
        "singh2025mini_review", "survey",
        ["MOF_derivatives", "stability", "charge_transport"], quality=6,
    ),
    make_card(
        "EC-2026-018",
        "MOF材料绿色合成、结构解析和先进表征技术是推动光催化应用的基础。大规模低成本合成是未来发展方向。",
        "jiang2026mof_review", "survey",
        ["green_synthesis", "characterization", "scale-up"], quality=6,
    ),
]


def main():
    cards_path = Path("data/processed/literature/literature_cards.jsonl")
    cards_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cards_path, "w", encoding="utf-8") as f:
        for card in cards:
            f.write(json.dumps(card, ensure_ascii=False) + "\n")
    print(f"Written {len(cards)} evidence cards")

    # Verify loading
    from vibewriting.literature.cache import LiteratureCache
    cache = LiteratureCache(cards_path)
    loaded = cache.load()
    print(f"Verified: loaded {loaded} cards from cache")


if __name__ == "__main__":
    main()
