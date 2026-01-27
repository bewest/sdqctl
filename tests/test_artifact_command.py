"""Tests for sdqctl artifact command."""

import json
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from sdqctl.cli import cli
from sdqctl.commands.artifact import (
    parse_type_and_category,
    scan_existing_ids,
    get_next_id,
)


class TestParseTypeAndCategory:
    """Test type/category parsing."""
    
    def test_simple_type(self):
        art_type, category = parse_type_and_category("REQ")
        assert art_type == "REQ"
        assert category is None
    
    def test_lowercase_type(self):
        art_type, category = parse_type_and_category("req")
        assert art_type == "REQ"
        assert category is None
    
    def test_category_type(self):
        art_type, category = parse_type_and_category("REQ-CGM")
        assert art_type == "REQ"
        assert category == "CGM"
    
    def test_category_lowercase(self):
        art_type, category = parse_type_and_category("uca-bolus")
        assert art_type == "UCA"
        assert category == "BOLUS"
    
    def test_multi_part_category(self):
        # Only first hyphen splits type from category
        art_type, category = parse_type_and_category("GAP-SYNC-V2")
        assert art_type == "GAP"
        assert category == "SYNC-V2"


class TestScanExistingIds:
    """Test scanning for existing artifact IDs."""
    
    def test_scan_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            found = scan_existing_ids(Path(tmpdir), "REQ")
            assert found == []
    
    def test_scan_simple_ids(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file with some REQ IDs
            test_file = Path(tmpdir) / "reqs.md"
            test_file.write_text("""
# Requirements

## REQ-001: First requirement
Statement here.

## REQ-002: Second requirement
Statement here.

## REQ-005: Fifth requirement (gap)
Statement here.
""")
            found = scan_existing_ids(Path(tmpdir), "REQ")
            ids = [id_ for id_, _ in found]
            assert "REQ-001" in ids
            assert "REQ-002" in ids
            assert "REQ-005" in ids
            assert len(found) == 3
    
    def test_scan_category_ids(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "ucas.md"
            test_file.write_text("""
# UCAs

## UCA-BOLUS-001: First bolus UCA
## UCA-BOLUS-002: Second bolus UCA
## UCA-PUMP-001: First pump UCA
## UCA-003: Simple UCA (no category)
""")
            # Scan for all UCAs
            all_ucas = scan_existing_ids(Path(tmpdir), "UCA")
            assert len(all_ucas) >= 3  # At least the 3 category UCAs
            
            # Scan for BOLUS-specific UCAs
            bolus_ucas = scan_existing_ids(Path(tmpdir), "UCA", "BOLUS")
            ids = [id_ for id_, _ in bolus_ucas]
            assert "UCA-BOLUS-001" in ids
            assert "UCA-BOLUS-002" in ids
            # UCA-PUMP-001 should not be in BOLUS category
            assert "UCA-PUMP-001" not in ids
    
    def test_scan_recursive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested structure
            subdir = Path(tmpdir) / "sub" / "nested"
            subdir.mkdir(parents=True)
            
            (Path(tmpdir) / "top.md").write_text("## GAP-SYNC-001: Top level gap")
            (subdir / "nested.md").write_text("## GAP-SYNC-002: Nested gap")
            
            found = scan_existing_ids(Path(tmpdir), "GAP", "SYNC", recursive=True)
            ids = [id_ for id_, _ in found]
            assert "GAP-SYNC-001" in ids
            assert "GAP-SYNC-002" in ids
    
    def test_scan_non_recursive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "sub"
            subdir.mkdir()
            
            (Path(tmpdir) / "top.md").write_text("## BUG-001: Top level bug")
            (subdir / "nested.md").write_text("## BUG-002: Nested bug")
            
            found = scan_existing_ids(Path(tmpdir), "BUG", recursive=False)
            ids = [id_ for id_, _ in found]
            assert "BUG-001" in ids
            assert "BUG-002" not in ids


class TestGetNextId:
    """Test next ID generation."""
    
    def test_empty_list(self):
        next_id = get_next_id("REQ", None, [])
        assert next_id == "REQ-001"
    
    def test_simple_increment(self):
        existing = [("REQ-001", 1), ("REQ-002", 2)]
        next_id = get_next_id("REQ", None, existing)
        assert next_id == "REQ-003"
    
    def test_gap_handling(self):
        # Should use max + 1, not fill gaps
        existing = [("REQ-001", 1), ("REQ-005", 5)]
        next_id = get_next_id("REQ", None, existing)
        assert next_id == "REQ-006"
    
    def test_category_increment(self):
        existing = [("REQ-CGM-001", 1), ("REQ-CGM-010", 10)]
        next_id = get_next_id("REQ", "CGM", existing)
        assert next_id == "REQ-CGM-011"
    
    def test_category_empty(self):
        next_id = get_next_id("UCA", "BOLUS", [])
        assert next_id == "UCA-BOLUS-001"


class TestArtifactNextCLI:
    """Test sdqctl artifact next CLI command."""
    
    def test_next_no_scan(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["artifact", "next", "REQ", "--no-scan"])
        assert result.exit_code == 0
        assert "REQ-001" in result.output
    
    def test_next_category_no_scan(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["artifact", "next", "UCA-BOLUS", "--no-scan"])
        assert result.exit_code == 0
        assert "UCA-BOLUS-001" in result.output
    
    def test_next_json_output(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["artifact", "next", "PROP", "--no-scan", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "PROP"
        assert data["next_id"] == "PROP-001"
        assert data["existing_count"] == 0
    
    def test_next_unknown_type(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["artifact", "next", "UNKNOWN"])
        assert result.exit_code == 1
        assert "Unknown artifact type" in result.output
    
    def test_next_with_scan(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.md"
            test_file.write_text("## SPEC-001\n## SPEC-005\n")
            
            result = runner.invoke(cli, ["artifact", "next", "SPEC", "--path", tmpdir])
            assert result.exit_code == 0
            assert "SPEC-006" in result.output


class TestArtifactListCLI:
    """Test sdqctl artifact list CLI command."""
    
    def test_list_specific_type(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.md"
            test_file.write_text("## Q-001\n## Q-002\n## Q-003\n")
            
            result = runner.invoke(cli, ["artifact", "list", "Q", "--path", tmpdir])
            assert result.exit_code == 0
            assert "Q-001" in result.output
            assert "Q-002" in result.output
            assert "Q-003" in result.output
    
    def test_list_all(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.md"
            test_file.write_text("## REQ-001\n## SPEC-001\n## TEST-001\n")
            
            result = runner.invoke(cli, ["artifact", "list", "--all", "--path", tmpdir])
            assert result.exit_code == 0
            # Should show table with types
            assert "REQ" in result.output
            assert "SPEC" in result.output
            assert "TEST" in result.output
    
    def test_list_json(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.md"
            test_file.write_text("## BUG-001\n## BUG-002\n")
            
            result = runner.invoke(cli, ["artifact", "list", "BUG", "--path", tmpdir, "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["type"] == "BUG"
            assert len(data["artifacts"]) == 2
    
    def test_list_empty(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(cli, ["artifact", "list", "HAZ", "--path", tmpdir])
            assert result.exit_code == 0
            assert "No HAZ artifacts found" in result.output


class TestArtifactRenameCLI:
    """Test sdqctl artifact rename CLI command."""
    
    def test_rename_dry_run(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "reqs.md"
            test_file.write_text("## REQ-001: Original requirement\nSee REQ-001 for details.\n")
            
            result = runner.invoke(cli, [
                "artifact", "rename", "REQ-001", "REQ-OVERRIDE-001",
                "--path", tmpdir, "--dry-run"
            ])
            assert result.exit_code == 0
            assert "Dry run" in result.output
            assert "REQ-001" in result.output
            assert "REQ-OVERRIDE-001" in result.output
            assert "2 reference" in result.output
            
            # Verify file was NOT changed
            content = test_file.read_text()
            assert "REQ-001" in content
            assert "REQ-OVERRIDE-001" not in content
    
    def test_rename_applies_changes(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "reqs.md"
            test_file.write_text("## REQ-001: Original requirement\nSee REQ-001 for details.\n")
            
            result = runner.invoke(cli, [
                "artifact", "rename", "REQ-001", "REQ-OVERRIDE-001",
                "--path", tmpdir
            ])
            assert result.exit_code == 0
            assert "Renamed" in result.output
            assert "2 replacement" in result.output
            
            # Verify file WAS changed
            content = test_file.read_text()
            assert "REQ-001" not in content
            assert "REQ-OVERRIDE-001" in content
    
    def test_rename_multiple_files(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "file1.md"
            file2 = Path(tmpdir) / "file2.md"
            file1.write_text("Uses UCA-003 from analysis.\n")
            file2.write_text("## UCA-003: Control action\nReferences UCA-003.\n")
            
            result = runner.invoke(cli, [
                "artifact", "rename", "UCA-003", "UCA-BOLUS-003",
                "--path", tmpdir
            ])
            assert result.exit_code == 0
            assert "3 replacement" in result.output
            assert "2 file" in result.output
            
            # Verify both files changed
            assert "UCA-BOLUS-003" in file1.read_text()
            assert "UCA-BOLUS-003" in file2.read_text()
    
    def test_rename_no_matches(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "empty.md"
            test_file.write_text("No artifacts here.\n")
            
            result = runner.invoke(cli, [
                "artifact", "rename", "NONEXISTENT-001", "NEW-001",
                "--path", tmpdir
            ])
            assert result.exit_code == 0
            assert "No references" in result.output
    
    def test_rename_json_output(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.md"
            test_file.write_text("## GAP-001: A gap\n")
            
            result = runner.invoke(cli, [
                "artifact", "rename", "GAP-001", "GAP-SYNC-001",
                "--path", tmpdir, "--json"
            ])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["old_id"] == "GAP-001"
            assert data["new_id"] == "GAP-SYNC-001"
            assert data["total_replacements"] == 1
            assert data["files_changed"] == 1
    
    def test_rename_dry_run_json(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.md"
            test_file.write_text("## SPEC-005: A spec\nSee SPEC-005.\n")
            
            result = runner.invoke(cli, [
                "artifact", "rename", "SPEC-005", "SPEC-CGM-005",
                "--path", tmpdir, "--dry-run", "--json"
            ])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["dry_run"] is True
            assert data["total_references"] == 2
            assert data["files_affected"] == 1
            
            # Verify file NOT changed
            content = test_file.read_text()
            assert "SPEC-005" in content
            assert "SPEC-CGM-005" not in content
    
    def test_rename_word_boundary(self):
        """Ensure rename only matches whole words, not substrings."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.md"
            # REQ-001 should match, but REQ-0012 and XREQ-001 should not
            test_file.write_text("REQ-001 and REQ-0012 and XREQ-001\n")
            
            result = runner.invoke(cli, [
                "artifact", "rename", "REQ-001", "REQ-NEW-001",
                "--path", tmpdir
            ])
            assert result.exit_code == 0
            
            content = test_file.read_text()
            assert "REQ-NEW-001" in content  # Changed
            assert "REQ-0012" in content     # Unchanged (different number)
            assert "XREQ-001" in content     # Unchanged (prefix)


class TestArtifactRetireCLI:
    """Test sdqctl artifact retire CLI command."""
    
    def test_retire_dry_run(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "reqs.md"
            test_file.write_text("### REQ-003: Old requirement\nThis is an old requirement.\n")
            
            result = runner.invoke(cli, [
                "artifact", "retire", "REQ-003",
                "--reason", "Superseded by REQ-010",
                "--path", tmpdir, "--dry-run"
            ])
            assert result.exit_code == 0
            assert "Dry run" in result.output
            assert "REQ-003" in result.output
            assert "[RETIRED]" in result.output
            assert "Superseded by REQ-010" in result.output
            
            # Verify file was NOT changed
            content = test_file.read_text()
            assert "[RETIRED]" not in content
    
    def test_retire_applies_changes(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "reqs.md"
            test_file.write_text("### REQ-003: Old requirement\nThis is an old requirement.\n")
            
            result = runner.invoke(cli, [
                "artifact", "retire", "REQ-003",
                "--reason", "Superseded by REQ-010",
                "--path", tmpdir
            ])
            assert result.exit_code == 0
            assert "Retired" in result.output
            
            # Verify file WAS changed
            content = test_file.read_text()
            assert "[RETIRED]" in content
            assert "**Status:** RETIRED" in content
            assert "Superseded by REQ-010" in content
    
    def test_retire_with_successor(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "gaps.md"
            test_file.write_text("### GAP-001: A gap to close\nDetails here.\n")
            
            result = runner.invoke(cli, [
                "artifact", "retire", "GAP-001",
                "--reason", "Fixed in v2.0",
                "--successor", "REQ-020",
                "--path", tmpdir
            ])
            assert result.exit_code == 0
            
            content = test_file.read_text()
            assert "[RETIRED]" in content
            assert "**Successor:** REQ-020" in content
    
    def test_retire_no_definition_found(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            # File has REQ-001 but no heading definition
            test_file = Path(tmpdir) / "notes.md"
            test_file.write_text("See REQ-001 for details.\n")
            
            result = runner.invoke(cli, [
                "artifact", "retire", "REQ-001",
                "--reason", "Test",
                "--path", tmpdir
            ])
            assert result.exit_code == 1
            assert "No definition heading found" in result.output
    
    def test_retire_not_found(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "empty.md"
            test_file.write_text("No artifacts here.\n")
            
            result = runner.invoke(cli, [
                "artifact", "retire", "NONEXISTENT-001",
                "--reason", "Test",
                "--path", tmpdir
            ])
            assert result.exit_code == 1
            assert "No references" in result.output
    
    def test_retire_json_output(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.md"
            test_file.write_text("## UCA-005: Control action\nDetails.\n")
            
            result = runner.invoke(cli, [
                "artifact", "retire", "UCA-005",
                "--reason", "Obsolete design",
                "--path", tmpdir, "--json"
            ])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["artifact_id"] == "UCA-005"
            assert data["status"] == "retired"
            assert data["reason"] == "Obsolete design"
            assert "date" in data
    
    def test_retire_dry_run_json(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.md"
            test_file.write_text("### SPEC-010: A spec\nDetails.\n")
            
            result = runner.invoke(cli, [
                "artifact", "retire", "SPEC-010",
                "--reason", "Merged into SPEC-020",
                "--successor", "SPEC-020",
                "--path", tmpdir, "--dry-run", "--json"
            ])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["dry_run"] is True
            assert data["artifact_id"] == "SPEC-010"
            assert "[RETIRED]" in data["retired_heading"]
            assert data["successor"] == "SPEC-020"
            
            # Verify file NOT changed
            content = test_file.read_text()
            assert "[RETIRED]" not in content
    
    def test_retire_idempotent(self):
        """Already retired artifacts should not get double-tagged."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            # File already has [RETIRED] in heading
            test_file = Path(tmpdir) / "test.md"
            content = (
                "### REQ-005: [RETIRED] Old req\n"
                "**Status:** RETIRED (2026-01-01)\n"
            )
            test_file.write_text(content)
            
            result = runner.invoke(cli, [
                "artifact", "retire", "REQ-005",
                "--reason", "Already retired",
                "--path", tmpdir, "--dry-run"
            ])
            assert result.exit_code == 0
            # The retired_heading should NOT have double [RETIRED]
            assert "[RETIRED] [RETIRED]" not in result.output
