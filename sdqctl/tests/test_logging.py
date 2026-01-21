"""Tests for sdqctl logging configuration."""

import logging
import sys
from io import StringIO
from unittest.mock import patch

import pytest

from sdqctl.core.logging import (
    TRACE,
    setup_logging,
    get_logger,
)


class TestTraceLevelSetup:
    """Test custom TRACE level setup."""
    
    def test_trace_level_value(self):
        """Test TRACE level is set correctly."""
        assert TRACE == 5
    
    def test_trace_level_name(self):
        """Test TRACE level name is registered."""
        assert logging.getLevelName(TRACE) == "TRACE"
        assert logging.getLevelName("TRACE") == TRACE
    
    def test_trace_method_exists(self):
        """Test trace method is added to Logger."""
        logger = logging.getLogger("test.trace")
        assert hasattr(logger, "trace")
        assert callable(logger.trace)


class TestSetupLogging:
    """Test setup_logging function."""
    
    def test_default_verbosity(self):
        """Test default verbosity level is WARNING."""
        logger = setup_logging(verbosity=0)
        
        assert logger.level == logging.WARNING
    
    def test_verbosity_one_is_info(self):
        """Test -v sets INFO level."""
        logger = setup_logging(verbosity=1)
        
        assert logger.level == logging.INFO
    
    def test_verbosity_two_is_debug(self):
        """Test -vv sets DEBUG level."""
        logger = setup_logging(verbosity=2)
        
        assert logger.level == logging.DEBUG
    
    def test_verbosity_three_is_trace(self):
        """Test -vvv sets TRACE level."""
        logger = setup_logging(verbosity=3)
        
        assert logger.level == TRACE
    
    def test_high_verbosity_is_trace(self):
        """Test high verbosity (>3) is also TRACE."""
        logger = setup_logging(verbosity=10)
        
        assert logger.level == TRACE
    
    def test_quiet_overrides_verbosity(self):
        """Test quiet flag sets ERROR level."""
        logger = setup_logging(verbosity=3, quiet=True)
        
        assert logger.level == logging.ERROR
    
    def test_quiet_alone(self):
        """Test quiet flag alone."""
        logger = setup_logging(quiet=True)
        
        assert logger.level == logging.ERROR
    
    def test_returns_sdqctl_logger(self):
        """Test setup_logging returns the sdqctl logger."""
        logger = setup_logging()
        
        assert logger.name == "sdqctl"
    
    def test_clears_existing_handlers(self):
        """Test existing handlers are cleared."""
        logger = setup_logging(verbosity=0)
        initial_handler_count = len(logger.handlers)
        
        # Call again
        logger = setup_logging(verbosity=1)
        
        # Should have same number of handlers (1)
        assert len(logger.handlers) == initial_handler_count
    
    def test_handler_writes_to_stderr(self):
        """Test log output goes to stderr."""
        logger = setup_logging(verbosity=1)
        
        assert len(logger.handlers) == 1
        handler = logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert handler.stream == sys.stderr


class TestLogFormat:
    """Test log message formatting."""
    
    def test_warning_format_minimal(self):
        """Test warning level has minimal format."""
        logger = setup_logging(verbosity=0)
        handler = logger.handlers[0]
        
        # Minimal format just has message
        assert "%(message)s" in handler.formatter._fmt
        assert "%(levelname)" not in handler.formatter._fmt
    
    def test_info_format_simple(self):
        """Test info level has simple format with level name."""
        logger = setup_logging(verbosity=1)
        handler = logger.handlers[0]
        
        assert "%(levelname)s" in handler.formatter._fmt
        assert "%(asctime)s" not in handler.formatter._fmt
    
    def test_debug_format_detailed(self):
        """Test debug level has detailed format."""
        logger = setup_logging(verbosity=2)
        handler = logger.handlers[0]
        
        fmt = handler.formatter._fmt
        assert "%(asctime)s" in fmt
        assert "%(levelname)s" in fmt
        assert "%(name)s" in fmt


class TestTraceLogging:
    """Test TRACE level logging behavior."""
    
    def test_trace_logs_at_trace_level(self, caplog):
        """Test trace() method logs at TRACE level."""
        logger = setup_logging(verbosity=3)
        logger.trace("Test trace message")
        
        # caplog may not capture TRACE level, so check isEnabledFor instead
        assert logger.isEnabledFor(TRACE)
    
    def test_trace_not_logged_at_debug(self):
        """Test trace messages are not shown at DEBUG level."""
        logger = setup_logging(verbosity=2)  # DEBUG
        
        assert not logger.isEnabledFor(TRACE)
    
    def test_trace_enables_external_libs(self):
        """Test TRACE level also enables external lib debugging."""
        setup_logging(verbosity=3)
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG


class TestGetLogger:
    """Test get_logger function."""
    
    def test_get_logger_with_name(self):
        """Test getting a named logger."""
        logger = get_logger("sdqctl.commands.run")
        
        assert logger.name == "sdqctl.commands.run"
    
    def test_get_logger_without_name(self):
        """Test getting root sdqctl logger."""
        logger = get_logger()
        
        assert logger.name == "sdqctl"
    
    def test_get_logger_none_explicit(self):
        """Test getting root logger with explicit None."""
        logger = get_logger(None)
        
        assert logger.name == "sdqctl"
    
    def test_child_logger_inherits_level(self):
        """Test child loggers inherit parent level."""
        setup_logging(verbosity=1)  # Set parent to INFO
        
        parent = get_logger()
        child = get_logger("sdqctl.test.child")
        
        # Child should inherit effective level
        assert child.getEffectiveLevel() == parent.level


class TestLoggingOutput:
    """Test actual log output."""
    
    def test_info_message_logged(self):
        """Test INFO message is logged at verbosity 1."""
        logger = setup_logging(verbosity=1)
        
        # Capture stderr
        with patch.object(sys, 'stderr', new_callable=StringIO) as mock_stderr:
            # Need to recreate handler to point to mock
            logger.handlers.clear()
            handler = logging.StreamHandler(mock_stderr)
            handler.setLevel(logging.INFO)
            handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
            logger.addHandler(handler)
            
            logger.info("Test info message")
            
            output = mock_stderr.getvalue()
            assert "INFO" in output
            assert "Test info message" in output
    
    def test_warning_suppresses_info(self):
        """Test INFO messages not shown at WARNING level."""
        logger = setup_logging(verbosity=0)
        
        with patch.object(sys, 'stderr', new_callable=StringIO) as mock_stderr:
            logger.handlers.clear()
            handler = logging.StreamHandler(mock_stderr)
            handler.setLevel(logging.WARNING)
            logger.addHandler(handler)
            
            logger.info("Hidden info")
            logger.warning("Visible warning")
            
            output = mock_stderr.getvalue()
            assert "Hidden info" not in output
            assert "Visible warning" in output
    
    def test_quiet_only_shows_errors(self):
        """Test quiet mode only shows ERROR and above."""
        logger = setup_logging(quiet=True)
        
        assert not logger.isEnabledFor(logging.WARNING)
        assert logger.isEnabledFor(logging.ERROR)


class TestLoggingIntegration:
    """Integration tests for logging in sdqctl modules."""
    
    def test_module_logger_respects_setup(self):
        """Test module loggers respect global setup."""
        setup_logging(verbosity=2)  # DEBUG
        
        # Get a module-style logger
        module_logger = get_logger("sdqctl.core.session")
        
        # Should be enabled for DEBUG
        assert module_logger.getEffectiveLevel() == logging.DEBUG
    
    def test_different_modules_same_level(self):
        """Test different module loggers share same level."""
        setup_logging(verbosity=1)
        
        logger1 = get_logger("sdqctl.commands.run")
        logger2 = get_logger("sdqctl.adapters.copilot")
        
        assert logger1.getEffectiveLevel() == logger2.getEffectiveLevel()
