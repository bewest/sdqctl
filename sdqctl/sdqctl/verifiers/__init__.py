"""
Verification subsystem for sdqctl.

Provides tools for checking code references, links, terminology,
traceability, and assertions.
"""

from .assertions import AssertionsVerifier
from .base import VerificationError, VerificationResult, Verifier, scan_files
from .links import LinksVerifier
from .refs import RefsVerifier
from .terminology import TerminologyVerifier
from .traceability import TraceabilityVerifier

# Registry of available verifiers
VERIFIERS: dict[str, type] = {
    "refs": RefsVerifier,
    "links": LinksVerifier,
    "traceability": TraceabilityVerifier,
    "terminology": TerminologyVerifier,
    "assertions": AssertionsVerifier,
}

__all__ = [
    "VerificationError",
    "VerificationResult",
    "Verifier",
    "scan_files",
    "RefsVerifier",
    "LinksVerifier",
    "TraceabilityVerifier",
    "TerminologyVerifier",
    "AssertionsVerifier",
    "VERIFIERS",
]
