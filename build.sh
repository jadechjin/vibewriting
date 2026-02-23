#!/usr/bin/env bash
set -euo pipefail

RED='\033[31m'
GREEN='\033[32m'
YELLOW='\033[33m'
RESET='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PAPER_DIR="${SCRIPT_DIR}/paper"

info()  { printf "${GREEN}[INFO]${RESET} %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${RESET} %s\n" "$*"; }
error() { printf "${RED}[ERROR]${RESET} %s\n" "$*" >&2; }

require_cmd() {
    if ! command -v "$1" &>/dev/null; then
        error "$1 not found in PATH."
        error "Install TeX Live: https://tug.org/texlive/"
        exit 1
    fi
}

cmd_build() {
    require_cmd latexmk
    require_cmd xelatex
    info "Compiling paper with latexmk..."
    cd "${PAPER_DIR}"
    latexmk
    info "Build complete: paper/build/main.pdf"
}

cmd_watch() {
    require_cmd latexmk
    require_cmd xelatex
    info "Starting continuous compilation (Ctrl+C to stop)..."
    cd "${PAPER_DIR}"
    latexmk -pvc
}

cmd_clean() {
    info "Cleaning build artifacts..."
    if [ -d "${PAPER_DIR}/build" ]; then
        find "${PAPER_DIR}/build" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
        info "Cleaned paper/build/"
    else
        mkdir -p "${PAPER_DIR}/build"
        info "Created paper/build/"
    fi
}

cmd_check() {
    require_cmd checkcites
    local aux_file="${PAPER_DIR}/build/main.aux"
    if [ ! -f "${aux_file}" ]; then
        error "paper/build/main.aux not found. Run 'build' first."
        exit 1
    fi
    info "Running checkcites..."
    cd "${PAPER_DIR}"
    local rc=0
    checkcites build/main.aux || rc=$?
    if [ "${rc}" -ne 0 ]; then
        warn "checkcites reported issues (exit code ${rc}). Review output above."
    else
        info "Citation check complete. No issues found."
    fi
}

cmd_doi2bib() {
    local doi="${1:-}"
    if [ -z "${doi}" ]; then
        error "Usage: bash build.sh doi2bib <DOI>"
        exit 1
    fi
    info "Fetching BibTeX for DOI: ${doi}"
    curl -fsSLH "Accept: application/x-bibtex" "https://doi.org/${doi}"
    echo
}

usage() {
    cat <<EOF
Usage: bash build.sh <command> [args]

Commands:
  build           Compile paper with latexmk (XeLaTeX)
  watch           Continuous compilation mode
  clean           Remove build artifacts
  check           Run checkcites on citations
  doi2bib <DOI>   Convert DOI to BibTeX entry
EOF
}

case "${1:-}" in
    build)   cmd_build ;;
    watch)   cmd_watch ;;
    clean)   cmd_clean ;;
    check)   cmd_check ;;
    doi2bib) cmd_doi2bib "${2:-}" ;;
    *)       usage; exit 1 ;;
esac
