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
