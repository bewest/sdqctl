"""
Base classes and types for verification.

The verification system provides a unified interface for checking
various aspects of the codebase: references, links, terminology,
traceability, and assertions.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, Any


@dataclass
class VerificationError:
    """A single verification error or warning."""
    
    file: str
    line: int | None
    message: str
    fix_hint: str | None = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "fix_hint": self.fix_hint,
        }


@dataclass
class VerificationResult:
    """Result of a verification run."""
    
    passed: bool
    errors: list[VerificationError] = field(default_factory=list)
    warnings: list[VerificationError] = field(default_factory=list)
    summary: str = ""
    details: dict = field(default_factory=dict)
    
    def to_markdown(self) -> str:
        """Format results as markdown for context injection."""
        lines = []
        
        # Status header
        status = "✅ Passed" if self.passed else "❌ Failed"
        lines.append(f"## Verification Result: {status}")
        lines.append("")
        
        # Summary
        if self.summary:
            lines.append(self.summary)
            lines.append("")
        
        # Errors
        if self.errors:
            lines.append(f"### Errors ({len(self.errors)})")
            lines.append("")
            for err in self.errors:
                loc = f"{err.file}"
                if err.line:
                    loc += f":{err.line}"
                lines.append(f"- **{loc}**: {err.message}")
                if err.fix_hint:
                    lines.append(f"  - Fix: {err.fix_hint}")
            lines.append("")
        
        # Warnings
        if self.warnings:
            lines.append(f"### Warnings ({len(self.warnings)})")
            lines.append("")
            for warn in self.warnings:
                loc = f"{warn.file}"
                if warn.line:
                    loc += f":{warn.line}"
                lines.append(f"- **{loc}**: {warn.message}")
            lines.append("")
        
        # Details
        if self.details:
            lines.append("### Details")
            lines.append("")
            for key, value in self.details.items():
                lines.append(f"- **{key}**: {value}")
            lines.append("")
        
        return "\n".join(lines)
    
    def to_json(self) -> dict:
        """Format results as JSON for CLI output."""
        return {
            "passed": self.passed,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "summary": self.summary,
            "details": self.details,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }


class Verifier(Protocol):
    """Protocol for verification implementations."""
    
    name: str
    description: str
    
    def verify(self, root: Path, **options: Any) -> VerificationResult:
        """Run verification and return results.
        
        Args:
            root: Root directory to verify
            **options: Verifier-specific options
            
        Returns:
            VerificationResult with pass/fail status and details
        """
        ...
