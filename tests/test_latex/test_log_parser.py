"""Tests for LaTeX log parser."""

from __future__ import annotations

from vibewriting.latex.log_parser import (
    ErrorKind,
    LatexError,
    classify_error,
    extract_error_context,
    parse_log,
)


LOG_MISSING_PACKAGE = """
(./main.tex
! LaTeX Error: File `nonexistent.sty' not found.

Type X to quit or <RETURN> to proceed,
l.5 \\usepackage{nonexistent}
"""

LOG_UNDEFINED_CONTROL = """
(./sections/intro.tex
! Undefined control sequence.
l.12 \\badcommand
"""

LOG_SYNTAX_MISSING = """
(./sections/method.tex
! Missing $ inserted.
<inserted text>
                $
l.42 some math x^2
"""

LOG_FILE_NOT_FOUND = """
! I can't find file `missing.tex'.
l.3 \\input{missing}
"""

LOG_ENCODING = """
! Package inputenc Error: Invalid UTF-8 byte sequence.
l.10 ...
"""

LOG_PACKAGE_ERROR = """
! Package hyperref Error: Wrong DVI mode driver option `dvips'.
l.1 ...
"""

LOG_UNKNOWN = """
! Emergency stop.
l.1 \\end
"""


class TestParseLog:
    def test_parse_missing_package(self):
        errors = parse_log(LOG_MISSING_PACKAGE)
        assert len(errors) >= 1
        assert any("not found" in e.message.lower() or "file" in e.message.lower() for e in errors)

    def test_parse_undefined_control(self):
        errors = parse_log(LOG_UNDEFINED_CONTROL)
        assert len(errors) >= 1
        assert any(e.error_type == "undefined_control" for e in errors)

    def test_parse_syntax_missing(self):
        errors = parse_log(LOG_SYNTAX_MISSING)
        assert len(errors) >= 1

    def test_parse_file_not_found(self):
        errors = parse_log(LOG_FILE_NOT_FOUND)
        assert len(errors) >= 1
        assert any("find file" in e.message.lower() or "cant_find" in e.error_type for e in errors)

    def test_parse_encoding_error(self):
        errors = parse_log(LOG_ENCODING)
        assert len(errors) >= 1

    def test_parse_package_error(self):
        errors = parse_log(LOG_PACKAGE_ERROR)
        assert len(errors) >= 1
        assert any(e.error_type == "package_error" for e in errors)

    def test_parse_empty_log(self):
        errors = parse_log("")
        assert errors == []

    def test_parse_clean_log(self):
        errors = parse_log("Output written on main.pdf (5 pages).\n")
        assert errors == []


class TestClassifyError:
    def test_classify_missing_package(self):
        e = LatexError(None, None, "package_error", "Package hyperref Error: wrong driver")
        assert classify_error(e) == ErrorKind.MISSING_PACKAGE

    def test_classify_undefined_reference(self):
        e = LatexError(None, None, "undefined_control", "Undefined control sequence")
        assert classify_error(e) == ErrorKind.UNDEFINED_REFERENCE

    def test_classify_syntax_error(self):
        e = LatexError(None, None, "missing_token", "Missing $ inserted")
        assert classify_error(e) == ErrorKind.SYNTAX_ERROR

    def test_classify_missing_file(self):
        e = LatexError(None, None, "cant_find_file", "I can't find file `foo.tex'")
        assert classify_error(e) == ErrorKind.MISSING_FILE

    def test_classify_encoding(self):
        e = LatexError(None, None, "generic_error", "Invalid UTF-8 byte sequence")
        assert classify_error(e) == ErrorKind.ENCODING_ERROR

    def test_classify_unknown(self):
        e = LatexError(None, None, "generic_error", "Emergency stop")
        assert classify_error(e) == ErrorKind.UNKNOWN


class TestExtractErrorContext:
    def test_context_found(self):
        log = "line1\nline2\n! Missing $ inserted.\nline4\nline5\n"
        e = LatexError(None, None, "missing_token", "! Missing $ inserted.")
        ctx = extract_error_context(log, e, window=1)
        assert "Missing" in ctx

    def test_context_not_found(self):
        log = "all good\nno errors\n"
        e = LatexError(None, None, "generic_error", "nonexistent message xyz")
        ctx = extract_error_context(log, e)
        assert ctx == ""
