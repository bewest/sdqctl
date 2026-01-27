"""
sdqctl - Software Defined Quality Control

Vendor-agnostic CLI for orchestrating AI-assisted development workflows
with reproducible context management and declarative workflow definitions.
"""

__version__ = "0.1.0"
__author__ = "Ben West"

from .core.conversation import ConversationFile
from .core.session import Session

__all__ = ["ConversationFile", "Session", "__version__"]
