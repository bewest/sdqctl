"""
Logging configuration for sdqctl.

Provides centralized logging setup with verbosity levels:
- 0 (default): WARNING - errors and warnings only
- 1 (-v):      INFO - key operations
- 2 (-vv):     DEBUG - detailed tracing
- 3+ (-vvv):   TRACE - everything including external libs
"""

import logging
import sys
from typing import Optional

# Custom TRACE level (more verbose than DEBUG)
TRACE = 5
logging.addLevelName(TRACE, "TRACE")


def trace(self, message, *args, **kwargs):
    """Log at TRACE level."""
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kwargs)


# Add trace method to Logger class
logging.Logger.trace = trace


def setup_logging(verbosity: int = 0, quiet: bool = False) -> logging.Logger:
    """Configure logging based on verbosity level.
    
    Args:
        verbosity: Number of -v flags (0=WARNING, 1=INFO, 2=DEBUG, 3+=TRACE)
        quiet: If True, suppress all output except errors
        
    Returns:
        The configured root logger for sdqctl
    """
    # Determine log level
    if quiet:
        level = logging.ERROR
    elif verbosity == 0:
        level = logging.WARNING
    elif verbosity == 1:
        level = logging.INFO
    elif verbosity == 2:
        level = logging.DEBUG
    else:  # verbosity >= 3
        level = TRACE
    
    # Get our logger
    logger = logging.getLogger("sdqctl")
    logger.setLevel(level)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create console handler with formatting
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)
    
    # Format based on verbosity
    if verbosity >= 2:
        # Detailed format for debug/trace
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        datefmt = "%H:%M:%S"
    elif verbosity == 1:
        # Simple format for info
        fmt = "[%(levelname)s] %(message)s"
        datefmt = None
    else:
        # Minimal format for warnings
        fmt = "%(message)s"
        datefmt = None
    
    formatter = logging.Formatter(fmt, datefmt=datefmt)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # At TRACE level, also enable debug for external libs
    if verbosity >= 3:
        logging.getLogger().setLevel(logging.DEBUG)
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger for a module.
    
    Args:
        name: Module name (e.g., "sdqctl.commands.run"). 
              If None, returns the root sdqctl logger.
              
    Returns:
        Logger instance
    """
    if name is None:
        return logging.getLogger("sdqctl")
    return logging.getLogger(name)
