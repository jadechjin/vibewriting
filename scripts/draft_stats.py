"""Collect draft statistics for the paper."""
import json
import re
from pathlib import Path


def main():
    state = json.loads(Path("output/paper_state.json").read_text(encoding="utf-8"))
    sections = state.get("sections", [])
    drafted = [s for s in sections if s.get("status") == "drafted"]

    cite_pat = re.compile(r"\\cite[pt]?\{[^}]+\}")
    claim_pat = re.compile(r"CLAIM_ID: EC-")

    total_cites = 0
    total_claims = 0
    total_words = 0
    for s in sections:
        tex_path = Path("paper") / s.get("tex_file", "")
        if tex_path.exists():
            content = tex_path.read_text(encoding="utf-8")
            total_cites += len(cite_pat.findall(content))
            total_claims += len(claim_pat.findall(content))
            total_words += len(content.split())

    print(f"sections_total: {len(sections)}")
    print(f"sections_drafted: {len(drafted)}")
    print(f"total_citations: {total_cites}")
    print(f"total_claims: {total_claims}")
    print(f"total_words: {total_words}")

    pdf = Path("paper/build/main.pdf")
    print(f"pdf_exists: {pdf.exists()}")
    if pdf.exists():
        print(f"pdf_size: {pdf.stat().st_size} bytes")


if __name__ == "__main__":
    main()
