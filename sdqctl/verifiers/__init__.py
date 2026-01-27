"""
Verification subsystem for sdqctl.

Provides tools for checking code references, links, terminology,
traceability, and assertions. Supports plugin verifiers via
.sdqctl/directives.yaml manifests.
"""

from .assertions import AssertionsVerifier
from .base import VerificationError, VerificationResult, Verifier, scan_files
from .links import LinksVerifier
from .refs import RefsVerifier
from .terminology import TerminologyVerifier
from .traceability import TraceabilityVerifier

# Registry of available verifiers (built-in)
VERIFIERS: dict[str, type] = {
    "refs": RefsVerifier,
    "links": LinksVerifier,
    "traceability": TraceabilityVerifier,
    "terminology": TerminologyVerifier,
    "assertions": AssertionsVerifier,
}


def _register_plugins() -> None:
    """Register plugin verifiers from .sdqctl/directives.yaml manifests."""
    try:
        from ..plugins import register_plugins
        register_plugins(VERIFIERS)
    except Exception:
        # Plugin loading errors should not break core functionality
        pass


# Register plugins at import time
_register_plugins()

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
