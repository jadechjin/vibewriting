"""Build and save run metrics report (Step 8)."""
import json
from pathlib import Path
from datetime import datetime, timezone


def main():
    output_dir = Path("output")

    # Load checkpoint
    cp = json.loads((output_dir / "checkpoint.json").read_text(encoding="utf-8"))

    # Load phase6 report
    phase6 = json.loads((output_dir / "phase6_report.json").read_text(encoding="utf-8"))

    # Load orchestration report
    orch_path = output_dir / "orchestration_report.json"
    orch = json.loads(orch_path.read_text(encoding="utf-8")) if orch_path.exists() else {}

    # Count evidence cards
    cards_path = Path("data/processed/literature/literature_cards.jsonl")
    card_count = 0
    if cards_path.exists():
        card_count = sum(1 for line in cards_path.read_text(encoding="utf-8").splitlines() if line.strip())

    # Build metrics report
    report = {
        "run_id": cp.get("run_id", "unknown"),
        "topic": cp.get("topic", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "literature": {
            "evidence_cards": card_count,
            "bib_entries": phase6.get("citation_audit", {}).get("bib_entries", 0),
            "dedup_rate": 0.0,
        },
        "writing": {
            "total_sections": phase6.get("summary", {}).get("total_sections", 0),
            "total_words": phase6.get("summary", {}).get("total_words", 0),
            "total_citations": phase6.get("summary", {}).get("total_citations", 0),
            "claim_annotations": phase6.get("summary", {}).get("total_claim_annotations", 0),
            "citation_coverage": phase6.get("summary", {}).get("citation_coverage", 0),
        },
        "orchestration": {
            "rounds": orch.get("rounds", 0),
            "sections_completed": orch.get("sections_completed", 0),
            "total_conflicts": orch.get("total_conflicts", 0),
            "unresolved_conflicts": orch.get("unresolved_conflicts", 0),
        },
        "compilation": {
            "success": phase6.get("compilation", {}).get("success", False),
            "first_pass_success": phase6.get("compilation", {}).get("first_pass_success", False),
            "heal_rounds": phase6.get("compilation", {}).get("heal_rounds", 0),
            "pdf_size_bytes": phase6.get("compilation", {}).get("pdf_size_bytes", 0),
            "peer_review_score": phase6.get("peer_review", {}).get("score", 0),
            "peer_review_verdict": phase6.get("peer_review", {}).get("verdict", ""),
            "contract_violations": phase6.get("contract_violations", 0),
            "undefined_references": phase6.get("citation_audit", {}).get("undefined_references", 0),
            "unused_references": phase6.get("citation_audit", {}).get("unused_references", 0),
        },
        "phases": {k: v.get("status", "") for k, v in cp.get("phases", {}).items()},
    }

    # Atomic write
    metrics_path = output_dir / "run_metrics.json"
    tmp_path = output_dir / "run_metrics.json.tmp"
    tmp_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_path.rename(metrics_path)
    print(f"Run metrics saved to {metrics_path}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"Run Metrics Summary (run_id: {report['run_id']})")
    print(f"{'='*60}")
    print(f"Topic: {report['topic']}")
    print(f"\nLiterature:")
    print(f"  Evidence cards: {report['literature']['evidence_cards']}")
    print(f"  BibTeX entries: {report['literature']['bib_entries']}")
    print(f"\nWriting:")
    print(f"  Sections: {report['writing']['total_sections']}")
    print(f"  Words: {report['writing']['total_words']}")
    print(f"  Citations: {report['writing']['total_citations']}")
    print(f"  CLAIM_IDs: {report['writing']['claim_annotations']}")
    print(f"\nOrchestration:")
    print(f"  Rounds: {report['orchestration']['rounds']}")
    print(f"  Completed: {report['orchestration']['sections_completed']}")
    print(f"  Conflicts: {report['orchestration']['total_conflicts']}")
    print(f"\nCompilation:")
    print(f"  Success: {report['compilation']['success']}")
    print(f"  PDF: {report['compilation']['pdf_size_bytes'] // 1024} KB")
    print(f"  Peer review: {report['compilation']['peer_review_score']}/10 ({report['compilation']['peer_review_verdict']})")
    print(f"  Violations: {report['compilation']['contract_violations']}")
    print(f"  Undefined refs: {report['compilation']['undefined_references']}")
    print(f"  Unused refs: {report['compilation']['unused_references']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
