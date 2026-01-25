"""Tests for model capability registry and resolution."""

import pytest

from sdqctl.core.models import (
    ModelRequirement,
    ModelPreference,
    ModelRequirements,
    ResolutionPolicy,
    CostTier,
    SpeedTier,
    CapabilityClass,
    resolve_model,
    _parse_context_size,
)


class TestModelRequirement:
    """Tests for ModelRequirement parsing."""

    def test_parse_context_requirement(self):
        """Test parsing context:50k requirement."""
        req = ModelRequirement.parse("context:50k")
        assert req.dimension == "context"
        assert req.value == "50k"

    def test_parse_tier_requirement(self):
        """Test parsing tier:standard requirement."""
        req = ModelRequirement.parse("tier:standard")
        assert req.dimension == "tier"
        assert req.value == "standard"

    def test_parse_with_spaces(self):
        """Test parsing with whitespace."""
        req = ModelRequirement.parse("  context : 100k  ")
        assert req.dimension == "context"
        assert req.value == "100k"

    def test_invalid_format_no_colon(self):
        """Test error on invalid format."""
        with pytest.raises(ValueError, match="Expected 'dimension:value'"):
            ModelRequirement.parse("context50k")

    def test_unknown_dimension(self):
        """Test error on unknown dimension."""
        with pytest.raises(ValueError, match="Unknown requirement dimension"):
            ModelRequirement.parse("unknown:value")


class TestModelPreference:
    """Tests for ModelPreference parsing."""

    def test_parse_vendor_preference(self):
        """Test parsing vendor:anthropic preference."""
        pref = ModelPreference.parse("vendor:anthropic")
        assert pref.dimension == "vendor"
        assert pref.value == "anthropic"

    def test_parse_family_preference(self):
        """Test parsing family:claude preference."""
        pref = ModelPreference.parse("family:claude")
        assert pref.dimension == "family"
        assert pref.value == "claude"

    def test_invalid_dimension(self):
        """Test error on non-preference dimension."""
        with pytest.raises(ValueError, match="Unknown preference dimension"):
            ModelPreference.parse("context:50k")


class TestModelRequirements:
    """Tests for ModelRequirements collection."""

    def test_add_requirements(self):
        """Test adding multiple requirements."""
        reqs = ModelRequirements()
        reqs.add_requirement("context:50k")
        reqs.add_requirement("tier:standard")
        
        assert len(reqs.requirements) == 2
        assert reqs.get_context_requirement() == 50000
        assert reqs.get_tier_requirement() == CostTier.STANDARD

    def test_add_preferences(self):
        """Test adding preferences."""
        reqs = ModelRequirements()
        reqs.add_preference("vendor:anthropic")
        
        assert len(reqs.preferences) == 1
        assert reqs.preferences[0].value == "anthropic"

    def test_set_policy(self):
        """Test setting resolution policy."""
        reqs = ModelRequirements()
        reqs.set_policy("cheapest")
        assert reqs.policy == ResolutionPolicy.CHEAPEST
        
        reqs.set_policy("best-fit")
        assert reqs.policy == ResolutionPolicy.BEST_FIT

    def test_to_hints_dict(self):
        """Test converting to hints dict for adapter."""
        reqs = ModelRequirements()
        reqs.add_requirement("context:50k")
        reqs.add_requirement("tier:standard")
        reqs.add_preference("vendor:anthropic")
        reqs.set_policy("fastest")
        
        hints = reqs.to_hints_dict()
        
        assert hints["min_context_tokens"] == 50000
        assert hints["tier"] == "standard"
        assert hints["prefer_vendor"] == "anthropic"
        assert hints["policy"] == "fastest"

    def test_is_empty(self):
        """Test empty requirements check."""
        reqs = ModelRequirements()
        assert reqs.is_empty()
        
        reqs.add_requirement("context:5k")
        assert not reqs.is_empty()


class TestContextSizeParsing:
    """Tests for context size string parsing."""

    def test_parse_k_suffix(self):
        """Test parsing k suffix."""
        assert _parse_context_size("5k") == 5000
        assert _parse_context_size("50k") == 50000
        assert _parse_context_size("128k") == 128000

    def test_parse_m_suffix(self):
        """Test parsing m suffix."""
        assert _parse_context_size("1m") == 1000000

    def test_parse_raw_number(self):
        """Test parsing raw number."""
        assert _parse_context_size("128000") == 128000


class TestResolveModel:
    """Tests for model resolution logic."""

    def test_empty_requirements_returns_fallback(self):
        """Test that empty requirements returns fallback."""
        reqs = ModelRequirements()
        result = resolve_model(reqs, fallback="gpt-4")
        assert result == "gpt-4"

    def test_context_requirement_filters(self):
        """Test context requirement filters models."""
        reqs = ModelRequirements()
        reqs.add_requirement("context:150k")  # Needs > 128k
        
        result = resolve_model(reqs)
        
        # Should pick a Claude model (200k context)
        assert result is not None
        assert "claude" in result

    def test_tier_requirement_filters(self):
        """Test tier requirement filters models."""
        reqs = ModelRequirements()
        reqs.add_requirement("tier:economy")
        
        result = resolve_model(reqs)
        
        # Should pick an economy model
        assert result in ["claude-haiku-3", "gpt-4o-mini"]

    def test_preference_affects_selection(self):
        """Test that preferences affect selection."""
        reqs = ModelRequirements()
        reqs.add_requirement("tier:standard")
        reqs.add_preference("vendor:anthropic")
        
        result = resolve_model(reqs)
        
        # Should prefer Anthropic
        assert result == "claude-sonnet-4"


class TestConversationFileParsing:
    """Tests for MODEL-REQUIRES directive parsing in ConversationFile."""

    def test_parse_model_requires(self):
        """Test parsing MODEL-REQUIRES directive."""
        from sdqctl.core.conversation import ConversationFile
        
        content = """MODEL-REQUIRES context:50k
MODEL-REQUIRES tier:standard
ADAPTER copilot
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        
        assert conv.model_requirements is not None
        assert len(conv.model_requirements.requirements) == 2
        assert conv.model_requirements.get_context_requirement() == 50000

    def test_parse_model_prefers(self):
        """Test parsing MODEL-PREFERS directive."""
        from sdqctl.core.conversation import ConversationFile
        
        content = """MODEL-PREFERS vendor:anthropic
MODEL-PREFERS family:claude
ADAPTER copilot
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        
        assert conv.model_requirements is not None
        assert len(conv.model_requirements.preferences) == 2

    def test_parse_model_policy(self):
        """Test parsing MODEL-POLICY directive."""
        from sdqctl.core.conversation import ConversationFile
        
        content = """MODEL-POLICY cheapest
ADAPTER copilot
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        
        assert conv.model_requirements is not None
        assert conv.model_requirements.policy == ResolutionPolicy.CHEAPEST

    def test_full_model_requirements_workflow(self):
        """Test complete workflow with all model requirement directives."""
        from sdqctl.core.conversation import ConversationFile
        
        content = """MODEL-REQUIRES context:50k
MODEL-REQUIRES capability:reasoning
MODEL-REQUIRES tier:standard
MODEL-PREFERS vendor:anthropic
MODEL-POLICY best-fit
ADAPTER copilot
PROMPT Analyze security vulnerabilities.
"""
        conv = ConversationFile.parse(content)
        
        reqs = conv.model_requirements
        assert reqs is not None
        assert reqs.get_context_requirement() == 50000
        assert reqs.get_capability_requirement() == CapabilityClass.REASONING
        assert reqs.get_tier_requirement() == CostTier.STANDARD
        assert len(reqs.preferences) == 1
        assert reqs.policy == ResolutionPolicy.BEST_FIT


class TestValidateCheckModel:
    """Tests for sdqctl validate --check-model CLI integration."""

    def test_validate_check_model_json_output(self, tmp_path):
        """Test that --check-model adds resolved_model to JSON output."""
        import json
        from click.testing import CliRunner
        from sdqctl.cli import cli
        
        conv_file = tmp_path / "test.conv"
        conv_file.write_text("""MODEL claude-sonnet-4.5
ADAPTER mock
MODEL-REQUIRES context:50k
MODEL-REQUIRES tier:standard
PROMPT Test workflow
""")
        
        runner = CliRunner()
        result = runner.invoke(cli, ["validate", str(conv_file), "--check-model", "--json"])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["valid"] is True
        assert data["model_requirements"] == 2
        assert data["resolved_model"] is not None

    def test_validate_shows_model_requirements_count(self, tmp_path):
        """Test that validate output includes model requirements count."""
        from click.testing import CliRunner
        from sdqctl.cli import cli
        
        conv_file = tmp_path / "test.conv"
        conv_file.write_text("""MODEL gpt-4
ADAPTER mock
MODEL-REQUIRES context:50k
MODEL-PREFERS vendor:openai
PROMPT Test.
""")
        
        runner = CliRunner()
        result = runner.invoke(cli, ["validate", str(conv_file)])
        
        assert result.exit_code == 0
        assert "Model requirements: 1" in result.output
