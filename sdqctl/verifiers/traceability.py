"""
Traceability verification - check STPA/IEC 62304 trace links.

Scans markdown files for traceability IDs (UCA, REQ, SPEC, TEST) and
verifies that artifacts are properly linked.
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .base import VerificationError, VerificationResult, scan_files
from .traceability_coverage import calculate_coverage


@dataclass
class TraceArtifact:
    """A single traceability artifact."""
    id: str
    type: str  # UCA, SC, REQ, SPEC, TEST, GAP, LOSS, HAZ, BUG, PROP, Q, IQ
    file: str
    line: int
    links_to: list[str] = field(default_factory=list)  # IDs this artifact links to
    linked_from: list[str] = field(default_factory=list)  # IDs that link to this


class TraceabilityVerifier:
    """Verify traceability links between STPA/IEC 62304 artifacts."""

    name = "traceability"
    description = "Check STPA/IEC 62304 traceability links"

    # Patterns for artifact IDs (from ARTIFACT-TAXONOMY.md)
    # Format: PREFIX-CATEGORY-NNN or PREFIX-NNN
    ID_PATTERNS = {
        # STPA safety artifacts
        "LOSS": re.compile(r'\b(LOSS-\d{3})\b'),
        "HAZ": re.compile(r'\b(HAZ-\d{3})\b'),
        "UCA": re.compile(r'\b(UCA-[A-Z0-9]+-\d{3}|UCA-\d{3})\b'),
        "SC": re.compile(r'\b(SC-[A-Z0-9]+-\d{3}[a-z]?|SC-\d{3}[a-z]?)\b'),
        # Requirements/specifications
        "REQ": re.compile(r'\b(REQ-[A-Z0-9]+-\d{3}|REQ-\d{3})\b'),
        "SPEC": re.compile(r'\b(SPEC-[A-Z0-9]+-\d{3}|SPEC-\d{3})\b'),
        "TEST": re.compile(r'\b(TEST-[A-Z0-9]+-\d{3}|TEST-\d{3})\b'),
        "GAP": re.compile(r'\b(GAP-[A-Z0-9]+-\d{3}|GAP-\d{3})\b'),
        # Development artifacts
        "BUG": re.compile(r'\b(BUG-\d{3})\b'),
        "PROP": re.compile(r'\b(PROP-\d{3})\b'),
        "Q": re.compile(r'\b(Q-\d{3})\b'),
        "IQ": re.compile(r'\b(IQ-\d+)\b'),
    }

    # Expected trace chain (higher level → lower level)
    # STPA: LOSS → HAZ → UCA → SC → REQ
    # IEC 62304: REQ → SPEC → TEST
    TRACE_CHAIN = ["LOSS", "HAZ", "UCA", "SC", "REQ", "SPEC", "TEST"]

    # Standalone artifact types (allowed to have no links)
    STANDALONE_TYPES = {"GAP", "BUG", "PROP", "Q", "IQ"}

    # File extensions to scan
    SCAN_EXTENSIONS = {'.md', '.markdown', '.yaml', '.yml', '.txt', '.conv'}

    def verify(
        self,
        root: Path,
        recursive: bool = True,
        extensions: set[str] | None = None,
        require_chain: bool = False,
        **options: Any
    ) -> VerificationResult:
        """Verify traceability links in documentation.

        Args:
            root: Directory to scan
            recursive: Whether to scan subdirectories
            extensions: File extensions to scan
            require_chain: If True, require complete trace chains

        Returns:
            VerificationResult with trace coverage metrics and orphan detection
        """
        root = Path(root)
        scan_ext = extensions or self.SCAN_EXTENSIONS

        errors: list[VerificationError] = []
        warnings: list[VerificationError] = []

        # Collect all artifacts
        artifacts: dict[str, TraceArtifact] = {}
        artifacts_by_type: dict[str, list[str]] = defaultdict(list)

        # Stats
        files_scanned = 0

        # Find files to scan
        files = scan_files(root, scan_ext, recursive=recursive)

        for filepath in files:
            files_scanned += 1
            try:
                content = filepath.read_text(errors='replace')
            except Exception as e:
                warnings.append(VerificationError(
                    file=str(self._relative_path(filepath, root)),
                    line=None,
                    message=f"Could not read file: {e}",
                ))
                continue

            # Extract artifacts from file
            self._extract_artifacts(
                content,
                str(self._relative_path(filepath, root)),
                artifacts,
                artifacts_by_type
            )

        # Build link graph
        self._build_link_graph(artifacts)

        # Check for orphans (artifacts not linked to anything)
        orphan_artifacts = self._find_orphans(artifacts, artifacts_by_type)
        for orphan in orphan_artifacts:
            art = artifacts[orphan]
            # LOSS without HAZ is concerning (top of STPA chain)
            if art.type == "LOSS":
                errors.append(VerificationError(
                    file=art.file,
                    line=art.line,
                    message=f"Orphan LOSS: {art.id} has no downstream HAZ links",
                    fix_hint="Add Hazard (HAZ) that leads to this loss",
                ))
            # HAZ without UCA is concerning
            elif art.type == "HAZ":
                errors.append(VerificationError(
                    file=art.file,
                    line=art.line,
                    message=f"Orphan HAZ: {art.id} has no links",
                    fix_hint="Add UCA that causes this hazard or link to LOSS",
                ))
            # UCAs without downstream links are concerning
            elif art.type == "UCA":
                errors.append(VerificationError(
                    file=art.file,
                    line=art.line,
                    message=f"Orphan UCA: {art.id} has no downstream links",
                    fix_hint="Add Safety Constraint (SC) or link to GAP",
                ))
            elif art.type in ("SC", "REQ", "SPEC"):
                warnings.append(VerificationError(
                    file=art.file,
                    line=art.line,
                    message=f"Orphan {art.type}: {art.id} has no links",
                    fix_hint="Link to upstream or downstream artifact",
                ))

        # Check for broken links (references to non-existent IDs)
        broken_links = self._find_broken_links(artifacts)
        for ref_id, locations in broken_links.items():
            for loc_file, loc_line in locations:
                errors.append(VerificationError(
                    file=loc_file,
                    line=loc_line,
                    message=f"Broken reference: {ref_id} not defined",
                    fix_hint=f"Create artifact {ref_id} or fix the reference",
                ))

        # Calculate coverage metrics
        coverage = calculate_coverage(artifacts, artifacts_by_type)

        # Build result
        total_artifacts = len(artifacts)
        orphan_count = len(orphan_artifacts)
        broken_count = len(broken_links)

        passed = len(errors) == 0
        summary = (
            f"Scanned {files_scanned} file(s), found {total_artifacts} artifact(s): "
            f"{orphan_count} orphan(s), {broken_count} broken link(s)"
        )

        # Add coverage to summary if we have artifacts
        if coverage.get("uca_to_sc", 0) > 0 or coverage.get("total_ucas", 0) > 0:
            coverage_pct = coverage.get("overall", 0)
            summary += f", {coverage_pct:.0f}% trace coverage"

        return VerificationResult(
            passed=passed,
            errors=errors,
            warnings=warnings,
            summary=summary,
            details={
                "files_scanned": files_scanned,
                "total_artifacts": total_artifacts,
                "artifacts_by_type": dict(artifacts_by_type),
                "orphan_count": orphan_count,
                "broken_links": broken_count,
                "coverage": coverage,
            },
        )

    def _extract_artifacts(
        self,
        content: str,
        filepath: str,
        artifacts: dict[str, TraceArtifact],
        artifacts_by_type: dict[str, list[str]],
    ) -> None:
        """Extract artifact IDs from file content."""
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            for art_type, pattern in self.ID_PATTERNS.items():
                for match in pattern.finditer(line):
                    art_id = match.group(1)

                    # Check if this is a definition (first occurrence) or reference
                    if art_id not in artifacts:
                        # First occurrence - treat as definition
                        artifacts[art_id] = TraceArtifact(
                            id=art_id,
                            type=art_type,
                            file=filepath,
                            line=line_num,
                        )
                        artifacts_by_type[art_type].append(art_id)

                    # Check for links on this line
                    # Pattern: "ID → other-ID" or "ID -> other-ID" or "links: ID, ID"
                    self._extract_links_from_line(line, art_id, artifacts)

    def _extract_links_from_line(
        self,
        line: str,
        source_id: str,
        artifacts: dict[str, TraceArtifact],
    ) -> None:
        """Extract links from a line containing an artifact ID."""
        # Find all IDs on this line
        all_ids = set()
        for pattern in self.ID_PATTERNS.values():
            for match in pattern.finditer(line):
                all_ids.add(match.group(1))

        # If multiple IDs on same line, they might be linked
        if len(all_ids) > 1 and source_id in all_ids:
            other_ids = all_ids - {source_id}

            # Check for explicit link indicators
            has_arrow = '→' in line or '->' in line
            has_link_keyword = any(kw in line.lower() for kw in
                                   ['links', 'traces', 'implements', 'satisfies', 'derived'])

            if has_arrow or has_link_keyword:
                if source_id in artifacts:
                    artifacts[source_id].links_to.extend(other_ids)

    def _build_link_graph(self, artifacts: dict[str, TraceArtifact]) -> None:
        """Build bidirectional link graph."""
        for art_id, artifact in artifacts.items():
            for linked_id in artifact.links_to:
                if linked_id in artifacts:
                    artifacts[linked_id].linked_from.append(art_id)

    def _find_orphans(
        self,
        artifacts: dict[str, TraceArtifact],
        artifacts_by_type: dict[str, list[str]],
    ) -> list[str]:
        """Find artifacts with no links in either direction."""
        orphans = []
        for art_id, artifact in artifacts.items():
            if not artifact.links_to and not artifact.linked_from:
                # Standalone types are allowed to have no links
                if artifact.type not in self.STANDALONE_TYPES:
                    orphans.append(art_id)
        return orphans

    def _find_broken_links(
        self,
        artifacts: dict[str, TraceArtifact],
    ) -> dict[str, list[tuple[str, int]]]:
        """Find references to non-existent artifact IDs."""
        broken: dict[str, list[tuple[str, int]]] = defaultdict(list)

        for art_id, artifact in artifacts.items():
            for linked_id in artifact.links_to:
                if linked_id not in artifacts:
                    broken[linked_id].append((artifact.file, artifact.line))

        return broken

    def _relative_path(self, path: Path, root: Path) -> Path:
        """Get path relative to root, or absolute if not under root."""
        try:
            return path.relative_to(root)
        except ValueError:
            return path

    def verify_trace(
        self,
        from_id: str,
        to_id: str,
        root: Path,
        recursive: bool = True,
        **options: Any
    ) -> VerificationResult:
        """Verify that a specific trace link exists between two artifacts.

        A trace link exists if:
        1. Both artifacts are defined in the documentation
        2. There is a direct link from from_id to to_id, OR
        3. There is a path through the trace chain from from_id to to_id

        Args:
            from_id: Source artifact ID (e.g., "UCA-001")
            to_id: Target artifact ID (e.g., "REQ-020")
            root: Directory to scan for artifacts
            recursive: Whether to scan subdirectories

        Returns:
            VerificationResult with pass/fail and details
        """
        root = Path(root)

        errors: list[VerificationError] = []
        warnings: list[VerificationError] = []

        # First, collect all artifacts
        artifacts: dict[str, TraceArtifact] = {}
        artifacts_by_type: dict[str, list[str]] = defaultdict(list)
        files_scanned = 0

        # Find files to scan
        files = scan_files(root, self.SCAN_EXTENSIONS, recursive=recursive)

        for filepath in files:
            files_scanned += 1
            try:
                content = filepath.read_text(errors='replace')
            except Exception:
                continue

            self._extract_artifacts(
                content,
                str(self._relative_path(filepath, root)),
                artifacts,
                artifacts_by_type
            )

        # Build link graph
        self._build_link_graph(artifacts)

        # Check if both artifacts exist
        if from_id not in artifacts:
            errors.append(VerificationError(
                file=None,
                line=None,
                message=f"Source artifact not found: {from_id}",
                fix_hint=f"Define {from_id} in documentation",
            ))

        if to_id not in artifacts:
            errors.append(VerificationError(
                file=None,
                line=None,
                message=f"Target artifact not found: {to_id}",
                fix_hint=f"Define {to_id} in documentation",
            ))

        if errors:
            return VerificationResult(
                passed=False,
                errors=errors,
                warnings=warnings,
                summary=f"VERIFY-TRACE {from_id} -> {to_id}: artifacts not found",
                details={"from": from_id, "to": to_id, "linked": False},
            )

        # Check for direct link
        from_artifact = artifacts[from_id]
        if to_id in from_artifact.links_to or to_id in from_artifact.linked_from:
            return VerificationResult(
                passed=True,
                errors=[],
                warnings=[],
                summary=f"VERIFY-TRACE {from_id} -> {to_id}: linked ✓",
                details={"from": from_id, "to": to_id, "linked": True, "direct": True},
            )

        # Check for indirect link (BFS through trace chain)
        visited = set()
        queue = [from_id]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            if current == to_id:
                return VerificationResult(
                    passed=True,
                    errors=[],
                    warnings=[],
                    summary=f"VERIFY-TRACE {from_id} -> {to_id}: linked (indirect) ✓",
                    details={"from": from_id, "to": to_id, "linked": True, "direct": False},
                )

            if current in artifacts:
                queue.extend(artifacts[current].links_to)

        # No link found
        errors.append(VerificationError(
            file=from_artifact.file,
            line=from_artifact.line,
            message=f"No trace link found: {from_id} -> {to_id}",
            fix_hint=f"Add link from {from_id} to {to_id} in documentation",
        ))

        return VerificationResult(
            passed=False,
            errors=errors,
            warnings=warnings,
            summary=f"VERIFY-TRACE {from_id} -> {to_id}: NOT linked",
            details={"from": from_id, "to": to_id, "linked": False},
        )

    def verify_coverage(
        self,
        root: Path,
        metric: str | None = None,
        op: str | None = None,
        threshold: float | None = None,
        recursive: bool = True,
        **options: Any
    ) -> VerificationResult:
        """Verify traceability coverage meets a threshold.

        If no metric/threshold specified, returns a coverage report.
        If metric and threshold specified, checks if the metric meets the threshold.

        Args:
            root: Directory to scan for artifacts
            metric: Coverage metric name (e.g., "uca_to_sc", "overall")
            op: Comparison operator (>=, <=, >, <, ==)
            threshold: Threshold percentage (0-100)
            recursive: Whether to scan subdirectories

        Returns:
            VerificationResult with coverage data
        """
        root = Path(root)

        errors: list[VerificationError] = []
        warnings: list[VerificationError] = []

        # First, collect all artifacts
        artifacts: dict[str, TraceArtifact] = {}
        artifacts_by_type: dict[str, list[str]] = defaultdict(list)
        files_scanned = 0

        # Find files to scan
        files = scan_files(root, self.SCAN_EXTENSIONS, recursive=recursive)

        for filepath in files:
            files_scanned += 1
            try:
                content = filepath.read_text(errors='replace')
            except Exception:
                continue

            self._extract_artifacts(
                content,
                str(self._relative_path(filepath, root)),
                artifacts,
                artifacts_by_type
            )

        # Build link graph
        self._build_link_graph(artifacts)

        # Calculate coverage
        coverage = calculate_coverage(artifacts, artifacts_by_type)

        # Valid metric names
        valid_metrics = {
            "loss_to_haz", "haz_to_uca", "uca_to_sc",
            "req_to_spec", "spec_to_test", "overall"
        }

        # If no threshold check, just return coverage report
        if metric is None or threshold is None:
            summary_parts = []
            for key in ["uca_to_sc", "req_to_spec", "spec_to_test", "overall"]:
                if key in coverage:
                    summary_parts.append(f"{key}: {coverage[key]:.1f}%")

            return VerificationResult(
                passed=True,
                errors=[],
                warnings=[],
                summary=f"Coverage: {', '.join(summary_parts)}",
                details={"coverage": coverage, "files_scanned": files_scanned},
            )

        # Validate metric name
        if metric not in valid_metrics:
            errors.append(VerificationError(
                file=None,
                line=None,
                message=f"Unknown coverage metric: {metric}",
                fix_hint=f"Valid metrics: {', '.join(sorted(valid_metrics))}",
            ))
            return VerificationResult(
                passed=False,
                errors=errors,
                warnings=warnings,
                summary=f"VERIFY-COVERAGE: invalid metric '{metric}'",
                details={"coverage": coverage, "metric": metric},
            )

        # Get the metric value
        actual = coverage.get(metric, 0)

        # Compare against threshold
        comparison_ops = {
            ">=": lambda a, t: a >= t,
            "<=": lambda a, t: a <= t,
            ">": lambda a, t: a > t,
            "<": lambda a, t: a < t,
            "==": lambda a, t: abs(a - t) < 0.01,
        }

        compare_fn = comparison_ops.get(op, lambda a, t: a >= t)
        passed = compare_fn(actual, threshold)

        if passed:
            return VerificationResult(
                passed=True,
                errors=[],
                warnings=[],
                summary=f"VERIFY-COVERAGE {metric} {op} {threshold}%: PASS ({actual:.1f}%)",
                details={
                    "coverage": coverage, "metric": metric,
                    "actual": actual, "threshold": threshold
                },
            )
        else:
            errors.append(VerificationError(
                file=None,
                line=None,
                message=(
                    f"Coverage check failed: {metric} = {actual:.1f}% "
                    f"(expected {op} {threshold}%)"
                ),
                fix_hint="Improve traceability by adding links between artifacts",
            ))
            return VerificationResult(
                passed=False,
                errors=errors,
                warnings=warnings,
                summary=f"VERIFY-COVERAGE {metric} {op} {threshold}%: FAIL ({actual:.1f}%)",
                details={
                    "coverage": coverage, "metric": metric,
                    "actual": actual, "threshold": threshold
                },
            )
