"""
Tests for sdqctl apply command - component iteration workflows.

Tests the apply command's ability to iterate over components,
substitute template variables, and track progress.
"""

import pytest
from pathlib import Path
from click.testing import CliRunner

from sdqctl.cli import cli
from sdqctl.core.conversation import ConversationFile, apply_iteration_context


class TestApplyCommandBasic:
    """Test basic apply command functionality."""

    def test_apply_help(self, cli_runner):
        """Test apply --help shows usage."""
        result = cli_runner.invoke(cli, ["apply", "--help"])
        assert result.exit_code == 0
        assert "--components" in result.output
        assert "--from-discovery" in result.output
        assert "--progress" in result.output

    def test_apply_help_shows_stop_file_option(self, cli_runner):
        """Test apply --help shows --no-stop-file-prologue option."""
        result = cli_runner.invoke(cli, ["apply", "--help"])
        assert result.exit_code == 0
        assert "--no-stop-file-prologue" in result.output

    def test_apply_requires_workflow(self, cli_runner):
        """Test apply requires workflow argument."""
        result = cli_runner.invoke(cli, ["apply"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "required" in result.output.lower()

    def test_apply_dry_run(self, cli_runner, workflow_file, tmp_path):
        """Test apply --dry-run shows configuration."""
        # Create a component to iterate over
        component = tmp_path / "component.js"
        component.write_text("// component code")
        
        result = cli_runner.invoke(cli, [
            "apply", str(workflow_file),
            "--components", str(component),
            "--dry-run"
        ])
        assert result.exit_code == 0


class TestApplyComponentDiscovery:
    """Test apply command component discovery."""

    def test_apply_discovers_glob_pattern(self, cli_runner, tmp_path):
        """Test apply discovers components via glob pattern."""
        # Create workflow
        workflow = tmp_path / "analyze.conv"
        workflow.write_text("MODEL gpt-4\nADAPTER mock\nPROMPT Analyze {{COMPONENT_NAME}}.")
        
        # Create components
        components_dir = tmp_path / "components"
        components_dir.mkdir()
        for i in range(3):
            (components_dir / f"comp{i}.js").write_text(f"// component {i}")
        
        result = cli_runner.invoke(cli, [
            "apply", str(workflow),
            "--components", str(components_dir / "*.js"),
            "--adapter", "mock",
            "--dry-run"
        ])
        assert result.exit_code == 0

    def test_apply_from_discovery_file(self, cli_runner, tmp_path):
        """Test apply loads components from discovery JSON."""
        # Create workflow
        workflow = tmp_path / "analyze.conv"
        workflow.write_text("MODEL gpt-4\nADAPTER mock\nPROMPT Analyze {{COMPONENT_PATH}}.")
        
        # Create discovery file
        discovery = tmp_path / "components.json"
        discovery.write_text('{"components": [{"path": "lib/auth.js", "type": "plugin"}]}')
        
        result = cli_runner.invoke(cli, [
            "apply", str(workflow),
            "--from-discovery", str(discovery),
            "--adapter", "mock",
            "--dry-run"
        ])
        assert result.exit_code == 0


class TestApplyExecution:
    """Test apply command execution with mock adapter."""

    def test_apply_executes_for_single_component(self, cli_runner, tmp_path):
        """Test apply executes workflow for one component."""
        # Create workflow
        workflow = tmp_path / "analyze.conv"
        workflow.write_text("MODEL gpt-4\nADAPTER mock\nPROMPT Analyze {{COMPONENT_NAME}}.")
        
        # Create component
        component = tmp_path / "auth.js"
        component.write_text("// auth module")
        
        result = cli_runner.invoke(cli, [
            "apply", str(workflow),
            "--components", str(component),
            "--adapter", "mock"
        ])
        assert result.exit_code == 0

    def test_apply_executes_for_multiple_components(self, cli_runner, tmp_path):
        """Test apply iterates over multiple components."""
        # Create workflow
        workflow = tmp_path / "analyze.conv"
        workflow.write_text("MODEL gpt-4\nADAPTER mock\nPROMPT Analyze {{COMPONENT_NAME}}.")
        
        # Create components
        for name in ["auth", "db", "api"]:
            (tmp_path / f"{name}.js").write_text(f"// {name} module")
        
        result = cli_runner.invoke(cli, [
            "apply", str(workflow),
            "--components", str(tmp_path / "*.js"),
            "--adapter", "mock"
        ])
        assert result.exit_code == 0


class TestApplyTemplateVariables:
    """Test template variable substitution in apply."""

    def test_component_path_substituted(self):
        """Test {{COMPONENT_PATH}} is substituted."""
        content = "MODEL gpt-4\nADAPTER mock\nPROMPT Analyze {{COMPONENT_PATH}}."
        conv = ConversationFile.parse(content)
        
        result = apply_iteration_context(conv, "/lib/auth.js", 1, 5, "plugin")
        assert "/lib/auth.js" in result.prompts[0]

    def test_component_name_substituted(self):
        """Test {{COMPONENT_NAME}} is substituted."""
        content = "MODEL gpt-4\nADAPTER mock\nPROMPT Analyze {{COMPONENT_NAME}}."
        conv = ConversationFile.parse(content)
        
        result = apply_iteration_context(conv, "/lib/auth.js", 1, 5, "plugin")
        assert "auth" in result.prompts[0]

    def test_iteration_index_substituted(self):
        """Test {{ITERATION_INDEX}} is substituted."""
        content = (
            "MODEL gpt-4\nADAPTER mock\n"
            "PROMPT Item {{ITERATION_INDEX}} of {{ITERATION_TOTAL}}."
        )
        conv = ConversationFile.parse(content)
        
        result = apply_iteration_context(conv, "/lib/auth.js", 3, 10, "plugin")
        assert "3" in result.prompts[0]
        assert "10" in result.prompts[0]

    def test_component_type_substituted(self):
        """Test {{COMPONENT_TYPE}} is substituted."""
        content = "MODEL gpt-4\nADAPTER mock\nPROMPT This is a {{COMPONENT_TYPE}}."
        conv = ConversationFile.parse(content)
        
        result = apply_iteration_context(conv, "/lib/auth.js", 1, 1, "api-endpoint")
        assert "api-endpoint" in result.prompts[0]


class TestApplyOptions:
    """Test apply command options."""

    def test_apply_with_adapter_override(self, cli_runner, tmp_path):
        """Test --adapter overrides workflow setting."""
        workflow = tmp_path / "test.conv"
        workflow.write_text("MODEL gpt-4\nADAPTER copilot\nPROMPT Test.")
        component = tmp_path / "comp.js"
        component.write_text("// code")
        
        result = cli_runner.invoke(cli, [
            "apply", str(workflow),
            "--components", str(component),
            "--adapter", "mock",
            "--dry-run"
        ])
        assert result.exit_code == 0

    def test_apply_with_output_dir(self, cli_runner, tmp_path):
        """Test --output-dir sets output directory."""
        workflow = tmp_path / "test.conv"
        workflow.write_text("MODEL gpt-4\nADAPTER mock\nPROMPT Test.")
        component = tmp_path / "comp.js"
        component.write_text("// code")
        output_dir = tmp_path / "output"
        
        result = cli_runner.invoke(cli, [
            "apply", str(workflow),
            "--components", str(component),
            "--output-dir", str(output_dir),
            "--adapter", "mock"
        ])
        assert result.exit_code == 0

    def test_apply_with_progress_file(self, cli_runner, tmp_path):
        """Test --progress creates progress tracker file."""
        workflow = tmp_path / "test.conv"
        workflow.write_text("MODEL gpt-4\nADAPTER mock\nPROMPT Test.")
        component = tmp_path / "comp.js"
        component.write_text("// code")
        progress = tmp_path / "progress.md"
        
        result = cli_runner.invoke(cli, [
            "apply", str(workflow),
            "--components", str(component),
            "--progress", str(progress),
            "--adapter", "mock"
        ])
        assert result.exit_code == 0
        # Progress file should be created
        assert progress.exists()


class TestApplyInjection:
    """Test prologue/epilogue and header/footer injection in apply."""

    def test_apply_with_prologue(self, cli_runner, tmp_path):
        """Test --prologue adds content to prompts."""
        workflow = tmp_path / "test.conv"
        workflow.write_text("MODEL gpt-4\nADAPTER mock\nPROMPT Analyze.")
        component = tmp_path / "comp.js"
        component.write_text("// code")
        
        result = cli_runner.invoke(cli, [
            "apply", str(workflow),
            "--components", str(component),
            "--adapter", "mock",
            "--prologue", "Component iteration context"
        ])
        assert result.exit_code == 0

    def test_apply_with_header_footer(self, cli_runner, tmp_path):
        """Test --header and --footer wrap output."""
        workflow = tmp_path / "test.conv"
        workflow.write_text("MODEL gpt-4\nADAPTER mock\nPROMPT Analyze.")
        component = tmp_path / "comp.js"
        component.write_text("// code")
        output_dir = tmp_path / "output"
        
        result = cli_runner.invoke(cli, [
            "apply", str(workflow),
            "--components", str(component),
            "--adapter", "mock",
            "--header", "# Component Report",
            "--footer", "---\nGenerated by apply",
            "--output-dir", str(output_dir)
        ])
        assert result.exit_code == 0


class TestApplyParallel:
    """Test apply command parallel execution."""

    def test_apply_parallel_option(self, cli_runner, tmp_path):
        """Test --parallel option is accepted."""
        workflow = tmp_path / "test.conv"
        workflow.write_text("MODEL gpt-4\nADAPTER mock\nPROMPT Analyze {{COMPONENT_NAME}}.")
        
        for i in range(3):
            (tmp_path / f"comp{i}.js").write_text(f"// comp {i}")
        
        result = cli_runner.invoke(cli, [
            "apply", str(workflow),
            "--components", str(tmp_path / "*.js"),
            "--parallel", "2",
            "--adapter", "mock"
        ])
        assert result.exit_code == 0
