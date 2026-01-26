"""Tests for iterate_helpers module."""

import pytest
from pathlib import Path
from unittest.mock import Mock
import click

from sdqctl.commands.iterate_helpers import (
    TURN_SEPARATOR,
    TurnGroup,
    build_infinite_session_config,
    is_workflow_file,
    parse_targets,
    validate_targets,
)


class TestTurnGroup:
    """Tests for TurnGroup dataclass."""

    def test_default_items_empty(self):
        group = TurnGroup()
        assert group.items == []

    def test_items_assigned(self):
        group = TurnGroup(items=["a", "b", "c"])
        assert group.items == ["a", "b", "c"]


class TestIsWorkflowFile:
    """Tests for is_workflow_file function."""

    def test_conv_file_exists(self, tmp_path):
        conv_file = tmp_path / "test.conv"
        conv_file.write_text("PROMPT: test")
        assert is_workflow_file(str(conv_file)) is True

    def test_copilot_file_exists(self, tmp_path):
        copilot_file = tmp_path / "test.copilot"
        copilot_file.write_text("PROMPT: test")
        assert is_workflow_file(str(copilot_file)) is True

    def test_non_workflow_file(self, tmp_path):
        py_file = tmp_path / "test.py"
        py_file.write_text("print('hello')")
        assert is_workflow_file(str(py_file)) is False

    def test_nonexistent_file(self):
        assert is_workflow_file("/nonexistent/file.conv") is False


class TestParseTargets:
    """Tests for parse_targets function."""

    def test_single_item(self):
        groups = parse_targets(("prompt1",))
        assert len(groups) == 1
        assert groups[0].items == ["prompt1"]

    def test_multiple_items_single_group(self):
        groups = parse_targets(("a", "b", "c"))
        assert len(groups) == 1
        assert groups[0].items == ["a", "b", "c"]

    def test_separator_creates_groups(self):
        groups = parse_targets(("a", "---", "b"))
        assert len(groups) == 2
        assert groups[0].items == ["a"]
        assert groups[1].items == ["b"]

    def test_multiple_separators(self):
        groups = parse_targets(("a", "---", "b", "---", "c"))
        assert len(groups) == 3

    def test_empty_targets(self):
        groups = parse_targets(())
        assert len(groups) == 0

    def test_separator_at_end_filtered(self):
        groups = parse_targets(("a", "---"))
        assert len(groups) == 1
        assert groups[0].items == ["a"]


class TestValidateTargets:
    """Tests for validate_targets function."""

    def test_no_workflow_file(self):
        groups = [TurnGroup(items=["prompt1", "prompt2"])]
        workflow, pre, post = validate_targets(groups)
        assert workflow is None
        assert pre == ["prompt1", "prompt2"]
        assert post == []

    def test_single_workflow_file(self, tmp_path):
        conv_file = tmp_path / "test.conv"
        conv_file.write_text("PROMPT: test")
        groups = [TurnGroup(items=[str(conv_file)])]
        workflow, pre, post = validate_targets(groups)
        assert workflow == str(conv_file)
        assert pre == []
        assert post == []

    def test_pre_prompts_before_workflow(self, tmp_path):
        conv_file = tmp_path / "test.conv"
        conv_file.write_text("PROMPT: test")
        groups = [TurnGroup(items=["pre1", "pre2", str(conv_file)])]
        workflow, pre, post = validate_targets(groups)
        assert workflow == str(conv_file)
        assert pre == ["pre1", "pre2"]
        assert post == []

    def test_post_prompts_after_workflow(self, tmp_path):
        conv_file = tmp_path / "test.conv"
        conv_file.write_text("PROMPT: test")
        groups = [TurnGroup(items=[str(conv_file), "post1", "post2"])]
        workflow, pre, post = validate_targets(groups)
        assert workflow == str(conv_file)
        assert pre == []
        assert post == ["post1", "post2"]

    def test_multiple_conv_files_raises_error(self, tmp_path):
        conv1 = tmp_path / "test1.conv"
        conv2 = tmp_path / "test2.conv"
        conv1.write_text("PROMPT: test1")
        conv2.write_text("PROMPT: test2")
        groups = [TurnGroup(items=[str(conv1), str(conv2)])]
        with pytest.raises(click.UsageError, match="only ONE .conv file"):
            validate_targets(groups)


class TestBuildInfiniteSessionConfig:
    """Tests for build_infinite_session_config function."""

    def test_defaults(self):
        config = build_infinite_session_config(
            no_infinite_sessions=False,
            compaction_threshold=80,
        )
        assert config.enabled is True
        assert config.min_compaction_density == 0.30
        assert config.background_threshold == 0.80
        assert config.buffer_exhaustion == 0.95

    def test_disabled_via_cli(self):
        config = build_infinite_session_config(
            no_infinite_sessions=True,
            compaction_threshold=80,
        )
        assert config.enabled is False

    def test_disabled_via_conv(self):
        config = build_infinite_session_config(
            no_infinite_sessions=False,
            compaction_threshold=80,
            conv_infinite_sessions=False,
        )
        assert config.enabled is False

    def test_cli_overrides_conv(self):
        config = build_infinite_session_config(
            no_infinite_sessions=True,
            compaction_threshold=80,
            conv_infinite_sessions=True,  # Should be overridden
        )
        assert config.enabled is False

    def test_custom_thresholds(self):
        config = build_infinite_session_config(
            no_infinite_sessions=False,
            compaction_threshold=70,
            buffer_threshold=90,
            min_compaction_density=50,
        )
        assert config.background_threshold == 0.70
        assert config.buffer_exhaustion == 0.90
        assert config.min_compaction_density == 0.50

    def test_conv_thresholds_used_when_cli_default(self):
        """When CLI passes None, conv directive values should be used."""
        config = build_infinite_session_config(
            no_infinite_sessions=False,
            compaction_threshold=None,  # None = use conv/default
            conv_compaction_threshold=0.75,
            conv_compaction_min=0.40,
        )
        assert config.background_threshold == 0.75
        assert config.min_compaction_density == 0.40


class TestBuildInfiniteSessionConfigCompactionMax:
    """Tests for COMPACTION-MAX directive and --compaction-max CLI option."""

    def test_conv_compaction_max_used_when_cli_not_set(self):
        """Conv COMPACTION-MAX directive should be used when CLI not set."""
        config = build_infinite_session_config(
            no_infinite_sessions=False,
            compaction_threshold=None,
            buffer_threshold=None,
            min_compaction_density=None,
            conv_compaction_max=0.90,
        )
        assert config.buffer_exhaustion == 0.90

    def test_cli_compaction_max_overrides_conv(self):
        """CLI --compaction-max should override conv directive."""
        config = build_infinite_session_config(
            no_infinite_sessions=False,
            compaction_threshold=None,
            buffer_threshold=85,  # CLI override
            conv_compaction_max=0.90,  # Conv directive
        )
        assert config.buffer_exhaustion == 0.85

    def test_default_compaction_max_when_none_set(self):
        """Default 95% should be used when neither CLI nor conv set."""
        config = build_infinite_session_config(
            no_infinite_sessions=False,
            compaction_threshold=None,
            buffer_threshold=None,
        )
        assert config.buffer_exhaustion == 0.95

    def test_all_thresholds_from_conv(self):
        """All compaction thresholds should be configurable via conv directives."""
        config = build_infinite_session_config(
            no_infinite_sessions=False,
            compaction_threshold=None,
            buffer_threshold=None,
            min_compaction_density=None,
            conv_compaction_min=0.25,
            conv_compaction_threshold=0.70,
            conv_compaction_max=0.85,
        )
        assert config.min_compaction_density == 0.25
        assert config.background_threshold == 0.70
        assert config.buffer_exhaustion == 0.85
