"""
Tests for REFCAT - Reference Catalog module.

Tests parsing, extraction, formatting, and error handling.
"""

import pytest
from pathlib import Path
from textwrap import dedent

from sdqctl.core.refcat import (
    RefSpec,
    ExtractedContent,
    RefcatConfig,
    parse_ref,
    extract_content,
    format_for_context,
    format_for_json,
    extract_ref,
    detect_language,
    resolve_path,
    FileNotFoundError,
    InvalidRefError,
    PatternNotFoundError,
    AliasNotFoundError,
)


class TestParseRef:
    """Tests for parse_ref() function."""

    def test_basic_path(self):
        """Parse simple path without line range."""
        spec = parse_ref("@path/file.py")
        assert spec.path == Path("path/file.py")
        assert spec.alias is None
        assert spec.line_start is None
        assert spec.line_end is None

    def test_path_without_at(self):
        """Parse path without @ prefix."""
        spec = parse_ref("path/file.py")
        assert spec.path == Path("path/file.py")

    def test_single_line(self):
        """Parse single line reference."""
        spec = parse_ref("@path/file.py#L10")
        assert spec.path == Path("path/file.py")
        assert spec.line_start == 10
        assert spec.line_end == 10  # Single line

    def test_line_range(self):
        """Parse line range."""
        spec = parse_ref("@path/file.py#L10-L50")
        assert spec.path == Path("path/file.py")
        assert spec.line_start == 10
        assert spec.line_end == 50

    def test_line_range_without_L_prefix(self):
        """Parse line range without L prefix on end."""
        spec = parse_ref("@path/file.py#L10-50")
        assert spec.line_start == 10
        assert spec.line_end == 50

    def test_open_range_to_eof(self):
        """Parse open range to end of file."""
        spec = parse_ref("@path/file.py#L10-")
        assert spec.line_start == 10
        assert spec.line_end is None  # EOF

    def test_alias_path(self):
        """Parse alias:path format."""
        spec = parse_ref("loop:LoopKit/Sources/Algorithm.swift#L100")
        assert spec.alias == "loop"
        assert spec.path == Path("LoopKit/Sources/Algorithm.swift")
        assert spec.line_start == 100

    def test_pattern(self):
        """Parse pattern reference."""
        spec = parse_ref("@path/file.py#/def my_func/")
        assert spec.path == Path("path/file.py")
        assert spec.pattern == "def my_func"

    def test_invalid_ref(self):
        """Invalid ref raises error."""
        with pytest.raises(InvalidRefError):
            parse_ref("")

    def test_preserves_raw(self):
        """Raw ref string is preserved."""
        ref = "@path/file.py#L10-L50"
        spec = parse_ref(ref)
        assert spec.raw == ref


class TestExtractContent:
    """Tests for extract_content() function."""

    @pytest.fixture
    def temp_file(self, tmp_path):
        """Create a temporary test file."""
        content = dedent("""\
            line 1
            line 2
            line 3
            def my_func():
                pass
            line 6
            line 7
            line 8
            line 9
            line 10
        """).strip()
        file_path = tmp_path / "test.py"
        file_path.write_text(content)
        return file_path

    def test_extract_full_file(self, temp_file):
        """Extract entire file when no line range."""
        spec = RefSpec(path=temp_file)
        result = extract_content(spec, temp_file.parent)
        assert result.line_start == 1
        assert result.line_end == 10
        assert result.total_lines == 10
        assert len(result.lines) == 10

    def test_extract_line_range(self, temp_file):
        """Extract specific line range."""
        spec = RefSpec(path=temp_file, line_start=3, line_end=5)
        result = extract_content(spec, temp_file.parent)
        assert result.line_start == 3
        assert result.line_end == 5
        assert result.lines == ["line 3", "def my_func():", "    pass"]

    def test_extract_single_line(self, temp_file):
        """Extract single line."""
        spec = RefSpec(path=temp_file, line_start=4, line_end=4)
        result = extract_content(spec, temp_file.parent)
        assert result.lines == ["def my_func():"]

    def test_extract_to_eof(self, temp_file):
        """Extract from line to end of file."""
        spec = RefSpec(path=temp_file, line_start=8, line_end=None)
        result = extract_content(spec, temp_file.parent)
        assert result.line_start == 8
        assert result.line_end == 10
        assert len(result.lines) == 3

    def test_clamp_to_bounds(self, temp_file):
        """Lines out of range are clamped."""
        spec = RefSpec(path=temp_file, line_start=1, line_end=100)
        result = extract_content(spec, temp_file.parent)
        assert result.line_end == 10
        assert result.was_clamped is True

    def test_pattern_match(self, temp_file):
        """Extract line matching pattern."""
        spec = RefSpec(path=temp_file, pattern="def my_func")
        result = extract_content(spec, temp_file.parent)
        assert result.line_start == 4
        assert "def my_func" in result.lines[0]

    def test_pattern_not_found(self, temp_file):
        """Pattern not found raises error."""
        spec = RefSpec(path=temp_file, pattern="nonexistent_pattern")
        with pytest.raises(PatternNotFoundError):
            extract_content(spec, temp_file.parent)

    def test_file_not_found(self, tmp_path):
        """Missing file raises error."""
        spec = RefSpec(path=Path("nonexistent.py"))
        with pytest.raises(FileNotFoundError):
            extract_content(spec, tmp_path)


class TestFormatForContext:
    """Tests for format_for_context() function."""

    @pytest.fixture
    def extracted(self, tmp_path):
        """Create sample extracted content."""
        return ExtractedContent(
            path=tmp_path / "test.py",
            content="def foo():\n    pass",
            lines=["def foo():", "    pass"],
            line_start=10,
            line_end=11,
            total_lines=100,
            cwd=tmp_path,
        )

    def test_format_with_line_numbers(self, extracted):
        """Format includes line numbers for partial extraction."""
        result = format_for_context(extracted)
        assert "10 |" in result
        assert "11 |" in result
        assert "def foo():" in result

    def test_format_header_includes_range(self, extracted):
        """Header shows line range."""
        result = format_for_context(extracted)
        assert ":10-11" in result

    def test_format_header_includes_cwd(self, extracted):
        """Header includes CWD reference."""
        result = format_for_context(extracted)
        assert "(relative to" in result

    def test_format_detects_language(self, extracted):
        """Language is detected from extension."""
        result = format_for_context(extracted)
        assert "```python" in result

    def test_format_no_line_numbers(self, extracted):
        """Can disable line numbers."""
        config = RefcatConfig(show_line_numbers=False)
        result = format_for_context(extracted, config)
        assert "10 |" not in result

    def test_format_no_cwd(self, extracted):
        """Can disable CWD in header."""
        config = RefcatConfig(show_cwd=False)
        result = format_for_context(extracted, config)
        assert "(relative to" not in result


class TestFormatForJson:
    """Tests for format_for_json() function."""

    def test_json_format(self, tmp_path):
        """JSON output includes all fields."""
        extracted = ExtractedContent(
            path=tmp_path / "test.py",
            content="test content",
            lines=["test content"],
            line_start=1,
            line_end=1,
            total_lines=10,
            cwd=tmp_path,
            was_clamped=False,
        )
        result = format_for_json(extracted)
        assert "path" in result
        assert "line_start" in result
        assert "line_end" in result
        assert "content" in result
        assert "lines" in result
        assert result["was_clamped"] is False


class TestDetectLanguage:
    """Tests for detect_language() function."""

    def test_python(self):
        assert detect_language(Path("file.py")) == "python"

    def test_javascript(self):
        assert detect_language(Path("file.js")) == "javascript"

    def test_typescript(self):
        assert detect_language(Path("file.ts")) == "typescript"

    def test_swift(self):
        assert detect_language(Path("file.swift")) == "swift"

    def test_unknown(self):
        """Unknown extension returns extension itself."""
        result = detect_language(Path("file.xyz"))
        assert result == "xyz"


class TestExtractRefHighLevel:
    """Tests for extract_ref() high-level API."""

    @pytest.fixture
    def temp_file(self, tmp_path):
        """Create a temporary test file."""
        file_path = tmp_path / "sample.py"
        file_path.write_text("line 1\nline 2\nline 3\n")
        return file_path

    def test_extract_ref_simple(self, temp_file):
        """High-level API works end-to-end."""
        result = extract_ref(f"@{temp_file}#L1-L2", cwd=temp_file.parent)
        assert "line 1" in result
        assert "line 2" in result
        assert "```python" in result


class TestAliasResolution:
    """Tests for alias handling."""

    def test_unknown_alias_raises(self, tmp_path):
        """Unknown alias raises AliasNotFoundError."""
        spec = RefSpec(path=Path("file.py"), alias="unknown_alias")
        with pytest.raises(AliasNotFoundError):
            resolve_path(spec, tmp_path)

    def test_alias_with_mapping(self, tmp_path):
        """Alias resolves with provided mapping."""
        # Create file
        (tmp_path / "file.py").write_text("content")
        
        spec = RefSpec(path=Path("file.py"), alias="test")
        aliases = {"test": tmp_path}
        
        result = resolve_path(spec, tmp_path, aliases)
        assert result.exists()
