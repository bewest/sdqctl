"""
Tests for Context management - sdqctl/core/context.py

P1 High Priority - Context management tests.
"""

import pytest
from pathlib import Path

from sdqctl.core.context import ContextManager, ContextFile, ContextWindow


class TestContextWindow:
    """Tests for ContextWindow tracking."""

    def test_usage_percent(self):
        """Test usage percentage calculation."""
        window = ContextWindow(used_tokens=64000, max_tokens=128000)
        
        assert window.usage_percent == 0.5

    def test_usage_percent_zero_max(self):
        """Test usage with zero max tokens."""
        window = ContextWindow(used_tokens=100, max_tokens=0)
        
        assert window.usage_percent == 0

    def test_is_near_limit_below(self):
        """Test near limit check when below threshold."""
        window = ContextWindow(
            used_tokens=70000,
            max_tokens=128000,
            limit_threshold=0.8,  # 80%
        )
        
        # 70000/128000 = 54.7%, below 80%
        assert window.is_near_limit is False

    def test_is_near_limit_at_threshold(self):
        """Test near limit check at threshold."""
        window = ContextWindow(
            used_tokens=102400,
            max_tokens=128000,
            limit_threshold=0.8,
        )
        
        # 102400/128000 = 80%
        assert window.is_near_limit is True

    def test_is_near_limit_above(self):
        """Test near limit check above threshold."""
        window = ContextWindow(
            used_tokens=120000,
            max_tokens=128000,
            limit_threshold=0.8,
        )
        
        # 120000/128000 = 93.75%
        assert window.is_near_limit is True

    def test_available_tokens(self):
        """Test available tokens calculation."""
        window = ContextWindow(
            used_tokens=50000,
            max_tokens=128000,
            limit_threshold=0.8,
        )
        
        # Limit is 80% of 128000 = 102400
        # Available = 102400 - 50000 = 52400
        assert window.available_tokens == 52400

    def test_available_tokens_at_limit(self):
        """Test available returns 0 when at limit."""
        window = ContextWindow(
            used_tokens=110000,
            max_tokens=128000,
            limit_threshold=0.8,
        )
        
        assert window.available_tokens == 0


class TestContextManagerResolvePattern:
    """Tests for pattern resolution."""

    def test_resolve_single_file(self, temp_workspace):
        """Test resolving single file path."""
        ctx = ContextManager(base_path=temp_workspace)
        
        paths = ctx.resolve_pattern("@lib/auth.js")
        
        assert len(paths) == 1
        assert paths[0].name == "auth.js"

    def test_resolve_glob_pattern(self, temp_workspace):
        """Test resolving glob pattern."""
        ctx = ContextManager(base_path=temp_workspace)
        
        paths = ctx.resolve_pattern("@lib/*.js")
        
        assert len(paths) == 3  # auth.js, utils.js, secret.js
        names = [p.name for p in paths]
        assert "auth.js" in names
        assert "utils.js" in names

    def test_resolve_recursive_glob(self, temp_workspace):
        """Test resolving recursive glob pattern."""
        # Create nested structure
        (temp_workspace / "lib" / "deep").mkdir()
        (temp_workspace / "lib" / "deep" / "nested.js").write_text("// nested")
        
        ctx = ContextManager(base_path=temp_workspace)
        
        paths = ctx.resolve_pattern("@lib/**/*.js")
        
        assert len(paths) >= 4  # auth, utils, secret, nested
        names = [p.name for p in paths]
        assert "nested.js" in names

    def test_resolve_pattern_without_at(self, temp_workspace):
        """Test pattern works without @ prefix."""
        ctx = ContextManager(base_path=temp_workspace)
        
        paths = ctx.resolve_pattern("lib/auth.js")
        
        assert len(paths) == 1

    def test_resolve_nonexistent_file(self, temp_workspace):
        """Test resolving non-existent file returns empty."""
        ctx = ContextManager(base_path=temp_workspace)
        
        paths = ctx.resolve_pattern("@lib/nonexistent.js")
        
        assert len(paths) == 0

    def test_resolve_no_matches(self, temp_workspace):
        """Test glob with no matches returns empty."""
        ctx = ContextManager(base_path=temp_workspace)
        
        paths = ctx.resolve_pattern("@lib/*.xyz")
        
        assert len(paths) == 0


class TestContextManagerAddFile:
    """Tests for adding files to context."""

    def test_add_file(self, temp_workspace):
        """Test adding a file to context."""
        ctx = ContextManager(base_path=temp_workspace)
        
        file_path = temp_workspace / "lib" / "auth.js"
        ctx_file = ctx.add_file(file_path)
        
        assert ctx_file is not None
        assert ctx_file.path == file_path
        assert "// auth code" in ctx_file.content
        assert ctx_file.tokens_estimate > 0

    def test_add_file_updates_tokens(self, temp_workspace):
        """Test adding file updates token count."""
        ctx = ContextManager(base_path=temp_workspace)
        
        initial = ctx.window.used_tokens
        ctx.add_file(temp_workspace / "lib" / "auth.js")
        
        assert ctx.window.used_tokens > initial
        assert len(ctx.files) == 1

    def test_add_file_nonexistent(self, temp_workspace):
        """Test adding non-existent file returns None."""
        ctx = ContextManager(base_path=temp_workspace)
        
        result = ctx.add_file(temp_workspace / "nonexistent.js")
        
        assert result is None
        assert len(ctx.files) == 0

    def test_add_file_tracks_in_list(self, temp_workspace):
        """Test files are tracked in files list."""
        ctx = ContextManager(base_path=temp_workspace)
        
        ctx.add_file(temp_workspace / "lib" / "auth.js")
        ctx.add_file(temp_workspace / "lib" / "utils.js")
        
        assert len(ctx.files) == 2


class TestContextManagerAddPattern:
    """Tests for adding files via pattern."""

    def test_add_pattern(self, temp_workspace):
        """Test adding files via glob pattern."""
        ctx = ContextManager(base_path=temp_workspace)
        
        added = ctx.add_pattern("@lib/*.js")
        
        assert len(added) == 3
        assert len(ctx.files) == 3

    def test_add_pattern_cumulative(self, temp_workspace):
        """Test patterns are cumulative."""
        ctx = ContextManager(base_path=temp_workspace)
        
        ctx.add_pattern("@lib/auth.js")
        ctx.add_pattern("@lib/utils.js")
        
        assert len(ctx.files) == 2


class TestContextManagerConversationTokens:
    """Tests for conversation token tracking."""

    def test_add_conversation_turn(self, temp_workspace):
        """Test tracking tokens from conversation."""
        ctx = ContextManager(base_path=temp_workspace)
        
        initial = ctx.conversation_tokens
        ctx.add_conversation_turn("A" * 400)  # ~100 tokens
        
        assert ctx.conversation_tokens > initial
        assert ctx.window.used_tokens > 0


class TestContextManagerContent:
    """Tests for context content generation."""

    def test_get_context_content_empty(self, temp_workspace):
        """Test content when no files loaded."""
        ctx = ContextManager(base_path=temp_workspace)
        
        content = ctx.get_context_content()
        
        assert content == ""

    def test_get_context_content(self, temp_workspace):
        """Test formatted context content."""
        ctx = ContextManager(base_path=temp_workspace)
        ctx.add_file(temp_workspace / "lib" / "auth.js")
        
        content = ctx.get_context_content()
        
        assert "## Context Files" in content
        assert "auth.js" in content
        assert "```" in content
        assert "// auth code" in content


class TestContextManagerClear:
    """Tests for clearing context."""

    def test_clear_files(self, temp_workspace):
        """Test clearing loaded files."""
        ctx = ContextManager(base_path=temp_workspace)
        ctx.add_pattern("@lib/*.js")
        
        initial_tokens = ctx.window.used_tokens
        assert len(ctx.files) > 0
        
        ctx.clear_files()
        
        assert len(ctx.files) == 0
        assert ctx.window.used_tokens < initial_tokens


class TestContextManagerStatus:
    """Tests for status reporting."""

    def test_get_status(self, temp_workspace):
        """Test status dictionary."""
        ctx = ContextManager(base_path=temp_workspace)
        ctx.add_pattern("@lib/*.js")
        ctx.add_conversation_turn("Test message")
        
        status = ctx.get_status()
        
        assert status["files_loaded"] == 3
        assert status["file_tokens"] > 0
        assert status["conversation_tokens"] > 0
        assert status["total_tokens"] > 0
        assert "usage_percent" in status
        assert "near_limit" in status
        assert "available_tokens" in status


class TestContextManagerInitialization:
    """Tests for context manager initialization."""

    def test_default_initialization(self):
        """Test default values."""
        ctx = ContextManager()
        
        assert ctx.base_path == Path.cwd()
        assert ctx.window.max_tokens == 128000
        assert ctx.window.limit_threshold == 0.8

    def test_custom_initialization(self, temp_workspace):
        """Test custom values."""
        ctx = ContextManager(
            base_path=temp_workspace,
            max_tokens=64000,
            limit_threshold=0.7,
        )
        
        assert ctx.base_path == temp_workspace
        assert ctx.window.max_tokens == 64000
        assert ctx.window.limit_threshold == 0.7


class TestContextManagerPathFilter:
    """Tests for path filter functionality."""

    def test_path_filter_denies_files(self, temp_workspace):
        """Test path filter can deny specific files."""
        # Create test files
        (temp_workspace / "allowed.py").write_text("allowed content")
        (temp_workspace / "denied.py").write_text("denied content")
        
        # Filter that denies files named "denied.py"
        def deny_filter(path: str) -> bool:
            return "denied.py" not in path
        
        ctx = ContextManager(base_path=temp_workspace, path_filter=deny_filter)
        
        # Allowed file should be added
        result = ctx.add_file(temp_workspace / "allowed.py")
        assert result is not None
        assert len(ctx.files) == 1
        
        # Denied file should be filtered out
        result = ctx.add_file(temp_workspace / "denied.py")
        assert result is None
        assert len(ctx.files) == 1  # Still just the allowed file

    def test_path_filter_with_pattern(self, temp_workspace):
        """Test path filter works with glob patterns."""
        # Create test files
        lib_dir = temp_workspace / "lib"
        lib_dir.mkdir(exist_ok=True)
        (lib_dir / "module1.py").write_text("module 1")
        (lib_dir / "module2.py").write_text("module 2")
        (lib_dir / "secret.py").write_text("secret content")
        
        # Filter that denies "secret"
        def deny_secret(path: str) -> bool:
            return "secret" not in path
        
        ctx = ContextManager(base_path=temp_workspace, path_filter=deny_secret)
        added = ctx.add_pattern("@lib/*.py")
        
        # Should add module1 and module2, but not secret
        assert len(added) == 2
        names = [f.path.name for f in ctx.files]
        assert "module1.py" in names
        assert "module2.py" in names
        assert "secret.py" not in names

    def test_no_filter_allows_all(self, temp_workspace):
        """Test that no filter allows all files."""
        (temp_workspace / "file1.py").write_text("content 1")
        (temp_workspace / "file2.py").write_text("content 2")
        
        ctx = ContextManager(base_path=temp_workspace)  # No filter
        ctx.add_file(temp_workspace / "file1.py")
        ctx.add_file(temp_workspace / "file2.py")
        
        assert len(ctx.files) == 2


class TestSessionWithFileRestrictions:
    """Tests for Session respecting file restrictions."""

    def test_session_filters_context_by_deny_patterns(self, temp_workspace):
        """Test Session applies DENY-FILES to context loading."""
        from sdqctl.core.session import Session
        from sdqctl.core.conversation import ConversationFile, FileRestrictions
        
        # Create test files
        (temp_workspace / "public.py").write_text("public content")
        (temp_workspace / "secret.py").write_text("secret content")
        
        # Create conversation with deny pattern
        conv = ConversationFile(
            cwd=str(temp_workspace),
            context_files=["@*.py"],
            file_restrictions=FileRestrictions(deny_patterns=["*secret*"]),
        )
        
        session = Session(conv)
        
        # Public file should be loaded, secret should be denied
        loaded_paths = [f.path.name for f in session.context.files]
        assert "public.py" in loaded_paths
        assert "secret.py" not in loaded_paths

    def test_session_filters_context_by_allow_patterns(self, temp_workspace):
        """Test Session applies ALLOW-FILES to context loading."""
        from sdqctl.core.session import Session
        from sdqctl.core.conversation import ConversationFile, FileRestrictions
        
        # Create test files
        (temp_workspace / "allowed.py").write_text("allowed")
        (temp_workspace / "denied.js").write_text("denied")
        
        # Create conversation with allow pattern (only .py files)
        conv = ConversationFile(
            cwd=str(temp_workspace),
            context_files=["@*.*"],
            file_restrictions=FileRestrictions(allow_patterns=["*.py"]),
        )
        
        session = Session(conv)
        
        # Only .py file should be loaded
        loaded_paths = [f.path.name for f in session.context.files]
        assert "allowed.py" in loaded_paths
        assert "denied.js" not in loaded_paths

    def test_session_no_restrictions_loads_all(self, temp_workspace):
        """Test Session with no restrictions loads all context files."""
        from sdqctl.core.session import Session
        from sdqctl.core.conversation import ConversationFile
        
        # Create test files
        (temp_workspace / "file1.py").write_text("content 1")
        (temp_workspace / "file2.py").write_text("content 2")
        
        conv = ConversationFile(
            cwd=str(temp_workspace),
            context_files=["@*.py"],
        )
        
        session = Session(conv)
        
        assert len(session.context.files) == 2
