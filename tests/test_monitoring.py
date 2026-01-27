"""Tests for monitoring module."""

from datetime import datetime
from pathlib import Path

import pytest

from sdqctl.monitoring import (
    Change,
    ChangeImpact,
    DriftReport,
    GitChangeDetector,
)


class TestChangeImpact:
    """Test ChangeImpact enum."""

    def test_impact_values(self):
        assert ChangeImpact.CRITICAL.value == "critical"
        assert ChangeImpact.HIGH.value == "high"
        assert ChangeImpact.MEDIUM.value == "medium"
        assert ChangeImpact.LOW.value == "low"


class TestChange:
    """Test Change dataclass."""

    def test_basic_creation(self):
        change = Change(
            repo=Path("/repo"),
            file_path=Path("src/model.py"),
            commit_hash="abc123",
            commit_date=datetime.now(),
            author="Test User",
            message="Update model",
            change_type="modified",
        )
        assert change.repo == Path("/repo")
        assert change.impact == ChangeImpact.LOW

    def test_is_significant_critical(self):
        change = Change(
            repo=Path("/repo"),
            file_path=Path("src/types.py"),
            commit_hash="abc123",
            commit_date=datetime.now(),
            author="Test User",
            message="Delete types",
            change_type="deleted",
            impact=ChangeImpact.CRITICAL,
        )
        assert change.is_significant is True

    def test_is_significant_high(self):
        change = Change(
            repo=Path("/repo"),
            file_path=Path("src/model.py"),
            commit_hash="abc123",
            commit_date=datetime.now(),
            author="Test User",
            message="Update model",
            change_type="modified",
            impact=ChangeImpact.HIGH,
        )
        assert change.is_significant is True

    def test_is_significant_low(self):
        change = Change(
            repo=Path("/repo"),
            file_path=Path("README.md"),
            commit_hash="abc123",
            commit_date=datetime.now(),
            author="Test User",
            message="Update docs",
            change_type="modified",
            impact=ChangeImpact.LOW,
        )
        assert change.is_significant is False


class TestDriftReport:
    """Test DriftReport dataclass."""

    def test_empty_report(self):
        report = DriftReport(
            generated_at=datetime.now(),
            since=None,
            repos_checked=[],
            changes=[],
        )
        assert report.critical_count == 0
        assert report.high_count == 0
        assert report.has_significant_drift is False

    def test_report_with_changes(self):
        changes = [
            Change(
                repo=Path("/repo"),
                file_path=Path("types.py"),
                commit_hash="abc123",
                commit_date=datetime.now(),
                author="User",
                message="Delete types",
                change_type="deleted",
                impact=ChangeImpact.CRITICAL,
            ),
            Change(
                repo=Path("/repo"),
                file_path=Path("model.py"),
                commit_hash="def456",
                commit_date=datetime.now(),
                author="User",
                message="Update model",
                change_type="modified",
                impact=ChangeImpact.HIGH,
            ),
        ]
        report = DriftReport(
            generated_at=datetime.now(),
            since=datetime(2026, 1, 1),
            repos_checked=[Path("/repo")],
            changes=changes,
        )
        assert report.critical_count == 1
        assert report.high_count == 1
        assert report.has_significant_drift is True

    def test_to_markdown(self):
        report = DriftReport(
            generated_at=datetime(2026, 1, 27, 12, 0, 0),
            since=datetime(2026, 1, 1),
            repos_checked=[Path("/repo")],
            changes=[],
        )
        md = report.to_markdown()
        assert "# Drift Report" in md
        assert "**Generated**:" in md
        assert "**Since**:" in md
        assert "| Impact | Count |" in md


class TestGitChangeDetector:
    """Test GitChangeDetector."""

    def test_init(self, tmp_path):
        detector = GitChangeDetector(tmp_path)
        assert detector.repo_path == tmp_path

    def test_classify_impact_model(self, tmp_path):
        detector = GitChangeDetector(tmp_path)
        change = Change(
            repo=tmp_path,
            file_path=Path("src/model.py"),
            commit_hash="abc123",
            commit_date=datetime.now(),
            author="User",
            message="Update",
            change_type="modified",
        )
        assert detector.classify_impact(change) == ChangeImpact.HIGH

    def test_classify_impact_type_deleted(self, tmp_path):
        detector = GitChangeDetector(tmp_path)
        change = Change(
            repo=tmp_path,
            file_path=Path("types/treatment.py"),
            commit_hash="abc123",
            commit_date=datetime.now(),
            author="User",
            message="Delete",
            change_type="deleted",
        )
        assert detector.classify_impact(change) == ChangeImpact.CRITICAL

    def test_classify_impact_treatment(self, tmp_path):
        detector = GitChangeDetector(tmp_path)
        change = Change(
            repo=tmp_path,
            file_path=Path("src/treatment_handler.py"),
            commit_hash="abc123",
            commit_date=datetime.now(),
            author="User",
            message="Update",
            change_type="modified",
        )
        assert detector.classify_impact(change) == ChangeImpact.HIGH

    def test_classify_impact_glucose(self, tmp_path):
        detector = GitChangeDetector(tmp_path)
        change = Change(
            repo=tmp_path,
            file_path=Path("src/glucose_reader.py"),
            commit_hash="abc123",
            commit_date=datetime.now(),
            author="User",
            message="Update",
            change_type="modified",
        )
        assert detector.classify_impact(change) == ChangeImpact.MEDIUM

    def test_classify_impact_readme(self, tmp_path):
        detector = GitChangeDetector(tmp_path)
        change = Change(
            repo=tmp_path,
            file_path=Path("README.md"),
            commit_hash="abc123",
            commit_date=datetime.now(),
            author="User",
            message="Update docs",
            change_type="modified",
        )
        assert detector.classify_impact(change) == ChangeImpact.LOW

    def test_parse_log_output_empty(self, tmp_path):
        detector = GitChangeDetector(tmp_path)
        result = detector._parse_log_output("")
        assert result == []

    def test_parse_log_output_single_commit(self, tmp_path):
        detector = GitChangeDetector(tmp_path)
        output = "abc123|2026-01-27T12:00:00+00:00|Test User|Test commit\nM\tsrc/file.py"
        result = detector._parse_log_output(output)
        assert len(result) == 1
        assert result[0]["hash"] == "abc123"
        assert result[0]["author"] == "Test User"
        assert result[0]["message"] == "Test commit"
        assert len(result[0]["files"]) == 1
        assert result[0]["files"][0]["type"] == "modified"

    def test_parse_log_output_multiple_commits(self, tmp_path):
        detector = GitChangeDetector(tmp_path)
        output = """abc123|2026-01-27T12:00:00+00:00|User1|First commit
M\tsrc/a.py
A\tsrc/b.py
def456|2026-01-26T12:00:00+00:00|User2|Second commit
D\tsrc/c.py"""
        result = detector._parse_log_output(output)
        assert len(result) == 2
        assert len(result[0]["files"]) == 2
        assert len(result[1]["files"]) == 1

    def test_matches_patterns(self, tmp_path):
        detector = GitChangeDetector(tmp_path)
        assert detector._matches_patterns(Path("src/models/user.py"), ["*/models/*"])
        assert detector._matches_patterns(Path("types/base.ts"), ["types/*"])
        assert not detector._matches_patterns(Path("README.md"), ["*/models/*"])

    def test_detect_changes_no_git(self, tmp_path):
        """detect_changes returns empty list if not a git repo."""
        detector = GitChangeDetector(tmp_path)
        changes = detector.detect_changes(since="2026-01-01")
        assert changes == []
