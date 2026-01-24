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


class TestWorkspaceLockJsonAliases:
    """Tests for workspace.lock.json alias resolution."""

    @pytest.fixture
    def workspace_with_lock(self, tmp_path):
        """Create a workspace with workspace.lock.json."""
        import json
        
        # Create workspace structure
        externals = tmp_path / "externals"
        externals.mkdir()
        
        # Create mock repos
        crm = externals / "cgm-remote-monitor"
        crm.mkdir()
        (crm / "lib").mkdir()
        (crm / "lib" / "server.js").write_text("// server code")
        
        loop = externals / "LoopWorkspace"
        loop.mkdir()
        (loop / "Loop").mkdir()
        (loop / "Loop" / "Manager.swift").write_text("// swift code")
        
        # Create workspace.lock.json
        lockfile = tmp_path / "workspace.lock.json"
        lockfile.write_text(json.dumps({
            "externals_dir": "externals",
            "repos": [
                {"alias": "crm", "name": "cgm-remote-monitor", "aliases": ["ns"]},
                {"alias": "loop", "name": "LoopWorkspace"},
            ]
        }))
        
        return tmp_path

    def test_resolve_primary_alias(self, workspace_with_lock):
        """Resolve primary alias from workspace.lock.json."""
        from sdqctl.core.refcat import _resolve_workspace_alias
        
        result = _resolve_workspace_alias("crm", workspace_with_lock)
        assert result is not None
        assert result == workspace_with_lock / "externals" / "cgm-remote-monitor"

    def test_resolve_secondary_alias(self, workspace_with_lock):
        """Resolve secondary alias from aliases array."""
        from sdqctl.core.refcat import _resolve_workspace_alias
        
        result = _resolve_workspace_alias("ns", workspace_with_lock)
        assert result is not None
        assert result == workspace_with_lock / "externals" / "cgm-remote-monitor"

    def test_resolve_unknown_alias_returns_none(self, workspace_with_lock):
        """Unknown alias returns None (not found in lockfile)."""
        from sdqctl.core.refcat import _resolve_workspace_alias
        
        result = _resolve_workspace_alias("unknown", workspace_with_lock)
        assert result is None

    def test_full_extraction_with_workspace_alias(self, workspace_with_lock):
        """Extract content using workspace alias."""
        spec = RefSpec(path=Path("lib/server.js"), alias="crm")
        result = extract_content(spec, workspace_with_lock)
        assert "server code" in result.content

    def test_lockfile_in_parent_directory(self, workspace_with_lock):
        """Find lockfile when searching from subdirectory."""
        from sdqctl.core.refcat import _resolve_workspace_alias
        
        subdir = workspace_with_lock / "some" / "nested" / "dir"
        subdir.mkdir(parents=True)
        
        result = _resolve_workspace_alias("loop", subdir)
        assert result is not None
        assert result == workspace_with_lock / "externals" / "LoopWorkspace"


class TestGlobAndWorkflowPatterns:
    """Tests for glob pattern expansion and workflow loading."""

    @pytest.fixture
    def workspace_with_docs(self, tmp_path):
        """Create a workspace with docs and a workflow."""
        # Create docs directory with markdown files
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "readme.md").write_text("# Readme")
        (docs / "guide.md").write_text("# Guide")
        (docs / "api.md").write_text("# API")
        
        # Create a workflow file
        workflows = tmp_path / "workflows"
        workflows.mkdir()
        (workflows / "test.conv").write_text(dedent("""\
            MODEL gpt-4
            ADAPTER mock
            CONTEXT @docs/*.md
            CONTEXT @traceability/reqs.md
            CONTEXT-OPTIONAL @optional/file.md
            PROMPT Test prompt
        """))
        
        # Create traceability file
        trace = tmp_path / "traceability"
        trace.mkdir()
        (trace / "reqs.md").write_text("# Requirements")
        
        return tmp_path

    def test_load_workflow_context_patterns(self, workspace_with_docs):
        """Load CONTEXT patterns from workflow file."""
        from sdqctl.commands.refcat import _load_workflow_context_patterns
        
        workflow = workspace_with_docs / "workflows" / "test.conv"
        patterns = _load_workflow_context_patterns(workflow)
        
        assert "@docs/*.md" in patterns
        assert "@traceability/reqs.md" in patterns
        assert "@optional/file.md" in patterns
        assert len(patterns) == 3

    def test_expand_glob_patterns(self, workspace_with_docs):
        """Expand glob patterns to file paths."""
        from sdqctl.commands.refcat import _expand_glob_patterns
        
        refs = ["@docs/*.md", "@traceability/reqs.md"]
        expanded = _expand_glob_patterns(refs, workspace_with_docs)
        
        # Should have 3 docs + 1 non-glob ref
        paths = [p for p in expanded if isinstance(p, Path)]
        strings = [p for p in expanded if isinstance(p, str)]
        
        assert len(paths) == 3  # readme.md, guide.md, api.md
        assert len(strings) == 1  # @traceability/reqs.md (not a glob)

    def test_expand_preserves_line_refs(self, workspace_with_docs):
        """Glob expansion preserves refs with line numbers."""
        from sdqctl.commands.refcat import _expand_glob_patterns
        
        refs = ["@docs/readme.md#L1-L5", "alias:path/file.py#L10"]
        expanded = _expand_glob_patterns(refs, workspace_with_docs)
        
        # Should keep original strings (not expand)
        assert all(isinstance(p, str) for p in expanded)
        assert len(expanded) == 2
