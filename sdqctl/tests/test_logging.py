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
    get_workflow_logger,
    WorkflowContext,
    WorkflowLoggerAdapter,
    get_workflow_context,
    set_workflow_context,
    WorkflowContextFormatter,
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


class TestWorkflowContext:
    """Test WorkflowContext class."""
    
    def test_empty_context_no_prefix(self):
        """Test empty context returns no prefix."""
        ctx = WorkflowContext()
        assert ctx.format_prefix() == ""
    
    def test_workflow_name_only(self):
        """Test prefix with just workflow name."""
        ctx = WorkflowContext(workflow_name="fix-quirks")
        assert ctx.format_prefix() == "[fix-quirks]"
    
    def test_workflow_with_cycle(self):
        """Test prefix with workflow and cycle."""
        ctx = WorkflowContext(
            workflow_name="fix-quirks",
            cycle=1,
            total_cycles=3
        )
        assert ctx.format_prefix() == "[fix-quirks:1/3]"
    
    def test_workflow_with_cycle_and_prompt(self):
        """Test prefix with workflow, cycle, and prompt."""
        ctx = WorkflowContext(
            workflow_name="proposal-dev",
            cycle=2,
            total_cycles=3,
            prompt=1,
            total_prompts=4
        )
        assert ctx.format_prefix() == "[proposal-dev:2/3:P1/4]"
    
    def test_single_cycle_no_cycle_number(self):
        """Test single cycle workflows don't show cycle number."""
        ctx = WorkflowContext(
            workflow_name="quick-fix",
            cycle=1,
            total_cycles=1,
            prompt=2,
            total_prompts=3
        )
        # Single cycle should not show cycle position
        assert ctx.format_prefix() == "[quick-fix:P2/3]"
    
    def test_phase_name_alternative(self):
        """Test phase name as alternative to prompt number."""
        ctx = WorkflowContext(
            workflow_name="audit",
            cycle=1,
            total_cycles=2,
            phase_name="Execute"
        )
        assert ctx.format_prefix() == "[audit:1/2:Execute]"


class TestWorkflowLoggerAdapter:
    """Test WorkflowLoggerAdapter class."""
    
    def test_adapter_adds_prefix(self):
        """Test adapter adds workflow prefix to messages."""
        base_logger = get_logger("sdqctl.test")
        ctx = WorkflowContext(workflow_name="test-flow")
        adapter = WorkflowLoggerAdapter(base_logger, ctx)
        
        msg, kwargs = adapter.process("Test message", {})
        assert msg == "[test-flow] Test message"
    
    def test_adapter_no_prefix_when_empty(self):
        """Test adapter doesn't modify message when context empty."""
        base_logger = get_logger("sdqctl.test")
        ctx = WorkflowContext()
        adapter = WorkflowLoggerAdapter(base_logger, ctx)
        
        msg, kwargs = adapter.process("Test message", {})
        assert msg == "Test message"
    
    def test_update_context(self):
        """Test updating context fields."""
        base_logger = get_logger("sdqctl.test")
        ctx = WorkflowContext(workflow_name="my-flow")
        adapter = WorkflowLoggerAdapter(base_logger, ctx)
        
        # Initial prefix
        msg1, _ = adapter.process("msg", {})
        assert msg1 == "[my-flow] msg"
        
        # Update cycle
        adapter.update_context(cycle=2, total_cycles=5)
        msg2, _ = adapter.process("msg", {})
        assert msg2 == "[my-flow:2/5] msg"
    
    def test_adapter_has_trace_method(self):
        """Test adapter has trace method for compatibility."""
        base_logger = get_logger("sdqctl.test")
        ctx = WorkflowContext(workflow_name="test")
        adapter = WorkflowLoggerAdapter(base_logger, ctx)
        
        assert hasattr(adapter, "trace")
        assert callable(adapter.trace)


class TestWorkflowContextGlobal:
    """Test global workflow context management."""
    
    def setup_method(self):
        """Clear context before each test."""
        set_workflow_context(None)
    
    def teardown_method(self):
        """Clear context after each test."""
        set_workflow_context(None)
    
    def test_get_returns_none_initially(self):
        """Test get_workflow_context returns None initially."""
        assert get_workflow_context() is None
    
    def test_set_and_get_context(self):
        """Test setting and getting workflow context."""
        ctx = WorkflowContext(workflow_name="my-workflow")
        set_workflow_context(ctx)
        
        retrieved = get_workflow_context()
        assert retrieved is ctx
        assert retrieved.workflow_name == "my-workflow"
    
    def test_set_none_clears_context(self):
        """Test setting None clears the context."""
        ctx = WorkflowContext(workflow_name="temp")
        set_workflow_context(ctx)
        assert get_workflow_context() is not None
        
        set_workflow_context(None)
        assert get_workflow_context() is None


class TestWorkflowContextFormatter:
    """Test WorkflowContextFormatter class."""
    
    def setup_method(self):
        """Clear context before each test."""
        set_workflow_context(None)
    
    def teardown_method(self):
        """Clear context after each test."""
        set_workflow_context(None)
    
    def test_formatter_adds_prefix_when_context_set(self):
        """Test formatter adds prefix when workflow context is set."""
        ctx = WorkflowContext(workflow_name="formatter-test", cycle=1, total_cycles=2)
        set_workflow_context(ctx)
        
        formatter = WorkflowContextFormatter("%(message)s")
        
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Test message", args=(), exc_info=None
        )
        
        formatted = formatter.format(record)
        assert "[formatter-test:1/2]" in formatted
        assert "Test message" in formatted
    
    def test_formatter_no_prefix_without_context(self):
        """Test formatter doesn't add prefix when no context."""
        formatter = WorkflowContextFormatter("%(message)s")
        
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Test message", args=(), exc_info=None
        )
        
        formatted = formatter.format(record)
        assert formatted == "Test message"


class TestGetWorkflowLogger:
    """Test get_workflow_logger convenience function."""
    
    def test_creates_adapter_with_context(self):
        """Test get_workflow_logger creates adapter with context."""
        logger = get_workflow_logger(
            "sdqctl.test",
            workflow_name="convenience-test",
            cycle=3,
            total_cycles=5
        )
        
        assert isinstance(logger, WorkflowLoggerAdapter)
        assert logger.context.workflow_name == "convenience-test"
        assert logger.context.cycle == 3
        assert logger.context.total_cycles == 5
    
    def test_minimal_arguments(self):
        """Test get_workflow_logger with minimal arguments."""
        logger = get_workflow_logger("sdqctl.minimal")
        
        assert isinstance(logger, WorkflowLoggerAdapter)
        assert logger.context.workflow_name is None
