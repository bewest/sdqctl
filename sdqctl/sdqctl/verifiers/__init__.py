"""
Verification subsystem for sdqctl.

Provides tools for checking code references, links, terminology,
traceability, and assertions.
"""

from .base import VerificationError, VerificationResult, Verifier
from .refs import RefsVerifier

# Registry of available verifiers
VERIFIERS: dict[str, type] = {
    "refs": RefsVerifier,
}

__all__ = [
    "VerificationError",
    "VerificationResult", 
    "Verifier",
    "RefsVerifier",
    "VERIFIERS",
]
