"""Double-blind review anonymization utilities."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

_AUTHOR_RE = re.compile(r"\\author\{[^}]*\}", re.DOTALL)
_AFFILIATION_RE = re.compile(r"\\(?:affiliation|institute)\{[^}]*\}", re.DOTALL)
_PERSONAL_BLOCK_RE = re.compile(
    r"%% PERSONAL_INFO\s*\n.*?%% PERSONAL_INFO\s*\n",
    re.DOTALL,
)

_IDENTITY_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("self-reference", re.compile(r"\b(?:our previous work|our earlier)\b", re.IGNORECASE), "Major"),
    ("institution", re.compile(r"\b(?:University|Institute|Laboratory|College|School)\s+of\b", re.IGNORECASE), "Minor"),
    ("personal-url", re.compile(r"https?://(?!doi\.org|arxiv\.org|github\.com/[^/]+/[^/]+\b)[^\s}]+~[^\s}]+"), "Major"),
    ("personal-url-tilde", re.compile(r"\\url\{[^}]*~[^}]*\}"), "Major"),
]

_SELF_CITE_RE = re.compile(r"\\cite[tp]?\{([^}]+)\}")


def anonymize_tex(paper_dir: Path, output_dir: Path) -> Path:
    anon_dir = output_dir / "anonymous"
    if anon_dir.exists():
        shutil.rmtree(anon_dir)
    shutil.copytree(paper_dir, anon_dir)

    for tex_file in anon_dir.rglob("*.tex"):
        content = tex_file.read_text(encoding="utf-8")
        content = _AUTHOR_RE.sub(r"\\author{Anonymous}", content)
        content = _AFFILIATION_RE.sub("", content)
        content = _PERSONAL_BLOCK_RE.sub("", content)
        tex_file.write_text(content, encoding="utf-8")

    return anon_dir


def check_anonymization(paper_dir: Path) -> list[dict]:
    issues: list[dict] = []

    for tex_file in paper_dir.rglob("*.tex"):
        content = tex_file.read_text(encoding="utf-8")
        rel_path = str(tex_file.relative_to(paper_dir))
        lines = content.splitlines()

        for line_num, line in enumerate(lines, start=1):
            for name, pattern, severity in _IDENTITY_PATTERNS:
                for match in pattern.finditer(line):
                    issues.append({
                        "file": rel_path,
                        "line": line_num,
                        "pattern": name,
                        "match": match.group(),
                        "severity": severity,
                    })

            for cite_match in _SELF_CITE_RE.finditer(line):
                keys = [k.strip() for k in cite_match.group(1).split(",")]
                for key in keys:
                    if _looks_like_self_cite(key, content):
                        issues.append({
                            "file": rel_path,
                            "line": line_num,
                            "pattern": "possible-self-citation",
                            "match": key,
                            "severity": "Major",
                        })

    return issues


def _looks_like_self_cite(bib_key: str, tex_content: str) -> bool:
    author_match = _AUTHOR_RE.search(tex_content)
    if not author_match:
        return False
    author_block = author_match.group().lower()
    key_lower = bib_key.lower()
    surnames = re.findall(r"[a-z]{3,}", author_block)
    return any(surname in key_lower for surname in surnames)
