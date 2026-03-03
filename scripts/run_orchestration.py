"""Run multi-agent orchestration for MOF photocatalysis paper."""
import asyncio
import json
from pathlib import Path


def main():
    from vibewriting.literature.cache import LiteratureCache
    from vibewriting.writing.state_manager import PaperStateManager

    # Step 1: Load prerequisites
    cache = LiteratureCache(Path("data/processed/literature/literature_cards.jsonl"))
    cache.load()
    all_cards = [card.model_dump() for card in cache.all_cards()]
    print(f"Loaded {len(all_cards)} evidence cards")

    with open("output/asset_manifest.json", encoding="utf-8") as f:
        asset_manifest_raw = json.load(f)
    asset_manifest = asset_manifest_raw.get("assets", [])

    # Load BibTeX keys
    bib_path = Path("paper/bib/references.bib")
    bib_content = bib_path.read_text(encoding="utf-8")
    import re
    bib_keys = set(re.findall(r"@\w+\{(\w+),", bib_content))
    print(f"Loaded {len(bib_keys)} BibTeX keys")

    # Step 2: Load paper state
    manager = PaperStateManager(Path("output/paper_state.json"))
    state = manager.load()
    if state is None:
        raise FileNotFoundError("paper_state.json missing")
    print(f"Paper: {state.title}, phase: {state.phase}, sections: {len(state.sections)}")

    # Step 3: Run orchestrator with MockExecutor
    from vibewriting.agents.orchestrator import OrchestratorConfig, WritingOrchestrator
    from vibewriting.agents.executor import MockExecutor

    config = OrchestratorConfig(
        max_rounds=3,
        enable_git_snapshots=False,  # skip git snapshots in test mode
        executor_type="mock",
    )

    executor = MockExecutor()

    orchestrator = WritingOrchestrator(
        config=config,
        state_manager=manager,
        executor=executor,
        paper_dir=Path("paper"),
        output_dir=Path("output"),
    )

    # Run orchestration
    report = asyncio.run(
        orchestrator.run(
            state=state,
            evidence_cards=all_cards,
            asset_manifest=asset_manifest,
            glossary=None,
            symbols=None,
            bib_keys=bib_keys,
        )
    )

    # Step 4: Report results
    print(f"\nOrchestration Results:")
    print(f"  Rounds: {len(report.rounds)}")
    print(f"  Sections completed: {report.sections_completed}/{report.total_sections}")
    print(f"  Total conflicts: {report.total_conflicts}")
    print(f"  Unresolved: {report.unresolved_conflicts}")
    print(f"  Status: {'SUCCESS' if report.sections_completed == report.total_sections else 'PARTIAL'}")

    # Save report
    report_data = {
        "rounds": len(report.rounds),
        "sections_completed": report.sections_completed,
        "total_sections": report.total_sections,
        "total_conflicts": report.total_conflicts,
        "unresolved_conflicts": report.unresolved_conflicts,
    }
    Path("output/orchestration_report.json").write_text(
        json.dumps(report_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("Report saved to output/orchestration_report.json")


if __name__ == "__main__":
    main()
