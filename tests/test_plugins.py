"""
Tests for plugin discovery and registration.

Tests the .sdqctl/directives.yaml manifest loading and
plugin verifier registration.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from sdqctl.plugins import (
    DirectiveHandler,
    PluginManifest,
    PluginVerifier,
    discover_manifests,
    load_plugin_verifiers,
    register_plugins,
)


class TestPluginManifest:
    """Tests for PluginManifest parsing."""

    def test_from_file_minimal(self, tmp_path):
        """Parse minimal valid manifest."""
        manifest_file = tmp_path / "directives.yaml"
        manifest_file.write_text("""
version: 1
directives: {}
""")
        manifest = PluginManifest.from_file(manifest_file)
        assert manifest.version == 1
        assert manifest.handlers == []
        assert manifest.source_path == manifest_file

    def test_from_file_with_verify_handler(self, tmp_path):
        """Parse manifest with VERIFY directive."""
        manifest_file = tmp_path / "directives.yaml"
        manifest_file.write_text("""
version: 1
directives:
  VERIFY:
    ecosystem-gaps:
      handler: python tools/verify_gaps.py
      description: "Verify gap coverage"
      timeout: 60
""")
        manifest = PluginManifest.from_file(manifest_file)
        assert manifest.version == 1
        assert len(manifest.handlers) == 1

        handler = manifest.handlers[0]
        assert handler.name == "ecosystem-gaps"
        assert handler.directive_type == "VERIFY"
        assert handler.handler == "python tools/verify_gaps.py"
        assert handler.description == "Verify gap coverage"
        assert handler.timeout == 60

    def test_from_file_multiple_handlers(self, tmp_path):
        """Parse manifest with multiple directives."""
        manifest_file = tmp_path / "directives.yaml"
        manifest_file.write_text("""
version: 1
directives:
  VERIFY:
    stpa-hazards:
      handler: python verify_stpa.py
      description: "STPA verification"
    terminology:
      handler: ./check_terms.sh
      description: "Term check"
  TRACE:
    uca:
      handler: python trace_uca.py
      description: "Trace UCA"
      args:
        - name: uca-id
          required: true
""")
        manifest = PluginManifest.from_file(manifest_file)
        assert len(manifest.handlers) == 3

        # Check types
        types = {h.directive_type for h in manifest.handlers}
        assert types == {"VERIFY", "TRACE"}

    def test_from_file_invalid_yaml(self, tmp_path):
        """Raise error for invalid YAML."""
        manifest_file = tmp_path / "directives.yaml"
        manifest_file.write_text("not: valid: yaml: here")

        # Invalid YAML raises an exception
        import yaml
        with pytest.raises(yaml.YAMLError):
            PluginManifest.from_file(manifest_file)

    def test_from_file_non_dict(self, tmp_path):
        """Raise error when YAML is not a dict."""
        manifest_file = tmp_path / "directives.yaml"
        manifest_file.write_text("- list\n- items")

        with pytest.raises(ValueError, match="expected dict"):
            PluginManifest.from_file(manifest_file)


class TestPluginVerifier:
    """Tests for PluginVerifier execution."""

    def test_verify_success(self, tmp_path):
        """Handler returns success on exit 0."""
        handler = DirectiveHandler(
            name="test-plugin",
            directive_type="VERIFY",
            handler="echo success",
            description="Test plugin",
            timeout=5,
        )
        verifier = PluginVerifier(handler, tmp_path)
        result = verifier.verify(tmp_path)

        assert result.passed is True
        assert "passed" in result.summary
        assert "success" in result.details.get("stdout", "")

    def test_verify_failure(self, tmp_path):
        """Handler returns failure on non-zero exit."""
        handler = DirectiveHandler(
            name="test-plugin",
            directive_type="VERIFY",
            handler="sh -c 'echo error >&2; exit 1'",
            description="Test plugin",
            timeout=5,
        )
        verifier = PluginVerifier(handler, tmp_path)
        result = verifier.verify(tmp_path)

        assert result.passed is False
        assert "failed" in result.summary
        assert len(result.errors) == 1

    def test_verify_timeout(self, tmp_path):
        """Handler returns failure on timeout."""
        handler = DirectiveHandler(
            name="test-plugin",
            directive_type="VERIFY",
            handler="sleep 10",
            description="Slow plugin",
            timeout=1,
        )
        verifier = PluginVerifier(handler, tmp_path)
        result = verifier.verify(tmp_path)

        assert result.passed is False
        assert "timed out" in result.summary

    def test_verify_handler_not_found(self, tmp_path):
        """Handler returns failure when command not found."""
        handler = DirectiveHandler(
            name="test-plugin",
            directive_type="VERIFY",
            handler="/nonexistent/command",
            description="Missing handler",
            timeout=5,
        )
        verifier = PluginVerifier(handler, tmp_path)
        result = verifier.verify(tmp_path)

        assert result.passed is False
        assert "not found" in result.summary.lower()

    def test_verify_substitutes_root(self, tmp_path):
        """Handler substitutes {root} placeholder."""
        handler = DirectiveHandler(
            name="test-plugin",
            directive_type="VERIFY",
            handler="echo {root}",
            description="Root test",
            timeout=5,
        )
        verifier = PluginVerifier(handler, tmp_path)
        result = verifier.verify(tmp_path / "subdir")

        assert result.passed is True
        assert "subdir" in result.details.get("stdout", "")


class TestDiscoverManifests:
    """Tests for manifest discovery."""

    def test_discover_workspace_local(self, tmp_path):
        """Find workspace-local manifest."""
        sdqctl_dir = tmp_path / ".sdqctl"
        sdqctl_dir.mkdir()
        manifest = sdqctl_dir / "directives.yaml"
        manifest.write_text("version: 1\ndirectives: {}")

        with patch.object(Path, 'home', return_value=tmp_path / "home"):
            manifests = discover_manifests(tmp_path)

        assert len(manifests) == 1
        assert manifests[0] == manifest

    def test_discover_user_global(self, tmp_path):
        """Find user-global manifest."""
        home = tmp_path / "home"
        sdqctl_dir = home / ".sdqctl"
        sdqctl_dir.mkdir(parents=True)
        manifest = sdqctl_dir / "directives.yaml"
        manifest.write_text("version: 1\ndirectives: {}")

        work = tmp_path / "work"
        work.mkdir()

        with patch.object(Path, 'home', return_value=home):
            manifests = discover_manifests(work)

        assert len(manifests) == 1
        assert manifests[0] == manifest

    def test_discover_both(self, tmp_path):
        """Find both workspace and user-global manifests."""
        # User global
        home = tmp_path / "home"
        (home / ".sdqctl").mkdir(parents=True)
        global_manifest = home / ".sdqctl" / "directives.yaml"
        global_manifest.write_text("version: 1\ndirectives: {}")

        # Workspace local
        work = tmp_path / "work"
        (work / ".sdqctl").mkdir(parents=True)
        local_manifest = work / ".sdqctl" / "directives.yaml"
        local_manifest.write_text("version: 1\ndirectives: {}")

        with patch.object(Path, 'home', return_value=home):
            manifests = discover_manifests(work)

        assert len(manifests) == 2
        assert manifests[0] == local_manifest  # Local first
        assert manifests[1] == global_manifest

    def test_discover_none(self, tmp_path):
        """Return empty list when no manifests found."""
        with patch.object(Path, 'home', return_value=tmp_path / "home"):
            manifests = discover_manifests(tmp_path)

        assert manifests == []


class TestLoadPluginVerifiers:
    """Tests for loading plugin verifiers."""

    def test_load_verify_handlers(self, tmp_path):
        """Load VERIFY handlers as verifiers."""
        sdqctl_dir = tmp_path / ".sdqctl"
        sdqctl_dir.mkdir()
        manifest = sdqctl_dir / "directives.yaml"
        manifest.write_text("""
version: 1
directives:
  VERIFY:
    my-check:
      handler: echo ok
      description: "My verification"
""")

        with patch.object(Path, 'home', return_value=tmp_path / "home"):
            verifiers = load_plugin_verifiers(tmp_path)

        assert "my-check" in verifiers
        assert verifiers["my-check"].name == "my-check"
        assert verifiers["my-check"].description == "My verification"

    def test_skip_non_verify_handlers(self, tmp_path):
        """Only load VERIFY directive types."""
        sdqctl_dir = tmp_path / ".sdqctl"
        sdqctl_dir.mkdir()
        manifest = sdqctl_dir / "directives.yaml"
        manifest.write_text("""
version: 1
directives:
  TRACE:
    uca:
      handler: echo trace
      description: "Trace UCA"
""")

        with patch.object(Path, 'home', return_value=tmp_path / "home"):
            verifiers = load_plugin_verifiers(tmp_path)

        assert "uca" not in verifiers
        assert len(verifiers) == 0

    def test_workspace_wins_over_global(self, tmp_path):
        """Workspace manifest takes precedence over global."""
        # User global
        home = tmp_path / "home"
        (home / ".sdqctl").mkdir(parents=True)
        (home / ".sdqctl" / "directives.yaml").write_text("""
version: 1
directives:
  VERIFY:
    my-check:
      handler: echo global
      description: "Global version"
""")

        # Workspace local
        work = tmp_path / "work"
        (work / ".sdqctl").mkdir(parents=True)
        (work / ".sdqctl" / "directives.yaml").write_text("""
version: 1
directives:
  VERIFY:
    my-check:
      handler: echo local
      description: "Local version"
""")

        with patch.object(Path, 'home', return_value=home):
            verifiers = load_plugin_verifiers(work)

        assert "my-check" in verifiers
        assert verifiers["my-check"].description == "Local version"


class TestRegisterPlugins:
    """Tests for plugin registration into VERIFIERS."""

    def test_register_adds_to_registry(self, tmp_path):
        """Plugins are added to the verifiers registry."""
        sdqctl_dir = tmp_path / ".sdqctl"
        sdqctl_dir.mkdir()
        manifest = sdqctl_dir / "directives.yaml"
        manifest.write_text("""
version: 1
directives:
  VERIFY:
    plugin-check:
      handler: echo ok
      description: "Plugin verifier"
""")

        registry: dict = {}

        with patch.object(Path, 'home', return_value=tmp_path / "home"):
            with patch.object(Path, 'cwd', return_value=tmp_path):
                register_plugins(registry)

        assert "plugin-check" in registry
        # Can instantiate the wrapper
        instance = registry["plugin-check"]()
        assert instance.name == "plugin-check"

    def test_no_override_builtin(self, tmp_path):
        """Plugins don't override built-in verifiers."""
        sdqctl_dir = tmp_path / ".sdqctl"
        sdqctl_dir.mkdir()
        manifest = sdqctl_dir / "directives.yaml"
        manifest.write_text("""
version: 1
directives:
  VERIFY:
    refs:
      handler: echo fake-refs
      description: "Try to override refs"
""")

        class BuiltinRefs:
            name = "refs"
            description = "Built-in"

        registry = {"refs": BuiltinRefs}

        with patch.object(Path, 'home', return_value=tmp_path / "home"):
            with patch.object(Path, 'cwd', return_value=tmp_path):
                register_plugins(registry)

        # Built-in is preserved
        assert registry["refs"] == BuiltinRefs


class TestPluginVerifierIntegration:
    """Integration tests for plugin verifier execution."""

    def test_execute_python_script(self, tmp_path):
        """Execute a Python script as handler."""
        # Create a simple Python verification script
        script = tmp_path / "verify_test.py"
        script.write_text("""
import sys
print("Verification passed")
sys.exit(0)
""")

        handler = DirectiveHandler(
            name="py-check",
            directive_type="VERIFY",
            handler=f"python {script}",
            description="Python verifier",
            timeout=10,
        )
        verifier = PluginVerifier(handler, tmp_path)
        result = verifier.verify(tmp_path)

        assert result.passed is True
        assert "Verification passed" in result.details.get("stdout", "")

    def test_execute_failing_script(self, tmp_path):
        """Capture errors from failing script."""
        script = tmp_path / "verify_fail.py"
        script.write_text("""
import sys
print("Error: missing file", file=sys.stderr)
sys.exit(1)
""")

        handler = DirectiveHandler(
            name="py-fail",
            directive_type="VERIFY",
            handler=f"python {script}",
            description="Failing verifier",
            timeout=10,
        )
        verifier = PluginVerifier(handler, tmp_path)
        result = verifier.verify(tmp_path)

        assert result.passed is False
        assert len(result.errors) == 1
        assert "missing file" in result.errors[0].message


class TestDirectiveHandlerCapabilities:
    """Tests for capability validation."""

    def test_valid_capabilities(self):
        """Accept valid capabilities."""
        handler = DirectiveHandler(
            name="test",
            directive_type="VERIFY",
            handler="echo ok",
            description="Test",
            requires=["read_files", "run_commands"],
        )
        assert handler.validate_capabilities() == []

    def test_invalid_capability(self):
        """Detect invalid capabilities."""
        handler = DirectiveHandler(
            name="test",
            directive_type="VERIFY",
            handler="echo ok",
            description="Test",
            requires=["read_files", "invalid_cap", "network"],
        )
        invalid = handler.validate_capabilities()
        assert invalid == ["invalid_cap"]

    def test_all_valid_capabilities(self):
        """All defined capabilities are valid."""
        handler = DirectiveHandler(
            name="test",
            directive_type="VERIFY",
            handler="echo ok",
            description="Test",
            requires=list(DirectiveHandler.VALID_CAPABILITIES),
        )
        assert handler.validate_capabilities() == []


class TestPluginCommand:
    """Tests for sdqctl plugin CLI commands."""

    def test_plugin_list_empty(self, tmp_path):
        """List plugins when none discovered."""
        from click.testing import CliRunner
        from sdqctl.commands.plugin import plugin

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(plugin, ["list"])
            assert result.exit_code == 0
            assert "No plugins discovered" in result.output

    def test_plugin_list_json_empty(self, tmp_path):
        """List plugins as JSON when empty."""
        from click.testing import CliRunner
        from sdqctl.commands.plugin import plugin
        import json

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(plugin, ["list", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["plugins"] == []
            assert data["manifests"] == []

    def test_plugin_capabilities(self):
        """List available capabilities."""
        from click.testing import CliRunner
        from sdqctl.commands.plugin import plugin

        runner = CliRunner()
        result = runner.invoke(plugin, ["capabilities"])
        assert result.exit_code == 0
        assert "read_files" in result.output
        assert "write_files" in result.output
        assert "(default)" in result.output

    def test_plugin_validate_no_manifest(self, tmp_path):
        """Validate fails when no manifest found."""
        from click.testing import CliRunner
        from sdqctl.commands.plugin import plugin

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(plugin, ["validate"])
            assert result.exit_code == 1
            assert "not found" in result.output

    def test_plugin_validate_valid_manifest(self, tmp_path):
        """Validate passes for valid manifest."""
        from click.testing import CliRunner
        from sdqctl.commands.plugin import plugin

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            sdqctl_dir = Path(".sdqctl")
            sdqctl_dir.mkdir()
            (sdqctl_dir / "directives.yaml").write_text("""
version: 1
directives:
  VERIFY:
    test-check:
      handler: echo ok
      description: "Test verification"
""")
            result = runner.invoke(plugin, ["validate"])
            assert result.exit_code == 0
            assert "Validation passed" in result.output

    def test_plugin_validate_missing_handler(self, tmp_path):
        """Validate fails for missing handler script."""
        from click.testing import CliRunner
        from sdqctl.commands.plugin import plugin

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            sdqctl_dir = Path(".sdqctl")
            sdqctl_dir.mkdir()
            (sdqctl_dir / "directives.yaml").write_text("""
version: 1
directives:
  VERIFY:
    test-check:
      handler: python tools/nonexistent.py
      description: "Test verification"
""")
            result = runner.invoke(plugin, ["validate"])
            assert result.exit_code == 1
            assert "not found" in result.output
