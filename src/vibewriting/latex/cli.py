"""Phase 6 CLI: compile-heal -> citation-audit -> contract-audit -> peer-review."""

from __future__ import annotations

import json
import logging
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
    export_docx: bool = typer.Option(False, help="Export DOCX via format-neutral IR"),
    reference_docx: Path = typer.Option(None, help="Path to pandoc reference.docx"),
    csl_path: Path = typer.Option(None, help="Path to CSL file for bibliography style"),
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
    total_steps = 5 if export_docx else 4

    # Step 1: Compile + self-heal
    typer.echo(f"[1/{total_steps}] Compile & self-heal...")
    from vibewriting.latex.compiler import run_self_heal_loop, write_patch_reports
    reports = run_self_heal_loop(paper_dir, max_retries)
    write_patch_reports(reports, output_dir)

    has_critical = any(not r.success for r in reports) and not any(r.success for r in reports)
    if has_critical:
        typer.echo("  CRITICAL: Compilation failed after all retries")
        typer.echo("  See patch_report.json for details")

    # Step 2: Citation audit
    typer.echo(f"[2/{total_steps}] Citation audit...")
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
    typer.echo(f"[3/{total_steps}] Contract integrity...")
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
    typer.echo(f"[4/{total_steps}] Peer review...")
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

    docx_failed = False
    if export_docx:
        typer.echo(f"[5/{total_steps}] IR + DOCX export...")
        try:
            from vibewriting.models.paper_state import PaperState
            from vibewriting.rendering import (
                build_document_ir_from_paper_state,
                build_parity_report,
                render_docx_from_ir,
                write_document_ir,
                write_parity_report,
            )

            paper_state_path = output_dir / "paper_state.json"
            if not paper_state_path.exists():
                raise FileNotFoundError(f"Missing paper_state.json at {paper_state_path}")

            state = PaperState.model_validate_json(
                paper_state_path.read_text(encoding="utf-8")
            )
            document_ir = build_document_ir_from_paper_state(
                state,
                paper_dir,
                language="zh",
            )
            ir_path = output_dir / "document_ir.json"
            write_document_ir(document_ir, ir_path)

            resolved_reference_docx = reference_docx
            if resolved_reference_docx is None and settings.reference_docx_path:
                resolved_reference_docx = Path(settings.reference_docx_path)

            resolved_csl = csl_path
            if resolved_csl is None and settings.csl_path:
                resolved_csl = Path(settings.csl_path)

            bib_path = paper_dir / "bib" / "references.bib"
            docx_path = paper_dir / "build" / "main.docx"
            docx_result = render_docx_from_ir(
                document_ir,
                docx_path,
                working_dir=paper_dir,
                reference_docx=resolved_reference_docx,
                csl_path=resolved_csl,
                bibliography_path=bib_path if bib_path.exists() else None,
            )
            if not docx_result.success:
                docx_failed = True
                typer.echo(f"  CRITICAL: DOCX export failed: {docx_result.message}")
            else:
                typer.echo(f"  DOCX: {docx_result.output_path}")
                typer.echo(f"  Markdown: {docx_result.markdown_path}")

            parity = build_parity_report(document_ir, state)
            parity_path = output_dir / "parity_report.json"
            write_parity_report(parity, parity_path)
            typer.echo(f"  Parity report: {parity_path}")
            typer.echo(f"  Parity status: {'PASS' if parity['all_match'] else 'WARN'}")
        except Exception as e:
            docx_failed = True
            typer.echo(f"  CRITICAL: IR/DOCX pipeline failed: {e}")

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

    if has_critical or docx_failed:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
