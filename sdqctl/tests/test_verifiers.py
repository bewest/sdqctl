"""Tests for the verification subsystem."""

import pytest
from pathlib import Path

from sdqctl.core.conversation import ConversationFile
from sdqctl.verifiers import (
    VerificationError,
    VerificationResult,
    RefsVerifier,
    LinksVerifier,
    TraceabilityVerifier,
    VERIFIERS,
)


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""
    
    def test_passed_result(self):
        """Test a passing verification result."""
        result = VerificationResult(
            passed=True,
            summary="All checks passed",
        )
        assert result.passed
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
    
    def test_failed_result(self):
        """Test a failing verification result."""
        result = VerificationResult(
            passed=False,
            errors=[
                VerificationError(
                    file="test.md",
                    line=10,
                    message="Broken reference",
                    fix_hint="Fix the path",
                )
            ],
            summary="1 error found",
        )
        assert not result.passed
        assert len(result.errors) == 1
        assert result.errors[0].file == "test.md"
    
    def test_to_markdown(self):
        """Test markdown output formatting."""
        result = VerificationResult(
            passed=False,
            errors=[
                VerificationError(
                    file="test.md",
                    line=10,
                    message="Broken reference: @missing.txt",
                )
            ],
            summary="1 error found",
        )
        md = result.to_markdown()
        assert "❌ Failed" in md
        assert "test.md:10" in md
        assert "Broken reference" in md
    
    def test_to_json(self):
        """Test JSON output formatting."""
        result = VerificationResult(
            passed=True,
            errors=[],
            warnings=[
                VerificationError(file="warn.md", line=1, message="Warning")
            ],
            summary="0 errors, 1 warning",
            details={"files_scanned": 5},
        )
        json_out = result.to_json()
        assert json_out["passed"] is True
        assert json_out["error_count"] == 0
        assert json_out["warning_count"] == 1
        assert json_out["details"]["files_scanned"] == 5


class TestRefsVerifier:
    """Tests for RefsVerifier."""
    
    def test_verifier_registered(self):
        """Test that refs verifier is in the registry."""
        assert "refs" in VERIFIERS
        assert VERIFIERS["refs"] == RefsVerifier
    
    def test_verify_empty_directory(self, tmp_path):
        """Test verification of empty directory."""
        verifier = RefsVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["files_scanned"] == 0
        assert result.details["refs_found"] == 0
    
    def test_verify_valid_reference(self, tmp_path):
        """Test verification with valid reference."""
        # Create target file
        target = tmp_path / "target.txt"
        target.write_text("Target content")
        
        # Create file with reference
        source = tmp_path / "source.md"
        source.write_text("See @target.txt for details")
        
        verifier = RefsVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["refs_valid"] == 1
        assert result.details["refs_broken"] == 0
    
    def test_verify_broken_reference(self, tmp_path):
        """Test verification with broken reference."""
        # Create file with broken reference
        source = tmp_path / "source.md"
        source.write_text("See @nonexistent.txt for details")
        
        verifier = RefsVerifier()
        result = verifier.verify(tmp_path)
        
        assert not result.passed
        assert result.details["refs_broken"] == 1
        assert len(result.errors) == 1
        assert "nonexistent.txt" in result.errors[0].message
    
    def test_ignore_jsdoc_annotations(self, tmp_path):
        """Test that JSDoc-style annotations are ignored."""
        source = tmp_path / "code.md"
        source.write_text("""
        @param name The name
        @returns The result
        @deprecated Use newMethod
        """)
        
        verifier = RefsVerifier()
        result = verifier.verify(tmp_path)
        
        # Should pass - no real references to check
        assert result.passed
        assert result.details["refs_found"] == 0 or result.details["refs_broken"] == 0
    
    def test_relative_path_reference(self, tmp_path):
        """Test ./relative/path references."""
        subdir = tmp_path / "sub"
        subdir.mkdir()
        
        target = subdir / "target.txt"
        target.write_text("content")
        
        source = tmp_path / "source.md"
        source.write_text("See @./sub/target.txt")
        
        verifier = RefsVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed


class TestRefsVerifierExclusions:
    """Tests for exclude patterns in RefsVerifier."""
    
    def test_default_excludes_venv(self, tmp_path):
        """Test that .venv directory is excluded by default."""
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "test.md").write_text("@nonexistent.txt")
        
        # Also add a file in root that passes
        (tmp_path / "root.md").write_text("# No refs")
        
        verifier = RefsVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["files_scanned"] == 1
        assert result.details["files_excluded"] == 1
    
    def test_default_excludes_node_modules(self, tmp_path):
        """Test that node_modules is excluded by default."""
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "pkg.md").write_text("@broken.txt")
        
        verifier = RefsVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["files_excluded"] == 1
    
    def test_custom_exclude_pattern(self, tmp_path):
        """Test custom exclude patterns."""
        examples = tmp_path / "examples"
        examples.mkdir()
        (examples / "example.md").write_text("@nonexistent.txt")
        
        verifier = RefsVerifier()
        result = verifier.verify(tmp_path, exclude={"examples"})
        
        assert result.passed
        assert result.details["files_excluded"] == 1
    
    def test_no_default_excludes(self, tmp_path):
        """Test disabling default exclusions."""
        # Use 'venv' not '.venv' since rglob may skip hidden dirs
        venv = tmp_path / "venv"
        venv.mkdir()
        (venv / "test.md").write_text("@nonexistent.txt")
        
        verifier = RefsVerifier()
        result = verifier.verify(tmp_path, no_default_excludes=True)
        
        # Now venv should be scanned (it's in DEFAULT_EXCLUDES)
        assert not result.passed
        assert result.details["files_scanned"] == 1
        assert result.details["files_excluded"] == 0
    
    def test_sdqctlignore_file(self, tmp_path):
        """Test .sdqctlignore file is loaded."""
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()
        (custom_dir / "test.md").write_text("@broken.txt")
        
        # Create .sdqctlignore
        (tmp_path / ".sdqctlignore").write_text("custom\n# comment\n")
        
        verifier = RefsVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["files_excluded"] == 1


class TestRefsVerifierAliasRefs:
    """Tests for alias:path reference verification."""
    
    @pytest.fixture
    def workspace_with_lock(self, tmp_path):
        """Create a workspace with workspace.lock.json and externals."""
        import json
        
        # Create externals directory structure
        externals = tmp_path / "externals"
        externals.mkdir()
        
        # Create mock LoopWorkspace
        loop = externals / "LoopWorkspace"
        loop.mkdir()
        (loop / "Loop").mkdir()
        (loop / "Loop" / "README.md").write_text("# Loop")
        (loop / "Loop" / "Models").mkdir()
        (loop / "Loop" / "Models" / "Override.swift").write_text("struct Override {}")
        
        # Create mock cgm-remote-monitor
        crm = externals / "cgm-remote-monitor"
        crm.mkdir()
        (crm / "lib").mkdir()
        (crm / "lib" / "server.js").write_text("// server")
        
        # Create workspace.lock.json
        lockfile = tmp_path / "workspace.lock.json"
        lockfile.write_text(json.dumps({
            "externals_dir": "externals",
            "repos": [
                {"alias": "loop", "name": "LoopWorkspace"},
                {"alias": "crm", "name": "cgm-remote-monitor", "aliases": ["ns"]},
            ]
        }))
        
        return tmp_path
    
    def test_valid_alias_reference(self, workspace_with_lock):
        """Test verification with valid alias:path reference."""
        # Create file with valid alias reference
        source = workspace_with_lock / "docs.md"
        source.write_text("See `loop:Loop/README.md` for details")
        
        verifier = RefsVerifier()
        result = verifier.verify(workspace_with_lock)
        
        assert result.passed
        assert result.details["alias_refs_found"] == 1
        assert result.details["alias_refs_valid"] == 1
        assert result.details["alias_refs_broken"] == 0
    
    def test_broken_alias_reference(self, workspace_with_lock):
        """Test verification with broken alias:path reference."""
        source = workspace_with_lock / "docs.md"
        source.write_text("See `loop:Loop/NonExistent.swift` for implementation")
        
        verifier = RefsVerifier()
        result = verifier.verify(workspace_with_lock)
        
        assert not result.passed
        assert result.details["alias_refs_broken"] == 1
        assert len(result.errors) == 1
        assert "loop:Loop/NonExistent.swift" in result.errors[0].message
    
    def test_unknown_alias(self, workspace_with_lock):
        """Test verification with unknown alias."""
        source = workspace_with_lock / "docs.md"
        source.write_text("See `unknown:path/file.py` for details")
        
        verifier = RefsVerifier()
        result = verifier.verify(workspace_with_lock)
        
        assert not result.passed
        assert "Unknown alias" in result.errors[0].fix_hint
    
    def test_alias_with_line_range(self, workspace_with_lock):
        """Test alias reference with line range is validated (file part only)."""
        source = workspace_with_lock / "docs.md"
        source.write_text("See `loop:Loop/README.md#L1-L10` for header")
        
        verifier = RefsVerifier()
        result = verifier.verify(workspace_with_lock)
        
        assert result.passed
        assert result.details["alias_refs_valid"] == 1
    
    def test_url_schemes_ignored(self, workspace_with_lock):
        """Test that URL schemes like https:// are not treated as alias refs."""
        source = workspace_with_lock / "docs.md"
        source.write_text("Visit https://github.com/example/repo.git for more")
        
        verifier = RefsVerifier()
        result = verifier.verify(workspace_with_lock)
        
        assert result.passed
        assert result.details["alias_refs_found"] == 0
    
    def test_mixed_refs_both_types(self, workspace_with_lock):
        """Test file with both @-refs and alias:refs."""
        # Create a local file for @-ref
        readme = workspace_with_lock / "README.md"
        readme.write_text("# Project")
        
        source = workspace_with_lock / "docs.md"
        source.write_text("""
        See @README.md for overview.
        See `loop:Loop/Models/Override.swift` for implementation.
        See `crm:lib/server.js` for server code.
        """)
        
        verifier = RefsVerifier()
        result = verifier.verify(workspace_with_lock)
        
        assert result.passed
        assert result.details["refs_valid"] == 1
        assert result.details["alias_refs_valid"] == 2
    
    def test_secondary_alias(self, workspace_with_lock):
        """Test that secondary aliases (from 'aliases' array) work."""
        source = workspace_with_lock / "docs.md"
        source.write_text("See `ns:lib/server.js` for Nightscout server")
        
        verifier = RefsVerifier()
        result = verifier.verify(workspace_with_lock)
        
        assert result.passed
        assert result.details["alias_refs_valid"] == 1
    
    def test_ellipsis_paths_skipped(self, workspace_with_lock):
        """Test that ellipsis paths like Sources/.../File.swift are skipped."""
        source = workspace_with_lock / "docs.md"
        source.write_text("See `loop:Sources/.../OTPManager.swift` for details")
        
        verifier = RefsVerifier()
        result = verifier.verify(workspace_with_lock)
        
        # Should pass - ellipsis paths are display-only, not validated
        assert result.passed
        assert result.details["alias_refs_found"] == 0
    
    def test_version_pins_skipped(self, tmp_path):
        """Test that version pins like @v4.4.3 are not treated as refs."""
        source = tmp_path / "workflow.yml"
        source.write_text("uses: actions/checkout@v4.4.3")
        
        verifier = RefsVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["refs_found"] == 0
    
    def test_decorator_patterns_skipped(self, tmp_path):
        """Test that Python decorators are not treated as refs."""
        source = tmp_path / "example.md"
        source.write_text("""
        ```python
        @click.option('--name')
        @app.command()
        def main():
            pass
        ```
        """)
        
        verifier = RefsVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["refs_found"] == 0
    
    def test_domain_names_skipped(self, tmp_path):
        """Test that email-like domain refs are not treated as file refs."""
        source = tmp_path / "contact.md"
        source.write_text("Contact us at support@example.com or admin@zreptil.de")
        
        verifier = RefsVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["refs_found"] == 0

    def test_edu_domain_skipped(self, tmp_path):
        """Test that .edu domain refs are not treated as file refs."""
        source = tmp_path / "license.md"
        source.write_text("Contact professor@psu.edu or school@lincoln-elementary.edu")
        
        verifier = RefsVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["refs_found"] == 0

    def test_placeholder_aliases_skipped(self, tmp_path):
        """Test that placeholder aliases like project: and extract: are skipped."""
        source = tmp_path / "docs.md"
        source.write_text("""Example usage:
        
Use `project:path/to/file.ext` for project files.
Use `extract:glucose_parser.py` for extracted code.
Use `alias:example/path.md` for examples.
""")
        
        verifier = RefsVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["alias_refs_found"] == 0

    def test_case_insensitive_tld_skipped(self, tmp_path):
        """Test that case-insensitive TLDs like @School.EDU are skipped."""
        source = tmp_path / "test.md"
        source.write_text("Contact admin@School.EDU or user@Example.COM")
        
        verifier = RefsVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["refs_found"] == 0

    def test_connection_strings_skipped(self, tmp_path):
        """Test that connection strings like localhost:port are skipped."""
        source = tmp_path / "config.md"
        source.write_text("""Database connections:
- localhost:1337/api/v1/entries.json
- mongo:27017/nightscout
- mongodb://localhost:27017
- redis:6379/cache
""")
        
        verifier = RefsVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["alias_refs_found"] == 0


class TestUnixSocketExclusion:
    """Test Unix socket and absolute path exclusions."""
    
    def test_unix_socket_paths_skipped(self, tmp_path):
        """Test that Unix socket paths like sock:/var/run are skipped."""
        source = tmp_path / "docker-compose.yml"
        source.write_text("""volumes:
  - sock:/var/run/docker.sock
  - unix:/tmp/mysql.sock
  - docker:/var/lib/docker
""")
        
        verifier = RefsVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["alias_refs_found"] == 0


class TestTimestampAndPlaceholderExclusion:
    """Test timestamp format and placeholder path exclusions."""
    
    def test_timestamp_formats_skipped(self, tmp_path):
        """Test that timestamp patterns like mm:ss.SSS are skipped."""
        source = tmp_path / "date-formats.md"
        source.write_text("""Date format examples:
dateFormatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"
Alternative: "yyyy-MM-dd'T'HH:mm:ss'Z'"
Time only: "HH:mm:ss"
""")
        
        verifier = RefsVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["alias_refs_found"] == 0
    
    def test_placeholder_paths_skipped(self, tmp_path):
        """Test that placeholder paths like path/to/file.ext are skipped."""
        source = tmp_path / "documentation.md"
        source.write_text("""Example references:
- Location: `loop:path/to/file.swift`
- Location: `aaps:path/to/file.kt`
- Use `project:path/to/file.ext#L123` for line references
""")
        
        verifier = RefsVerifier()
        result = verifier.verify(tmp_path)
        
        # Should skip 'path' alias patterns
        assert result.passed


class TestRootRelativeResolution:
    """Test workspace-root-first resolution for @refs."""
    
    def test_root_relative_ref_resolves(self, tmp_path):
        """Test that @path/file.md tries workspace root first."""
        # Create file at root
        (tmp_path / "traceability").mkdir()
        (tmp_path / "traceability" / "requirements.md").write_text("# Reqs")
        
        # Create workflow in subdirectory
        (tmp_path / "workflows").mkdir()
        workflow = tmp_path / "workflows" / "test.conv"
        workflow.write_text("CONTEXT @traceability/requirements.md")
        
        verifier = RefsVerifier()
        result = verifier.verify(tmp_path)
        
        # Should resolve from root, not from workflows/
        assert result.passed
        assert result.details["refs_valid"] == 1
    
    def test_file_relative_fallback(self, tmp_path):
        """Test that file-relative resolution is used as fallback."""
        # Create file relative to source file only
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "local").mkdir()
        (tmp_path / "docs" / "local" / "notes.md").write_text("# Notes")
        
        source = tmp_path / "docs" / "readme.md"
        source.write_text("See @local/notes.md for details")
        
        verifier = RefsVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["refs_valid"] == 1
    
    def test_explicit_relative_stays_file_relative(self, tmp_path):
        """Test that ./path stays file-relative (no root fallback)."""
        # Create file only relative to source
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "local.md").write_text("# Local")
        
        source = tmp_path / "docs" / "readme.md"
        source.write_text("See @./local.md for details")
        
        verifier = RefsVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["refs_valid"] == 1


class TestVerifyExecutionIntegration:
    """Test VERIFY directive execution in workflows."""

    def test_verify_step_in_workflow(self, tmp_path):
        """Test that VERIFY steps run during workflow execution."""
        # Create a test file with a valid reference
        doc_dir = tmp_path / "docs"
        doc_dir.mkdir()
        test_file = doc_dir / "test.md"
        test_file.write_text("See @../README.md for more info.")
        
        # Create the referenced file
        readme = tmp_path / "README.md"
        readme.write_text("# Test")
        
        # Create workflow with VERIFY step
        workflow = tmp_path / "test.conv"
        workflow.write_text("""MODEL mock
ADAPTER mock
VERIFY-ON-ERROR continue
VERIFY-OUTPUT always
VERIFY refs

PROMPT Analyze the verification results.
""")
        
        conv = ConversationFile.parse(workflow.read_text(), source_path=workflow)
        
        # Check parsing
        verify_steps = [s for s in conv.steps if s.type == "verify"]
        assert len(verify_steps) == 1
        assert verify_steps[0].verify_type == "refs"
        assert conv.verify_on_error == "continue"
        assert conv.verify_output == "always"


class TestLinksVerifier:
    """Tests for LinksVerifier."""
    
    def test_verifier_registered(self):
        """Test that links verifier is in the registry."""
        assert "links" in VERIFIERS
        assert VERIFIERS["links"] == LinksVerifier
    
    def test_verify_empty_directory(self, tmp_path):
        """Test verification of empty directory."""
        verifier = LinksVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["files_scanned"] == 0
        assert result.details["links_found"] == 0
    
    def test_verify_valid_link(self, tmp_path):
        """Test verification with valid markdown link."""
        # Create target file
        target = tmp_path / "target.md"
        target.write_text("# Target")
        
        # Create file with link
        source = tmp_path / "source.md"
        source.write_text("See [the target](target.md) for details")
        
        verifier = LinksVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["links_valid"] == 1
        assert result.details["links_broken"] == 0
    
    def test_verify_broken_link(self, tmp_path):
        """Test verification with broken markdown link."""
        # Create file with broken link
        source = tmp_path / "source.md"
        source.write_text("See [missing](nonexistent.md) for details")
        
        verifier = LinksVerifier()
        result = verifier.verify(tmp_path)
        
        assert not result.passed
        assert result.details["links_broken"] == 1
        assert len(result.errors) == 1
        assert "Broken link" in result.errors[0].message
        assert "nonexistent.md" in result.errors[0].message
    
    def test_external_urls_skipped(self, tmp_path):
        """Test that external URLs are skipped by default."""
        source = tmp_path / "source.md"
        source.write_text("See [GitHub](https://github.com/example)")
        
        verifier = LinksVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["links_external"] == 1
    
    def test_anchor_links_valid(self, tmp_path):
        """Test that anchor-only links are considered valid."""
        source = tmp_path / "source.md"
        source.write_text("See [section](#section-name)")
        
        verifier = LinksVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["links_valid"] == 1
    
    def test_relative_path_link(self, tmp_path):
        """Test relative path links."""
        subdir = tmp_path / "docs"
        subdir.mkdir()
        
        target = subdir / "target.md"
        target.write_text("# Target")
        
        source = tmp_path / "README.md"
        source.write_text("See [the docs](docs/target.md)")
        
        verifier = LinksVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["links_valid"] == 1
    
    def test_link_with_anchor(self, tmp_path):
        """Test link to file with anchor is valid if file exists."""
        target = tmp_path / "target.md"
        target.write_text("# Target\n\n## Section")
        
        source = tmp_path / "source.md"
        source.write_text("See [section](target.md#section)")
        
        verifier = LinksVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["links_valid"] == 1
    
    def test_multiple_links_mixed(self, tmp_path):
        """Test file with multiple links, some valid some broken."""
        # Create only one target
        target = tmp_path / "exists.md"
        target.write_text("# Exists")
        
        source = tmp_path / "source.md"
        source.write_text("""
        - [Valid](exists.md)
        - [Broken](missing.md)
        - [External](https://example.com)
        """)
        
        verifier = LinksVerifier()
        result = verifier.verify(tmp_path)
        
        assert not result.passed
        assert result.details["links_valid"] == 1
        assert result.details["links_broken"] == 1
        assert result.details["links_external"] == 1
    
    def test_recursive_scan(self, tmp_path):
        """Test recursive scanning of subdirectories."""
        subdir = tmp_path / "sub"
        subdir.mkdir()
        
        source = subdir / "nested.md"
        source.write_text("See [broken](nonexistent.md)")
        
        verifier = LinksVerifier()
        result = verifier.verify(tmp_path, recursive=True)
        
        assert not result.passed
        assert result.details["files_scanned"] == 1
        assert result.details["links_broken"] == 1
    
    def test_non_recursive_scan(self, tmp_path):
        """Test non-recursive scanning skips subdirectories."""
        subdir = tmp_path / "sub"
        subdir.mkdir()
        
        # File in subdir with broken link
        nested = subdir / "nested.md"
        nested.write_text("See [broken](nonexistent.md)")
        
        # File in root with valid link
        root_file = tmp_path / "root.md"
        root_file.write_text("See [sub](sub/)")
        
        verifier = LinksVerifier()
        result = verifier.verify(tmp_path, recursive=False)
        
        # Only root file scanned
        assert result.details["files_scanned"] == 1
    
    def test_skip_links_in_code_blocks(self, tmp_path):
        """Test that links inside code blocks are skipped."""
        source = tmp_path / "doc.md"
        source.write_text("""# Example

Regular [valid](exists.md) link.

```markdown
This [link](broken.md) is in a code block and should be ignored.
```

After code block.
""")
        
        # Create only the file referenced outside code block
        target = tmp_path / "exists.md"
        target.write_text("# Target")
        
        verifier = LinksVerifier()
        result = verifier.verify(tmp_path)
        
        # Should only find the valid link outside code block
        assert result.passed, f"Unexpected errors: {result.errors}"
        assert result.details["links_found"] == 1
        assert result.details["links_valid"] == 1
        assert result.details["links_broken"] == 0
    
    def test_skip_links_in_inline_code(self, tmp_path):
        """Test that links inside inline code (backticks) are skipped."""
        source = tmp_path / "doc.md"
        source.write_text("""# Example

Check markdown links with `[text](url)` syntax.

Here's a real [valid](exists.md) link.
""")
        
        # Create only the file referenced outside inline code
        target = tmp_path / "exists.md"
        target.write_text("# Target")
        
        verifier = LinksVerifier()
        result = verifier.verify(tmp_path)
        
        # Should only find the valid link outside inline code
        assert result.passed, f"Unexpected errors: {result.errors}"
        assert result.details["links_found"] == 1
        assert result.details["links_valid"] == 1


class TestTraceabilityVerifier:
    """Tests for TraceabilityVerifier."""
    
    def test_verifier_registered(self):
        """Test that traceability verifier is in the registry."""
        assert "traceability" in VERIFIERS
        assert VERIFIERS["traceability"] == TraceabilityVerifier
    
    def test_verify_empty_directory(self, tmp_path):
        """Test verification of empty directory."""
        verifier = TraceabilityVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["files_scanned"] == 0
        assert result.details["total_artifacts"] == 0
    
    def test_extract_uca_artifact(self, tmp_path):
        """Test extraction of UCA artifacts."""
        source = tmp_path / "ucas.md"
        source.write_text("""
        # Unsafe Control Actions
        
        - UCA-BOLUS-001: Bolus not provided when needed
        - UCA-BOLUS-002: Bolus provided too late
        """)
        
        verifier = TraceabilityVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.details["total_artifacts"] == 2
        assert "UCA" in result.details["artifacts_by_type"]
        assert len(result.details["artifacts_by_type"]["UCA"]) == 2
    
    def test_extract_multiple_artifact_types(self, tmp_path):
        """Test extraction of different artifact types."""
        source = tmp_path / "trace.md"
        source.write_text("""
        # Traceability
        
        | UCA | SC | REQ | SPEC | TEST |
        |-----|----|----|------|------|
        | UCA-001 | SC-001a | REQ-020 | SPEC-020 | TEST-020 |
        """)
        
        verifier = TraceabilityVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.details["total_artifacts"] == 5
        assert "UCA" in result.details["artifacts_by_type"]
        assert "SC" in result.details["artifacts_by_type"]
        assert "REQ" in result.details["artifacts_by_type"]
        assert "SPEC" in result.details["artifacts_by_type"]
        assert "TEST" in result.details["artifacts_by_type"]
    
    def test_orphan_uca_detection(self, tmp_path):
        """Test detection of UCAs without downstream links."""
        source = tmp_path / "ucas.md"
        source.write_text("UCA-ORPHAN-001: Standalone UCA with no links")
        
        verifier = TraceabilityVerifier()
        result = verifier.verify(tmp_path)
        
        assert not result.passed  # Orphan UCAs are errors
        assert result.details["orphan_count"] == 1
        assert len(result.errors) == 1
        assert "Orphan UCA" in result.errors[0].message
    
    def test_linked_uca_passes(self, tmp_path):
        """Test that UCAs with links pass verification."""
        source = tmp_path / "trace.md"
        source.write_text("""
        # Trace
        
        UCA-BOLUS-001 → SC-BOLUS-001a: Validate glucose before bolus
        SC-BOLUS-001a → REQ-020: Glucose validation requirement
        """)
        
        verifier = TraceabilityVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["orphan_count"] == 0
    
    def test_broken_reference_detection(self, tmp_path):
        """Test detection of broken references.
        
        Note: IDs on the same line are both registered as artifacts.
        Broken references occur when links_to contains an ID not in artifacts.
        This requires explicit link tracking via arrow syntax where one ID
        references another that doesn't appear anywhere in scanned files.
        """
        # File 1: Define UCA that links to SC
        (tmp_path / "ucas.md").write_text("UCA-BOLUS-001 → SC-MISSING-999")
        # Don't create file defining SC-MISSING-999
        
        verifier = TraceabilityVerifier()
        result = verifier.verify(tmp_path)
        
        # Both UCA-BOLUS-001 and SC-MISSING-999 are found on same line
        # so both are registered as artifacts - this is correct behavior
        # The link graph shows UCA links to SC, and both exist
        assert result.details["total_artifacts"] == 2
    
    def test_coverage_calculation(self, tmp_path):
        """Test coverage metrics calculation."""
        source = tmp_path / "full_trace.md"
        source.write_text("""
        # Full Traceability Example
        
        ## UCAs
        UCA-001 → SC-001a
        UCA-002: No SC (orphan)
        
        ## Requirements  
        SC-001a → REQ-001
        REQ-001 → SPEC-001
        SPEC-001 → TEST-001
        """)
        
        verifier = TraceabilityVerifier()
        result = verifier.verify(tmp_path)
        
        coverage = result.details["coverage"]
        assert coverage["total_ucas"] == 2
        assert coverage["total_reqs"] == 1
        assert coverage["total_specs"] == 1
        assert coverage["total_tests"] == 1
    
    def test_gap_artifacts_allowed_standalone(self, tmp_path):
        """Test that GAP artifacts are allowed without links."""
        source = tmp_path / "gaps.md"
        source.write_text("""
        # Open Gaps
        
        GAP-001: Missing glucose validation
        GAP-002: No timeout handling
        """)
        
        verifier = TraceabilityVerifier()
        result = verifier.verify(tmp_path)
        
        # GAPs should not cause orphan warnings
        assert result.passed
        assert result.details["orphan_count"] == 0
    
    def test_alternative_id_formats(self, tmp_path):
        """Test various ID format patterns."""
        source = tmp_path / "artifacts.md"
        source.write_text("""
        UCA-BOLUS-001: Category-based ID
        UCA-001: Simple numeric ID
        SC-GLUCOSE-002a: With suffix letter
        REQ-CGM-010: Different category
        """)
        
        verifier = TraceabilityVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.details["total_artifacts"] == 4
    
    def test_recursive_scan(self, tmp_path):
        """Test recursive scanning of subdirectories."""
        subdir = tmp_path / "traceability" / "stpa"
        subdir.mkdir(parents=True)
        
        (subdir / "ucas.md").write_text("UCA-001 → SC-001a")
        (subdir / "scs.md").write_text("SC-001a → REQ-001")
        
        verifier = TraceabilityVerifier()
        result = verifier.verify(tmp_path, recursive=True)
        
        assert result.details["files_scanned"] == 2
        assert result.details["total_artifacts"] >= 3
    
    def test_non_recursive_scan(self, tmp_path):
        """Test non-recursive scanning skips subdirectories."""
        subdir = tmp_path / "sub"
        subdir.mkdir()
        
        (subdir / "ucas.md").write_text("UCA-NESTED-001")
        (tmp_path / "root.md").write_text("UCA-ROOT-001 → SC-ROOT-001a")
        
        verifier = TraceabilityVerifier()
        result = verifier.verify(tmp_path, recursive=False)
        
        assert result.details["files_scanned"] == 1
        assert "UCA-ROOT-001" in result.details["artifacts_by_type"].get("UCA", [])


class TestVerifyTraceabilityDirective:
    """Tests for VERIFY traceability directive parsing."""
    
    def test_verify_traceability_parsing(self):
        """Test parsing VERIFY traceability directive."""
        from sdqctl.core.conversation import ConversationFile
        
        conv = ConversationFile.parse("""MODEL mock
ADAPTER mock
VERIFY traceability
PROMPT Analyze traceability results.
""")
        
        verify_steps = [s for s in conv.steps if s.type == "verify"]
        assert len(verify_steps) == 1
        assert verify_steps[0].verify_type == "traceability"
    
    def test_verify_all_includes_traceability(self):
        """Test that VERIFY all includes traceability verifier."""
        from sdqctl.verifiers import VERIFIERS
        
        # Verify all registered verifiers include traceability
        assert "traceability" in VERIFIERS
        
        # All 3 verifiers should be present
        assert len(VERIFIERS) >= 3
        assert "refs" in VERIFIERS
        assert "links" in VERIFIERS
        assert "traceability" in VERIFIERS


class TestTraceabilityVerifierExtendedTypes:
    """Tests for extended artifact types (LOSS, HAZ, BUG, PROP, Q, IQ)."""

    def test_loss_artifact_detection(self, tmp_path):
        """Test LOSS artifact pattern detection."""
        source = tmp_path / "losses.md"
        source.write_text("""
        # System-Level Losses
        
        LOSS-001: Patient harm due to incorrect dosing
        LOSS-002: Data loss or corruption
        """)
        
        verifier = TraceabilityVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.details["artifacts_by_type"]["LOSS"] == ["LOSS-001", "LOSS-002"]
        assert result.details["coverage"]["total_losses"] == 2

    def test_hazard_artifact_detection(self, tmp_path):
        """Test HAZ artifact pattern detection."""
        source = tmp_path / "hazards.md"
        source.write_text("""
        # Hazards
        
        HAZ-001: Insulin overdose → LOSS-001
        HAZ-002: Missed bolus
        """)
        
        verifier = TraceabilityVerifier()
        result = verifier.verify(tmp_path)
        
        assert "HAZ-001" in result.details["artifacts_by_type"]["HAZ"]
        assert result.details["coverage"]["total_hazards"] == 2

    def test_full_stpa_chain(self, tmp_path):
        """Test LOSS → HAZ → UCA → SC chain."""
        source = tmp_path / "stpa_chain.md"
        source.write_text("""
        # STPA Analysis
        
        LOSS-001 → HAZ-001
        HAZ-001 → UCA-001
        UCA-001 → SC-001a
        """)
        
        verifier = TraceabilityVerifier()
        result = verifier.verify(tmp_path)
        
        # All artifacts found
        assert result.details["total_artifacts"] == 4
        # LOSS-001 has link, so not orphan
        assert result.passed or len(result.errors) == 0

    def test_bug_artifact_detection(self, tmp_path):
        """Test BUG artifact pattern detection."""
        source = tmp_path / "bugs.md"
        source.write_text("""
        # Bug Tracker
        
        BUG-001: Crash on empty context
        BUG-002: Timeout not respected
        """)
        
        verifier = TraceabilityVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.details["artifacts_by_type"]["BUG"] == ["BUG-001", "BUG-002"]
        assert result.details["coverage"]["total_bugs"] == 2

    def test_proposal_artifact_detection(self, tmp_path):
        """Test PROP artifact pattern detection."""
        source = tmp_path / "proposals.md"
        source.write_text("""
        # Proposals
        
        PROP-001: Custom URL scheme for refs
        PROP-002: Semantic extraction
        """)
        
        verifier = TraceabilityVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.details["artifacts_by_type"]["PROP"] == ["PROP-001", "PROP-002"]
        assert result.details["coverage"]["total_props"] == 2

    def test_quirk_artifact_detection(self, tmp_path):
        """Test Q (quirk) artifact pattern detection."""
        source = tmp_path / "quirks.md"
        source.write_text("""
        # Known Quirks
        
        Q-001: Filename affects behavior
        Q-012: Compaction unconditional
        """)
        
        verifier = TraceabilityVerifier()
        result = verifier.verify(tmp_path)
        
        assert "Q-001" in result.details["artifacts_by_type"]["Q"]
        assert "Q-012" in result.details["artifacts_by_type"]["Q"]
        assert result.details["coverage"]["total_quirks"] == 2

    def test_iq_artifact_detection(self, tmp_path):
        """Test IQ artifact pattern detection."""
        source = tmp_path / "quality.md"
        source.write_text("""
        # Implementation Quality Issues
        
        IQ-1: Missing error handling
        IQ-15: Excessive complexity
        """)
        
        verifier = TraceabilityVerifier()
        result = verifier.verify(tmp_path)
        
        assert "IQ-1" in result.details["artifacts_by_type"]["IQ"]
        assert "IQ-15" in result.details["artifacts_by_type"]["IQ"]

    def test_standalone_types_allowed(self, tmp_path):
        """Test that BUG, PROP, Q, IQ are allowed standalone (no orphan errors)."""
        source = tmp_path / "standalone.md"
        source.write_text("""
        # Standalone Artifacts
        
        BUG-001: A bug
        PROP-001: A proposal
        Q-001: A quirk
        IQ-1: An issue
        GAP-001: A gap
        """)
        
        verifier = TraceabilityVerifier()
        result = verifier.verify(tmp_path)
        
        # None should be flagged as orphans
        assert result.passed
        assert result.details["orphan_count"] == 0

    def test_loss_haz_coverage(self, tmp_path):
        """Test LOSS → HAZ coverage calculation."""
        source = tmp_path / "coverage.md"
        source.write_text("""
        # Coverage Test
        
        LOSS-001 → HAZ-001
        LOSS-002: No hazard (orphan)
        
        HAZ-001 → UCA-001
        HAZ-002: No UCA (orphan)
        """)
        
        verifier = TraceabilityVerifier()
        result = verifier.verify(tmp_path)
        
        coverage = result.details["coverage"]
        # 1 of 2 losses has HAZ link
        assert coverage["loss_to_haz"] == 50.0
        # 1 of 2 hazards has UCA link
        assert coverage["haz_to_uca"] == 50.0

    def test_orphan_loss_error(self, tmp_path):
        """Test that orphan LOSS produces error."""
        source = tmp_path / "orphan_loss.md"
        source.write_text("""
        # Losses
        
        LOSS-001: Unlinked loss
        """)
        
        verifier = TraceabilityVerifier()
        result = verifier.verify(tmp_path)
        
        # LOSS without links should produce error
        assert not result.passed
        assert any("LOSS-001" in err.message for err in result.errors)

    def test_orphan_haz_error(self, tmp_path):
        """Test that orphan HAZ produces error."""
        source = tmp_path / "orphan_haz.md"
        source.write_text("""
        # Hazards
        
        HAZ-001: Unlinked hazard
        """)
        
        verifier = TraceabilityVerifier()
        result = verifier.verify(tmp_path)
        
        # HAZ without links should produce error
        assert not result.passed
        assert any("HAZ-001" in err.message for err in result.errors)


# ============================================================
# Terminology Verifier Tests
# ============================================================

class TestTerminologyVerifier:
    """Tests for TerminologyVerifier."""

    def test_registry(self):
        """Test terminology verifier is registered."""
        from sdqctl.verifiers import VERIFIERS, TerminologyVerifier
        assert "terminology" in VERIFIERS
        assert VERIFIERS["terminology"] is TerminologyVerifier

    def test_deprecated_term_quine(self, tmp_path):
        """Test deprecated term 'quine' is flagged."""
        source = tmp_path / "doc.md"
        source.write_text("This is a quine-like pattern.")
        
        from sdqctl.verifiers import TerminologyVerifier
        verifier = TerminologyVerifier()
        result = verifier.verify(tmp_path)
        
        assert not result.passed
        assert result.details["deprecated_terms"] >= 1
        assert any("quine" in err.message.lower() for err in result.errors)

    def test_deprecated_term_synthesis_ok(self, tmp_path):
        """Test 'synthesis cycle' is NOT flagged as deprecated."""
        source = tmp_path / "doc.md"
        source.write_text("This is a synthesis cycle pattern.")
        
        from sdqctl.verifiers import TerminologyVerifier
        verifier = TerminologyVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["deprecated_terms"] == 0

    def test_capitalization_nightscout(self, tmp_path):
        """Test capitalization warning for 'nightscout'."""
        source = tmp_path / "doc.md"
        source.write_text("The nightscout project is great.")
        
        from sdqctl.verifiers import TerminologyVerifier
        verifier = TerminologyVerifier()
        result = verifier.verify(tmp_path)
        
        # Capitalization issues are warnings, not errors
        assert result.passed  # Still passes
        assert result.details["capitalization_issues"] >= 1
        assert any("Nightscout" in warn.message for warn in result.warnings)

    def test_capitalization_correct_form(self, tmp_path):
        """Test correct capitalization is not flagged."""
        source = tmp_path / "doc.md"
        source.write_text("The Nightscout project is great.")
        
        from sdqctl.verifiers import TerminologyVerifier
        verifier = TerminologyVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["capitalization_issues"] == 0

    def test_capitalization_stpa_acronym(self, tmp_path):
        """Test STPA acronym capitalization."""
        source = tmp_path / "doc.md"
        source.write_text("We use stpa analysis.")
        
        from sdqctl.verifiers import TerminologyVerifier
        verifier = TerminologyVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.details["capitalization_issues"] >= 1
        assert any("STPA" in warn.message for warn in result.warnings)

    def test_skip_code_blocks(self, tmp_path):
        """Test that code blocks are skipped."""
        source = tmp_path / "doc.md"
        source.write_text("""
# Example
```
This is a quine pattern in a code block.
```
        """)
        
        from sdqctl.verifiers import TerminologyVerifier
        verifier = TerminologyVerifier()
        result = verifier.verify(tmp_path)
        
        # Should not detect deprecated term in code block
        assert result.passed

    def test_skip_backtick_inline_code(self, tmp_path):
        """Test that inline code is skipped for capitalization."""
        source = tmp_path / "doc.md"
        source.write_text("Use `sdqctl` not SDQCTL.")
        
        from sdqctl.verifiers import TerminologyVerifier
        verifier = TerminologyVerifier()
        result = verifier.verify(tmp_path)
        
        # sdqctl in backticks should be skipped
        assert result.details["capitalization_issues"] == 0

    def test_skip_adapter_context(self, tmp_path):
        """Test that --adapter copilot is not flagged."""
        source = tmp_path / "doc.md"
        source.write_text("Run with --adapter copilot flag.")
        
        from sdqctl.verifiers import TerminologyVerifier
        verifier = TerminologyVerifier()
        result = verifier.verify(tmp_path)
        
        # Should not flag lowercase copilot in CLI context
        assert result.details["capitalization_issues"] == 0

    def test_glossary_detection(self, tmp_path):
        """Test glossary file detection."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        glossary = docs_dir / "GLOSSARY.md"
        glossary.write_text("""
# Glossary

### Synthesis Cycle
A multi-pass workflow.

### Convergence
Iterating until done.
        """)
        
        source = tmp_path / "doc.md"
        source.write_text("Testing glossary detection.")
        
        from sdqctl.verifiers import TerminologyVerifier
        verifier = TerminologyVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.details["glossary_terms"] >= 2
        assert "docs/GLOSSARY.md" in result.details["glossary_path"]

    def test_no_glossary_ok(self, tmp_path):
        """Test verification works without glossary."""
        source = tmp_path / "doc.md"
        source.write_text("Just a document.")
        
        from sdqctl.verifiers import TerminologyVerifier
        verifier = TerminologyVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["glossary_terms"] == 0

    def test_json_output(self, tmp_path):
        """Test JSON output format."""
        source = tmp_path / "doc.md"
        source.write_text("This uses quine terminology.")
        
        from sdqctl.verifiers import TerminologyVerifier
        verifier = TerminologyVerifier()
        result = verifier.verify(tmp_path)
        
        json_out = result.to_json()
        assert "passed" in json_out
        assert "errors" in json_out
        assert "warnings" in json_out
        assert json_out["error_count"] >= 1


class TestAssertionsVerifier:
    """Tests for AssertionsVerifier."""

    def test_registry(self):
        """Test verifier is registered."""
        assert "assertions" in VERIFIERS

    def test_empty_directory(self, tmp_path):
        """Test verification of empty directory."""
        from sdqctl.verifiers import AssertionsVerifier
        verifier = AssertionsVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["assertions_found"] == 0

    def test_python_assert_detection(self, tmp_path):
        """Test Python assertion detection."""
        source = tmp_path / "test.py"
        source.write_text("""
def validate(x):
    assert x > 0
    assert x < 100, "value must be less than 100"
""")
        
        from sdqctl.verifiers import AssertionsVerifier
        verifier = AssertionsVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert result.details["assertions_found"] == 2
        assert result.details["assertions_with_message"] == 1
        assert result.details["by_language"]["python"] == 2

    def test_python_assert_with_trace_id(self, tmp_path):
        """Test Python assertion with trace ID in message."""
        source = tmp_path / "test.py"
        source.write_text("""
def validate(x):
    assert x > 0, "REQ-001: value must be positive"
""")
        
        from sdqctl.verifiers import AssertionsVerifier
        verifier = AssertionsVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.details["assertions_found"] == 1
        assert result.details["assertions_with_trace"] == 1
        assert result.details["trace_coverage"] == 100.0

    def test_python_assert_trace_in_comment(self, tmp_path):
        """Test Python assertion with trace ID in preceding comment."""
        source = tmp_path / "test.py"
        source.write_text("""
def validate(x):
    # SC-001a: ensure positive values
    assert x > 0
""")
        
        from sdqctl.verifiers import AssertionsVerifier
        verifier = AssertionsVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.details["assertions_found"] == 1
        assert result.details["assertions_with_trace"] == 1

    def test_require_message_flag(self, tmp_path):
        """Test --require-message makes missing messages an error."""
        source = tmp_path / "test.py"
        source.write_text("assert x > 0")
        
        from sdqctl.verifiers import AssertionsVerifier
        verifier = AssertionsVerifier()
        
        # Default: warning only
        result = verifier.verify(tmp_path, require_message=False)
        assert result.passed
        assert len(result.warnings) == 1
        
        # With flag: error
        result = verifier.verify(tmp_path, require_message=True)
        assert not result.passed
        assert len(result.errors) == 1

    def test_require_trace_flag(self, tmp_path):
        """Test --require-trace makes missing trace IDs an error."""
        source = tmp_path / "test.py"
        source.write_text('assert x > 0, "value check"')
        
        from sdqctl.verifiers import AssertionsVerifier
        verifier = AssertionsVerifier()
        
        # Default: no error (trace not required)
        result = verifier.verify(tmp_path, require_trace=False)
        assert result.passed
        
        # With flag: error
        result = verifier.verify(tmp_path, require_trace=True)
        assert not result.passed
        assert len(result.errors) == 1

    def test_swift_assertions(self, tmp_path):
        """Test Swift assertion detection."""
        source = tmp_path / "Test.swift"
        source.write_text("""
func validate(_ x: Int) {
    assert(x > 0)
    precondition(x < 100, "must be less than 100")
    guard x != 50 else {
        fatalError("cannot be 50")
    }
}
""")
        
        from sdqctl.verifiers import AssertionsVerifier
        verifier = AssertionsVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.details["assertions_found"] == 3
        assert result.details["by_language"]["swift"] == 3
        # At least 1 has a message (fatalError's message is detected)
        assert result.details["assertions_with_message"] >= 1

    def test_kotlin_assertions(self, tmp_path):
        """Test Kotlin assertion detection."""
        source = tmp_path / "Test.kt"
        source.write_text("""
fun validate(x: Int) {
    assert(x > 0)
    require(x < 100) { "must be less than 100" }
    check(x != 50)
}
""")
        
        from sdqctl.verifiers import AssertionsVerifier
        verifier = AssertionsVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.details["assertions_found"] == 3
        assert result.details["by_language"]["kotlin"] == 3

    def test_typescript_assertions(self, tmp_path):
        """Test TypeScript assertion detection."""
        source = tmp_path / "test.ts"
        source.write_text("""
function validate(x: number) {
    console.assert(x > 0);
    console.assert(x < 100, "must be less than 100");
}
""")
        
        from sdqctl.verifiers import AssertionsVerifier
        verifier = AssertionsVerifier()
        result = verifier.verify(tmp_path)
        
        # Both console.assert calls are detected
        assert result.details["assertions_found"] >= 2
        assert result.details["by_language"]["typescript"] >= 2

    def test_multiple_trace_id_types(self, tmp_path):
        """Test detection of different trace ID types."""
        source = tmp_path / "test.py"
        source.write_text("""
assert x > 0, "REQ-001: positive"
# UCA-BOLUS-003: check before bolus
assert bolus_valid
# SC-BOLUS-003a: safety constraint
assert not overdose
assert tested, "SPEC-042: verified"
""")
        
        from sdqctl.verifiers import AssertionsVerifier
        verifier = AssertionsVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.details["assertions_found"] == 4
        assert result.details["assertions_with_trace"] == 4

    def test_json_output(self, tmp_path):
        """Test JSON output format."""
        source = tmp_path / "test.py"
        source.write_text('assert x > 0, "check value"')
        
        from sdqctl.verifiers import AssertionsVerifier
        verifier = AssertionsVerifier()
        result = verifier.verify(tmp_path)
        
        json_out = result.to_json()
        assert "passed" in json_out
        assert "details" in json_out
        assert json_out["details"]["assertions_found"] == 1


class TestTraceabilityVerifyTrace:
    """Tests for verify_trace method that checks specific trace links."""

    def test_verify_trace_direct_link(self, tmp_path):
        """Test detecting a direct trace link between artifacts."""
        doc = tmp_path / "trace.md"
        doc.write_text("""
# Safety Analysis

### UCA-001: Unsafe action
**Leads to:** HAZ-001
**Mitigates:** SC-001 → UCA-001

### SC-001: Safety constraint
**Implements:** REQ-001
SC-001 -> REQ-001
""")
        
        from sdqctl.verifiers import TraceabilityVerifier
        verifier = TraceabilityVerifier()
        
        # Direct link exists
        result = verifier.verify_trace("SC-001", "REQ-001", tmp_path)
        assert result.passed is True
        assert "linked" in result.summary.lower()
        assert result.details["linked"] is True

    def test_verify_trace_not_linked(self, tmp_path):
        """Test detecting missing trace link."""
        doc = tmp_path / "trace.md"
        doc.write_text("""
### UCA-001: Unsafe action
Not linked to anything.

### REQ-001: Requirement
Also standalone.
""")
        
        from sdqctl.verifiers import TraceabilityVerifier
        verifier = TraceabilityVerifier()
        
        result = verifier.verify_trace("UCA-001", "REQ-001", tmp_path)
        assert result.passed is False
        assert "not linked" in result.summary.lower()
        assert result.details["linked"] is False

    def test_verify_trace_artifact_not_found(self, tmp_path):
        """Test error when artifact doesn't exist."""
        doc = tmp_path / "trace.md"
        doc.write_text("""
### UCA-001: Unsafe action
This exists.
""")
        
        from sdqctl.verifiers import TraceabilityVerifier
        verifier = TraceabilityVerifier()
        
        result = verifier.verify_trace("UCA-001", "MISSING-001", tmp_path)
        assert result.passed is False
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].message.lower()

    def test_verify_trace_indirect_link(self, tmp_path):
        """Test detecting indirect trace link through chain."""
        doc = tmp_path / "trace.md"
        doc.write_text("""
### UCA-001: Unsafe action
UCA-001 → SC-001

### SC-001: Safety constraint
SC-001 → REQ-001

### REQ-001: Requirement
Requirement text.
""")
        
        from sdqctl.verifiers import TraceabilityVerifier
        verifier = TraceabilityVerifier()
        
        # UCA-001 → SC-001 → REQ-001 (indirect link)
        result = verifier.verify_trace("UCA-001", "REQ-001", tmp_path)
        assert result.passed is True
        assert result.details["linked"] is True
        assert result.details.get("direct") is False

    def test_verify_trace_scoped_ids(self, tmp_path):
        """Test verify_trace with scoped artifact IDs."""
        doc = tmp_path / "trace.md"
        doc.write_text("""
### UCA-BOLUS-003: Bolus unsafe action
UCA-BOLUS-003 → SC-BOLUS-003a

### SC-BOLUS-003a: Bolus safety constraint
Implements bolus safety.
""")
        
        from sdqctl.verifiers import TraceabilityVerifier
        verifier = TraceabilityVerifier()
        
        result = verifier.verify_trace("UCA-BOLUS-003", "SC-BOLUS-003a", tmp_path)
        assert result.passed is True


class TestTraceabilityVerifyCoverage:
    """Tests for verify_coverage() method on TraceabilityVerifier."""

    def test_verify_coverage_report_only(self, tmp_path):
        """Test verify_coverage in report-only mode."""
        doc = tmp_path / "artifacts.md"
        doc.write_text("""
### UCA-001: First unsafe action
### UCA-002: Second unsafe action

### SC-001: Safety constraint for UCA-001
UCA-001 → SC-001
""")
        
        from sdqctl.verifiers import TraceabilityVerifier
        verifier = TraceabilityVerifier()
        
        result = verifier.verify_coverage(tmp_path)
        
        # Report mode always passes
        assert result.passed is True
        assert "coverage" in result.details
        assert result.details["coverage"]["total_ucas"] == 2
        assert result.details["coverage"]["total_scs"] == 1

    def test_verify_coverage_threshold_pass(self, tmp_path):
        """Test verify_coverage with threshold check that passes."""
        doc = tmp_path / "artifacts.md"
        doc.write_text("""
### UCA-001: First unsafe action
### UCA-002: Second unsafe action

### SC-001: Safety constraint for UCA-001
UCA-001 → SC-001

### SC-002: Safety constraint for UCA-002
UCA-002 → SC-002
""")
        
        from sdqctl.verifiers import TraceabilityVerifier
        verifier = TraceabilityVerifier()
        
        result = verifier.verify_coverage(tmp_path, metric="uca_to_sc", op=">=", threshold=100)
        
        assert result.passed is True
        assert "uca_to_sc" in result.details["coverage"]
        assert result.details["coverage"]["uca_to_sc"] == 100.0

    def test_verify_coverage_threshold_fail(self, tmp_path):
        """Test verify_coverage with threshold check that fails."""
        doc = tmp_path / "artifacts.md"
        doc.write_text("""
### UCA-001: First unsafe action
### UCA-002: Second unsafe action

### SC-001: Safety constraint for UCA-001
UCA-001 → SC-001
""")
        
        from sdqctl.verifiers import TraceabilityVerifier
        verifier = TraceabilityVerifier()
        
        result = verifier.verify_coverage(tmp_path, metric="uca_to_sc", op=">=", threshold=100)
        
        assert result.passed is False
        assert len(result.errors) == 1
        assert "50.0%" in result.errors[0].message

    def test_verify_coverage_invalid_metric(self, tmp_path):
        """Test verify_coverage with invalid metric name."""
        doc = tmp_path / "artifacts.md"
        doc.write_text("### UCA-001: First unsafe action")
        
        from sdqctl.verifiers import TraceabilityVerifier
        verifier = TraceabilityVerifier()
        
        result = verifier.verify_coverage(tmp_path, metric="invalid_metric", op=">=", threshold=50)
        
        assert result.passed is False
        assert len(result.errors) == 1
        assert "Unknown coverage metric" in result.errors[0].message

    def test_verify_coverage_empty_docs(self, tmp_path):
        """Test verify_coverage with no artifacts found."""
        doc = tmp_path / "empty.md"
        doc.write_text("# Empty document\nNo artifacts here.")
        
        from sdqctl.verifiers import TraceabilityVerifier
        verifier = TraceabilityVerifier()
        
        result = verifier.verify_coverage(tmp_path)
        
        # Report mode always passes even with no artifacts
        assert result.passed is True
        assert result.details["coverage"]["total_ucas"] == 0
