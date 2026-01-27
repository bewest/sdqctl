"""
Continuous monitoring for drift detection and alignment tracking.

Detects changes in external repositories that may affect alignment,
identifies breaking changes, and surfaces alignment opportunities.

See: proposals/CONTINUOUS-MONITORING.md

Usage:
    from sdqctl.monitoring import ChangeDetector, DriftReport
    
    detector = GitChangeDetector(repo_path)
    changes = detector.detect_changes(since="2026-01-01")
    report = DriftReport.from_changes(changes)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Protocol


class ChangeImpact(Enum):
    """Impact level of a detected change."""
    
    CRITICAL = "critical"  # Breaking change, requires immediate attention
    HIGH = "high"          # Significant change, likely affects alignment
    MEDIUM = "medium"      # Moderate change, may affect alignment
    LOW = "low"            # Minor change, unlikely to affect alignment


@dataclass
class Change:
    """A detected change in a repository."""
    
    repo: Path
    file_path: Path
    commit_hash: str
    commit_date: datetime
    author: str
    message: str
    change_type: str  # added, modified, deleted, renamed
    lines_added: int = 0
    lines_deleted: int = 0
    impact: ChangeImpact = ChangeImpact.LOW
    
    @property
    def is_significant(self) -> bool:
        """Whether this change is significant enough to report."""
        return self.impact in (ChangeImpact.CRITICAL, ChangeImpact.HIGH)


@dataclass
class DriftReport:
    """Summary of detected drift across repositories."""
    
    generated_at: datetime
    since: datetime | None
    repos_checked: list[Path]
    changes: list[Change] = field(default_factory=list)
    
    @property
    def critical_count(self) -> int:
        return sum(1 for c in self.changes if c.impact == ChangeImpact.CRITICAL)
    
    @property
    def high_count(self) -> int:
        return sum(1 for c in self.changes if c.impact == ChangeImpact.HIGH)
    
    @property
    def has_significant_drift(self) -> bool:
        return self.critical_count > 0 or self.high_count > 0
    
    def to_markdown(self) -> str:
        """Render report as markdown."""
        lines = [
            "# Drift Report",
            "",
            f"**Generated**: {self.generated_at.isoformat()}",
        ]
        
        if self.since:
            lines.append(f"**Since**: {self.since.isoformat()}")
        
        lines.extend([
            f"**Repositories**: {len(self.repos_checked)}",
            f"**Changes**: {len(self.changes)}",
            "",
            "## Summary",
            "",
            f"| Impact | Count |",
            f"|--------|-------|",
            f"| Critical | {self.critical_count} |",
            f"| High | {self.high_count} |",
            f"| Medium | {sum(1 for c in self.changes if c.impact == ChangeImpact.MEDIUM)} |",
            f"| Low | {sum(1 for c in self.changes if c.impact == ChangeImpact.LOW)} |",
        ])
        
        if self.changes:
            lines.extend([
                "",
                "## Changes",
                "",
            ])
            
            # Group by repo
            by_repo: dict[Path, list[Change]] = {}
            for change in self.changes:
                by_repo.setdefault(change.repo, []).append(change)
            
            for repo, changes in by_repo.items():
                lines.append(f"### {repo.name}")
                lines.append("")
                for change in sorted(changes, key=lambda c: c.commit_date, reverse=True):
                    impact_icon = {
                        ChangeImpact.CRITICAL: "🔴",
                        ChangeImpact.HIGH: "🟠",
                        ChangeImpact.MEDIUM: "🟡",
                        ChangeImpact.LOW: "🟢",
                    }.get(change.impact, "⚪")
                    lines.append(
                        f"- {impact_icon} `{change.file_path}` - {change.message[:50]}"
                    )
                lines.append("")
        
        return "\n".join(lines)


class ChangeDetector(Protocol):
    """Protocol for change detection implementations."""
    
    def detect_changes(
        self,
        since: datetime | str | None = None,
        paths: list[str] | None = None,
    ) -> list[Change]:
        """Detect changes in the repository.
        
        Args:
            since: Only include changes after this date
            paths: Optional glob patterns to filter files
            
        Returns:
            List of detected changes
        """
        ...
    
    def classify_impact(self, change: Change) -> ChangeImpact:
        """Classify the impact level of a change.
        
        Args:
            change: The change to classify
            
        Returns:
            Impact level
        """
        ...


class GitChangeDetector:
    """Git-based change detector."""
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self._alignment_patterns = [
            "*/treatments/*",
            "*/bolus/*",
            "*/basal/*",
            "*/glucose/*",
            "*/cgm/*",
            "*/pump/*",
            "**/models/**",
            "**/types/**",
        ]
    
    def detect_changes(
        self,
        since: datetime | str | None = None,
        paths: list[str] | None = None,
    ) -> list[Change]:
        """Detect changes using git log.
        
        Args:
            since: Only include changes after this date (ISO format or datetime)
            paths: Optional glob patterns to filter files
            
        Returns:
            List of detected changes
        """
        commits = self._parse_git_log(since)
        
        changes = []
        for commit in commits:
            for file_change in commit.get("files", []):
                change = Change(
                    repo=self.repo_path,
                    file_path=Path(file_change["path"]),
                    commit_hash=commit["hash"],
                    commit_date=commit["date"],
                    author=commit["author"],
                    message=commit["message"],
                    change_type=file_change["type"],
                    lines_added=file_change.get("added", 0),
                    lines_deleted=file_change.get("deleted", 0),
                )
                change.impact = self.classify_impact(change)
                
                # Filter by paths if specified
                if paths:
                    if not self._matches_patterns(change.file_path, paths):
                        continue
                
                changes.append(change)
        
        return changes
    
    def _parse_git_log(
        self,
        since: datetime | str | None = None,
    ) -> list[dict]:
        """Parse git log output into structured data.
        
        Args:
            since: Only include commits after this date
            
        Returns:
            List of commit dicts with hash, date, author, message, files
        """
        import subprocess
        
        cmd = [
            "git", "-C", str(self.repo_path),
            "log",
            "--pretty=format:%H|%aI|%an|%s",
            "--name-status",
        ]
        
        if since:
            if isinstance(since, datetime):
                since_str = since.strftime("%Y-%m-%d")
            else:
                since_str = since
            cmd.extend(["--since", since_str])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode != 0:
                return []
            
            return self._parse_log_output(result.stdout)
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []
    
    def _parse_log_output(self, output: str) -> list[dict]:
        """Parse git log output into commit dicts."""
        commits = []
        current_commit = None
        
        for line in output.strip().split("\n"):
            if not line:
                continue
            
            # Check if this is a commit header line (hash|date|author|message)
            if "|" in line and len(line.split("|")) >= 4:
                if current_commit:
                    commits.append(current_commit)
                
                parts = line.split("|", 3)
                current_commit = {
                    "hash": parts[0],
                    "date": datetime.fromisoformat(parts[1]),
                    "author": parts[2],
                    "message": parts[3] if len(parts) > 3 else "",
                    "files": [],
                }
            elif current_commit and line[0] in "AMDRT":
                # File status line: A/M/D/R followed by file path
                parts = line.split("\t")
                if len(parts) >= 2:
                    change_type_map = {
                        "A": "added",
                        "M": "modified",
                        "D": "deleted",
                        "R": "renamed",
                        "T": "type_changed",
                    }
                    current_commit["files"].append({
                        "type": change_type_map.get(parts[0][0], "unknown"),
                        "path": parts[-1],  # Use last part for renamed files
                        "added": 0,
                        "deleted": 0,
                    })
        
        if current_commit:
            commits.append(current_commit)
        
        return commits
    
    def classify_impact(self, change: Change) -> ChangeImpact:
        """Classify change impact based on file path and change type."""
        path_str = str(change.file_path).lower()
        
        # Critical: Core model/type changes
        if any(x in path_str for x in ["model", "type", "schema", "protocol"]):
            if change.change_type in ("deleted", "renamed"):
                return ChangeImpact.CRITICAL
            return ChangeImpact.HIGH
        
        # High: Treatment/therapy related
        if any(x in path_str for x in ["treatment", "bolus", "basal", "dose"]):
            return ChangeImpact.HIGH
        
        # Medium: Data/glucose related
        if any(x in path_str for x in ["glucose", "cgm", "reading", "entry"]):
            return ChangeImpact.MEDIUM
        
        # Low: Everything else
        return ChangeImpact.LOW
    
    def _matches_patterns(self, path: Path, patterns: list[str]) -> bool:
        """Check if path matches any of the glob patterns."""
        import fnmatch
        
        path_str = str(path)
        return any(fnmatch.fnmatch(path_str, p) for p in patterns)


__all__ = [
    "ChangeImpact",
    "Change",
    "DriftReport",
    "ChangeDetector",
    "GitChangeDetector",
]
