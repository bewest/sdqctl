"""
Verification subsystem for sdqctl.

Provides tools for checking code references, links, terminology,
traceability, and assertions.
"""

from .base import VerificationError, VerificationResult, Verifier
from .refs import RefsVerifier
from .links import LinksVerifier
from .traceability import TraceabilityVerifier

# Registry of available verifiers
VERIFIERS: dict[str, type] = {
    "refs": RefsVerifier,
    "links": LinksVerifier,
    "traceability": TraceabilityVerifier,
}

__all__ = [
    "VerificationError",
    "VerificationResult", 
    "Verifier",
    "RefsVerifier",
    "LinksVerifier",
    "TraceabilityVerifier",
    "VERIFIERS",
]
