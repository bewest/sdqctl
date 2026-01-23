"""Tests for the verification subsystem."""

import pytest
from pathlib import Path

from sdqctl.verifiers import (
    VerificationError,
    VerificationResult,
    RefsVerifier,
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
