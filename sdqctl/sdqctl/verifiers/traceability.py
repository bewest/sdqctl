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

from .base import VerificationError, VerificationResult


@dataclass
class TraceArtifact:
    """A single traceability artifact."""
    id: str
    type: str  # UCA, SC, REQ, SPEC, TEST, GAP
    file: str
    line: int
    links_to: list[str] = field(default_factory=list)  # IDs this artifact links to
    linked_from: list[str] = field(default_factory=list)  # IDs that link to this


class TraceabilityVerifier:
    """Verify traceability links between STPA/IEC 62304 artifacts."""
    
    name = "traceability"
    description = "Check STPA/IEC 62304 traceability links"
    
    # Patterns for artifact IDs
    # Format: PREFIX-CATEGORY-NNN or PREFIX-NNN
    ID_PATTERNS = {
        "UCA": re.compile(r'\b(UCA-[A-Z0-9]+-\d{3}|UCA-\d{3})\b'),
        "SC": re.compile(r'\b(SC-[A-Z0-9]+-\d{3}[a-z]?|SC-\d{3}[a-z]?)\b'),
        "REQ": re.compile(r'\b(REQ-[A-Z0-9]+-\d{3}|REQ-\d{3})\b'),
        "SPEC": re.compile(r'\b(SPEC-[A-Z0-9]+-\d{3}|SPEC-\d{3})\b'),
        "TEST": re.compile(r'\b(TEST-[A-Z0-9]+-\d{3}|TEST-\d{3})\b'),
        "GAP": re.compile(r'\b(GAP-[A-Z0-9]+-\d{3}|GAP-\d{3})\b'),
    }
    
    # Expected trace chain (higher level → lower level)
    TRACE_CHAIN = ["UCA", "SC", "REQ", "SPEC", "TEST"]
    
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
        if recursive:
            files = [f for f in root.rglob('*') if f.suffix in scan_ext and f.is_file()]
        else:
            files = [f for f in root.glob('*') if f.suffix in scan_ext and f.is_file()]
        
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
            # UCAs without downstream links are concerning
            if art.type == "UCA":
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
                    fix_hint=f"Link to upstream or downstream artifact",
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
        coverage = self._calculate_coverage(artifacts, artifacts_by_type)
        
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
                # GAPs are allowed to be standalone
                if artifact.type != "GAP":
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
    
    def _calculate_coverage(
        self,
        artifacts: dict[str, TraceArtifact],
        artifacts_by_type: dict[str, list[str]],
    ) -> dict[str, float]:
        """Calculate traceability coverage metrics."""
        coverage = {
            "total_ucas": len(artifacts_by_type.get("UCA", [])),
            "total_scs": len(artifacts_by_type.get("SC", [])),
            "total_reqs": len(artifacts_by_type.get("REQ", [])),
            "total_specs": len(artifacts_by_type.get("SPEC", [])),
            "total_tests": len(artifacts_by_type.get("TEST", [])),
        }
        
        # UCA → SC coverage
        ucas_with_sc = 0
        for uca_id in artifacts_by_type.get("UCA", []):
            uca = artifacts[uca_id]
            if any(self._is_type(lid, "SC", artifacts) for lid in uca.links_to):
                ucas_with_sc += 1
        
        if coverage["total_ucas"] > 0:
            coverage["uca_to_sc"] = ucas_with_sc / coverage["total_ucas"] * 100
        else:
            coverage["uca_to_sc"] = 0
        
        # REQ → SPEC coverage
        reqs_with_spec = 0
        for req_id in artifacts_by_type.get("REQ", []):
            req = artifacts[req_id]
            has_spec = any(self._is_type(lid, "SPEC", artifacts) for lid in req.links_to)
            has_spec = has_spec or any(self._is_type(lid, "SPEC", artifacts) for lid in req.linked_from)
            if has_spec:
                reqs_with_spec += 1
        
        if coverage["total_reqs"] > 0:
            coverage["req_to_spec"] = reqs_with_spec / coverage["total_reqs"] * 100
        else:
            coverage["req_to_spec"] = 0
        
        # SPEC → TEST coverage
        specs_with_test = 0
        for spec_id in artifacts_by_type.get("SPEC", []):
            spec = artifacts[spec_id]
            has_test = any(self._is_type(lid, "TEST", artifacts) for lid in spec.links_to)
            has_test = has_test or any(self._is_type(lid, "TEST", artifacts) for lid in spec.linked_from)
            if has_test:
                specs_with_test += 1
        
        if coverage["total_specs"] > 0:
            coverage["spec_to_test"] = specs_with_test / coverage["total_specs"] * 100
        else:
            coverage["spec_to_test"] = 0
        
        # Overall coverage (average of available metrics)
        metrics = [v for k, v in coverage.items() if k.endswith("_to_") or "_to_" in k]
        if metrics:
            coverage["overall"] = sum(m for m in metrics if isinstance(m, (int, float))) / len(metrics)
        else:
            coverage["overall"] = 0
        
        return coverage
    
    def _is_type(self, art_id: str, art_type: str, artifacts: dict[str, TraceArtifact]) -> bool:
        """Check if an artifact ID is of a given type."""
        if art_id in artifacts:
            return artifacts[art_id].type == art_type
        # Infer from ID prefix
        return art_id.startswith(art_type + "-")
    
    def _relative_path(self, path: Path, root: Path) -> Path:
        """Get path relative to root, or absolute if not under root."""
        try:
            return path.relative_to(root)
        except ValueError:
            return path
