"""Phase 6 CLI: compile-heal -> citation-audit -> contract-audit -> peer-review."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import typer

from vibewriting.config import settings
from vibewriting.review.models import Phase6Report

app = typer.Typer(help="Phase 6: Compilation & Quality Assurance")
logger = logging.getLogger(__name__)


@app.command()
def run(
    paper_dir: Path = typer.Option(None, help="Paper source directory"),
    output_dir: Path = typer.Option(None, help="Output directory"),
    data_dir: Path = typer.Option(None, help="Data directory"),
    max_retries: int = typer.Option(None, help="Max compile retries"),
    skip_external_api: bool = typer.Option(False, help="Skip CrossRef API"),
) -> None:
    """Run full Phase 6 pipeline."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    paper_dir = paper_dir or settings.paper_dir
    output_dir = output_dir or settings.output_dir
    data_dir = data_dir or settings.data_dir
    max_retries = max_retries or settings.compile_max_retries

    typer.echo(f"=== Phase 6: Compilation & Quality ===")
    typer.echo(f"Paper: {paper_dir}")
    typer.echo(f"Output: {output_dir}")
    typer.echo()

    # Step 1: Compile + self-heal
    typer.echo("[1/4] Compile & self-heal...")
    from vibewriting.latex.compiler import run_self_heal_loop, write_patch_reports
    reports = run_self_heal_loop(paper_dir, max_retries)
    write_patch_reports(reports, output_dir)

    has_critical = any(not r.success for r in reports) and not any(r.success for r in reports)
    if has_critical:
        typer.echo("  CRITICAL: Compilation failed after all retries")
        typer.echo("  See patch_report.json for details")

    # Step 2: Citation audit
    typer.echo("[2/4] Citation audit...")
    citation_result = None
    try:
        from vibewriting.review.citation_audit import run_citation_audit
        cards_path = data_dir / "processed" / "literature" / "literature_cards.jsonl"
        bib_path = paper_dir / "bib" / "references.bib"
        aux_path = paper_dir / "build" / "main.aux"
        citation_result = run_citation_audit(
            paper_dir, cards_path, bib_path,
            aux_path=aux_path if aux_path.exists() else None,
            crossref_email=settings.crossref_api_email,
            skip_external_api=skip_external_api,
        )
        typer.echo(f"  Verified: {citation_result.verified_count}")
        typer.echo(f"  Suspicious: {len(citation_result.suspicious_keys)}")
        typer.echo(f"  Orphan claims: {len(citation_result.orphan_claims)}")
    except Exception as e:
        typer.echo(f"  WARNING: Citation audit failed: {e}")

    # Step 3: Contract integrity
    typer.echo("[3/4] Contract integrity...")
    integrity_violations = None
    try:
        from vibewriting.contracts.full_integrity import validate_end_to_end
        bib_path = paper_dir / "bib" / "references.bib"
        violations = validate_end_to_end(
            paper_dir, output_dir, data_dir,
            bib_path=bib_path if bib_path.exists() else None,
        )
        integrity_violations = [
            {"source": v.source, "field": v.field,
             "missing_key": v.missing_key, "target": v.target}
            for v in violations
        ]
        typer.echo(f"  Violations: {len(violations)}")
    except Exception as e:
        typer.echo(f"  WARNING: Contract integrity check failed: {e}")

    # Step 4: Peer review
    typer.echo("[4/4] Peer review...")
    peer_review = None
    try:
        from vibewriting.review.peer_review import generate_review_report, save_review_reports
        cards_path = data_dir / "processed" / "literature" / "literature_cards.jsonl"
        paper_state_path = output_dir / "paper_state.json"
        paper_state = {}
        if paper_state_path.exists():
            paper_state = json.loads(paper_state_path.read_text(encoding="utf-8"))
        peer_review = generate_review_report(paper_state, paper_dir, cards_path)
        save_review_reports(peer_review, output_dir)
        typer.echo(f"  Score: {peer_review.overall_score}/10")
        typer.echo(f"  Verdict: {peer_review.verdict}")
    except Exception as e:
        typer.echo(f"  WARNING: Peer review failed: {e}")

    # Aggregate report
    phase6 = Phase6Report(
        compilation=reports,
        citation_audit=citation_result,
        contract_integrity=integrity_violations,
        peer_review=peer_review,
    )
    report_path = output_dir / "phase6_report.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        phase6.model_dump_json(indent=2),
        encoding="utf-8",
    )
    typer.echo()
    typer.echo(f"Phase 6 report saved to {report_path}")

    if has_critical:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
