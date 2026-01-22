"""
Tests for context file validation.
"""

import pytest
from pathlib import Path
from sdqctl.core.conversation import ConversationFile
from sdqctl.core.exceptions import MissingContextFiles, ExitCode


class TestValidateContextFiles:
    """Test context file validation."""

    def test_no_context_files_returns_empty(self):
        """Workflow with no context files returns empty errors and warnings."""
        conv = ConversationFile(prompts=["Test prompt"])
        errors, warnings = conv.validate_context_files()
        assert errors == []
        assert warnings == []

    def test_existing_file_returns_empty(self, tmp_path):
        """Existing file returns empty errors list."""
        # Create a test file
        test_file = tmp_path / "existing.md"
        test_file.write_text("# Test")
        
        # Create workflow pointing to it
        workflow = tmp_path / "test.conv"
        workflow.write_text(f"CONTEXT @existing.md\nPROMPT Test")
        
        conv = ConversationFile.from_file(workflow)
        errors, warnings = conv.validate_context_files()
        assert errors == []

    def test_missing_file_returns_tuple(self, tmp_path):
        """Missing file returns (pattern, resolved_path) tuple in errors."""
        workflow = tmp_path / "test.conv"
        workflow.write_text("CONTEXT @nonexistent.md\nPROMPT Test")
        
        conv = ConversationFile.from_file(workflow)
        errors, warnings = conv.validate_context_files()
        
        assert len(errors) == 1
        pattern, resolved = errors[0]
        assert pattern == "@nonexistent.md"
        assert "nonexistent.md" in str(resolved)

    def test_multiple_missing_files(self, tmp_path):
        """Multiple missing files all returned in errors."""
        workflow = tmp_path / "test.conv"
        workflow.write_text("""
CONTEXT @missing1.md
CONTEXT @missing2.js
CONTEXT @missing3.py
PROMPT Test
""")
        
        conv = ConversationFile.from_file(workflow)
        errors, warnings = conv.validate_context_files()
        
        assert len(errors) == 3
        patterns = [p for p, _ in errors]
        assert "@missing1.md" in patterns
        assert "@missing2.js" in patterns
        assert "@missing3.py" in patterns

    def test_glob_pattern_no_matches_returns_missing(self, tmp_path):
        """Glob pattern with no matches counts as missing."""
        workflow = tmp_path / "test.conv"
        workflow.write_text("CONTEXT @lib/**/*.nonexistent\nPROMPT Test")
        
        conv = ConversationFile.from_file(workflow)
        errors, warnings = conv.validate_context_files()
        
        assert len(errors) == 1

    def test_glob_pattern_with_matches_returns_empty(self, tmp_path):
        """Glob pattern with matches returns empty errors list."""
        # Create matching files
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()
        (lib_dir / "auth.js").write_text("// auth")
        (lib_dir / "api.js").write_text("// api")
        
        workflow = tmp_path / "test.conv"
        workflow.write_text("CONTEXT @lib/*.js\nPROMPT Test")
        
        conv = ConversationFile.from_file(workflow)
        errors, warnings = conv.validate_context_files()
        
        assert errors == []

    def test_mixed_existing_and_missing(self, tmp_path):
        """Only missing files returned in errors when some exist."""
        # Create one file
        (tmp_path / "exists.md").write_text("# Exists")
        
        workflow = tmp_path / "test.conv"
        workflow.write_text("""
CONTEXT @exists.md
CONTEXT @missing.md
PROMPT Test
""")
        
        conv = ConversationFile.from_file(workflow)
        errors, warnings = conv.validate_context_files()
        
        assert len(errors) == 1
        assert errors[0][0] == "@missing.md"

    def test_inline_content_not_validated(self, tmp_path):
        """CONTEXT without @ prefix is inline content, not validated."""
        workflow = tmp_path / "test.conv"
        workflow.write_text("""
CONTEXT Here is some inline context content
PROMPT Test
""")
        
        conv = ConversationFile.from_file(workflow)
        errors, warnings = conv.validate_context_files()
        
        assert errors == []
        assert warnings == []

    def test_resolves_relative_to_workflow(self, tmp_path):
        """Files resolved relative to workflow location."""
        # Create subdir structure
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()
        
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "readme.md").write_text("# README")
        
        # Workflow in workflows/ referencing ../docs/
        workflow = workflows_dir / "test.conv"
        workflow.write_text("CONTEXT @../docs/readme.md\nPROMPT Test")
        
        conv = ConversationFile.from_file(workflow)
        errors, warnings = conv.validate_context_files()
        
        assert errors == []
    
    def test_optional_context_returns_warnings(self, tmp_path):
        """CONTEXT-OPTIONAL patterns return warnings, not errors."""
        workflow = tmp_path / "test.conv"
        workflow.write_text("""
CONTEXT-OPTIONAL @optional-file.md
PROMPT Test
""")
        
        conv = ConversationFile.from_file(workflow)
        errors, warnings = conv.validate_context_files()
        
        assert errors == []
        assert len(warnings) == 1
        assert "@optional-file.md" in warnings[0][0]
    
    def test_context_exclude_skips_pattern(self, tmp_path):
        """CONTEXT-EXCLUDE patterns are skipped as warnings."""
        workflow = tmp_path / "test.conv"
        workflow.write_text("""
CONTEXT-EXCLUDE missing.md
CONTEXT @missing.md
PROMPT Test
""")
        
        conv = ConversationFile.from_file(workflow)
        errors, warnings = conv.validate_context_files()
        
        assert errors == []
        assert len(warnings) == 1
    
    def test_allow_missing_converts_errors_to_warnings(self, tmp_path):
        """allow_missing=True moves all errors to warnings."""
        workflow = tmp_path / "test.conv"
        workflow.write_text("CONTEXT @missing.md\nPROMPT Test")
        
        conv = ConversationFile.from_file(workflow)
        errors, warnings = conv.validate_context_files(allow_missing=True)
        
        assert errors == []
        assert len(warnings) == 1
    
    def test_exclude_patterns_parameter(self, tmp_path):
        """exclude_patterns parameter skips matching patterns."""
        workflow = tmp_path / "test.conv"
        workflow.write_text("""
CONTEXT @docs/api.md
CONTEXT @tests/test.js
PROMPT Test
""")
        
        conv = ConversationFile.from_file(workflow)
        errors, warnings = conv.validate_context_files(exclude_patterns=["docs/**", "tests/**"])
        
        assert errors == []
        assert len(warnings) == 2


class TestMissingContextFilesException:
    """Test MissingContextFiles exception behavior."""

    def test_single_file_message(self):
        """Single file produces singular message."""
        exc = MissingContextFiles(["@missing.md"])
        assert "Missing mandatory context file:" in str(exc)
        assert "@missing.md" in str(exc)

    def test_multiple_files_message(self):
        """Multiple files produces plural message."""
        exc = MissingContextFiles(["@a.md", "@b.md", "@c.md"])
        assert "Missing 3 mandatory context files:" in str(exc)

    def test_exit_code(self):
        """Exception has correct exit code."""
        exc = MissingContextFiles(["@missing.md"])
        assert exc.exit_code == ExitCode.MISSING_FILES
        assert exc.exit_code == 2


class TestContextValidationIntegration:
    """Integration tests for context validation in commands."""

    def test_cycle_command_detects_missing(self, cli_runner, tmp_path):
        """Cycle command exits on missing context files."""
        from sdqctl.cli import cli
        
        workflow = tmp_path / "test.conv"
        workflow.write_text("""
MODEL gpt-4
ADAPTER mock
CONTEXT @nonexistent-file.md
PROMPT Analyze
""")
        
        result = cli_runner.invoke(cli, ["cycle", str(workflow)])
        
        # Should fail with missing files error
        assert result.exit_code != 0
        assert "Missing" in result.output or "missing" in result.output.lower()

    def test_run_command_detects_missing(self, cli_runner, tmp_path):
        """Run command exits on missing context files."""
        from sdqctl.cli import cli
        
        workflow = tmp_path / "test.conv"
        workflow.write_text("""
MODEL gpt-4
ADAPTER mock
CONTEXT @does-not-exist.js
PROMPT Test
""")
        
        result = cli_runner.invoke(cli, ["run", str(workflow)])
        
        # Should fail with missing files error
        assert result.exit_code != 0
