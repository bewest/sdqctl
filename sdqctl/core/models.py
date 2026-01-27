"""
Model capability registry and resolution logic.

Provides abstract model selection based on capability requirements
rather than explicit model names. Authors describe what they need
(context window size, cost tier, latency), and the system resolves
this to an appropriate concrete model.

See MODEL-REQUIREMENTS.md for full proposal.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml


class CostTier(Enum):
    """Cost tier for model selection."""
    ECONOMY = "economy"     # Cheapest available (e.g., haiku, mini)
    STANDARD = "standard"   # Balanced cost/capability (e.g., sonnet, gpt-4)
    PREMIUM = "premium"     # Best available (e.g., opus, o1)


class SpeedTier(Enum):
    """Speed/latency tier for model selection."""
    FAST = "fast"           # Prioritize low latency
    STANDARD = "standard"   # Default latency acceptable
    DELIBERATE = "deliberate"  # Extended thinking OK


class CapabilityClass(Enum):
    """Capability class for model selection."""
    CODE = "code"           # Code-optimized
    REASONING = "reasoning" # Strong reasoning
    GENERAL = "general"     # General purpose (default)


class ResolutionPolicy(Enum):
    """Policy for resolving model requirements to concrete model."""
    CHEAPEST = "cheapest"           # Among matching, pick cheapest
    FASTEST = "fastest"             # Among matching, pick fastest
    BEST_FIT = "best-fit"           # Balance all requirements (default)
    OPERATOR_DEFAULT = "operator-default"  # Defer to operator config


@dataclass
class ModelRequirement:
    """A single model requirement (e.g., context:50k)."""

    dimension: str  # context, tier, speed, capability
    value: str      # 50k, standard, fast, reasoning

    @classmethod
    def parse(cls, spec: str) -> "ModelRequirement":
        """Parse a requirement spec like 'context:50k' or 'tier:standard'.

        Args:
            spec: Requirement specification string

        Returns:
            ModelRequirement with parsed dimension and value

        Raises:
            ValueError: If spec is not in valid format
        """
        if ":" not in spec:
            raise ValueError(f"Invalid requirement format: {spec!r}. Expected 'dimension:value'")

        parts = spec.split(":", 1)
        dimension = parts[0].strip().lower()
        value = parts[1].strip().lower()

        # Validate known dimensions
        valid_dimensions = {"context", "tier", "speed", "capability", "vendor", "family"}
        if dimension not in valid_dimensions:
            raise ValueError(
                f"Unknown requirement dimension: {dimension!r}. "
                f"Valid dimensions: {', '.join(sorted(valid_dimensions))}"
            )

        return cls(dimension=dimension, value=value)

    def __str__(self) -> str:
        return f"{self.dimension}:{self.value}"


@dataclass
class ModelPreference:
    """A soft model preference (hint, not constraint)."""

    dimension: str  # vendor, family
    value: str      # anthropic, openai, claude, gpt

    @classmethod
    def parse(cls, spec: str) -> "ModelPreference":
        """Parse a preference spec like 'vendor:anthropic'.

        Args:
            spec: Preference specification string

        Returns:
            ModelPreference with parsed dimension and value
        """
        if ":" not in spec:
            raise ValueError(f"Invalid preference format: {spec!r}. Expected 'dimension:value'")

        parts = spec.split(":", 1)
        dimension = parts[0].strip().lower()
        value = parts[1].strip().lower()

        # Validate preference dimensions
        valid_dimensions = {"vendor", "family"}
        if dimension not in valid_dimensions:
            raise ValueError(
                f"Unknown preference dimension: {dimension!r}. "
                f"Valid dimensions: {', '.join(sorted(valid_dimensions))}"
            )

        return cls(dimension=dimension, value=value)

    def __str__(self) -> str:
        return f"{self.dimension}:{self.value}"


@dataclass
class ModelRequirements:
    """Collection of model requirements, preferences, and policy."""

    requirements: list[ModelRequirement] = field(default_factory=list)
    preferences: list[ModelPreference] = field(default_factory=list)
    policy: ResolutionPolicy = ResolutionPolicy.BEST_FIT

    def add_requirement(self, spec: str) -> None:
        """Add a requirement from a spec string."""
        self.requirements.append(ModelRequirement.parse(spec))

    def add_preference(self, spec: str) -> None:
        """Add a preference from a spec string."""
        self.preferences.append(ModelPreference.parse(spec))

    def set_policy(self, policy_str: str) -> None:
        """Set resolution policy from string."""
        policy_str = policy_str.strip().lower()

        # Normalize hyphenated names
        policy_map = {
            "cheapest": ResolutionPolicy.CHEAPEST,
            "fastest": ResolutionPolicy.FASTEST,
            "best-fit": ResolutionPolicy.BEST_FIT,
            "bestfit": ResolutionPolicy.BEST_FIT,
            "operator-default": ResolutionPolicy.OPERATOR_DEFAULT,
            "operatordefault": ResolutionPolicy.OPERATOR_DEFAULT,
        }

        if policy_str not in policy_map:
            valid = ["cheapest", "fastest", "best-fit", "operator-default"]
            raise ValueError(
                f"Unknown resolution policy: {policy_str!r}. "
                f"Valid policies: {', '.join(valid)}"
            )

        self.policy = policy_map[policy_str]

    def get_context_requirement(self) -> Optional[int]:
        """Get context window requirement in tokens, if specified.

        Parses values like '5k', '50k', '100k' to token counts.
        """
        for req in self.requirements:
            if req.dimension == "context":
                return _parse_context_size(req.value)
        return None

    def get_tier_requirement(self) -> Optional[CostTier]:
        """Get cost tier requirement, if specified."""
        for req in self.requirements:
            if req.dimension == "tier":
                try:
                    return CostTier(req.value)
                except ValueError:
                    pass
        return None

    def get_speed_requirement(self) -> Optional[SpeedTier]:
        """Get speed tier requirement, if specified."""
        for req in self.requirements:
            if req.dimension == "speed":
                try:
                    return SpeedTier(req.value)
                except ValueError:
                    pass
        return None

    def get_capability_requirement(self) -> Optional[CapabilityClass]:
        """Get capability class requirement, if specified."""
        for req in self.requirements:
            if req.dimension == "capability":
                try:
                    return CapabilityClass(req.value)
                except ValueError:
                    pass
        return None

    def to_hints_dict(self) -> dict:
        """Convert requirements to hints dict for adapter.

        Returns a dict suitable for passing to adapter.select_model().
        """
        hints = {}

        # Requirements (hard constraints)
        context = self.get_context_requirement()
        if context:
            hints["min_context_tokens"] = context

        tier = self.get_tier_requirement()
        if tier:
            hints["tier"] = tier.value

        speed = self.get_speed_requirement()
        if speed:
            hints["speed"] = speed.value

        capability = self.get_capability_requirement()
        if capability:
            hints["capability"] = capability.value

        # Preferences (soft hints)
        for pref in self.preferences:
            hints[f"prefer_{pref.dimension}"] = pref.value

        # Policy
        hints["policy"] = self.policy.value

        return hints

    def is_empty(self) -> bool:
        """Check if no requirements or preferences are set."""
        return (
            not self.requirements
            and not self.preferences
            and self.policy == ResolutionPolicy.BEST_FIT
        )

    def __str__(self) -> str:
        parts = []
        for req in self.requirements:
            parts.append(f"requires {req}")
        for pref in self.preferences:
            parts.append(f"prefers {pref}")
        if self.policy != ResolutionPolicy.BEST_FIT:
            parts.append(f"policy={self.policy.value}")
        return ", ".join(parts) if parts else "(no requirements)"


def _parse_context_size(value: str) -> int:
    """Parse context size string to token count.

    Supports formats like:
    - '5k' -> 5000
    - '50k' -> 50000
    - '100k' -> 100000
    - '1m' -> 1000000
    - '128000' -> 128000 (raw number)

    Args:
        value: Context size string

    Returns:
        Token count as integer
    """
    value = value.strip().lower()

    if value.endswith("k"):
        return int(float(value[:-1]) * 1000)
    elif value.endswith("m"):
        return int(float(value[:-1]) * 1000000)
    else:
        return int(value)


# ============================================================================
# Operator Configuration
# ============================================================================

# Environment variable prefix for model overrides
ENV_PREFIX = "SDQCTL_MODEL_"

# Cached operator config
_operator_config: Optional[dict] = None


def _get_config_paths() -> list[Optional[Path]]:
    """Get config file search paths (evaluated at call time)."""
    env_config = os.environ.get("SDQCTL_CONFIG")
    return [
        Path(env_config) / "models.yaml" if env_config else None,
        Path.home() / ".config" / "sdqctl" / "models.yaml",
        Path.home() / ".sdqctl" / "models.yaml",
    ]


def _load_operator_config() -> dict:
    """Load operator configuration from file and environment.

    Config file format (~/.config/sdqctl/models.yaml):

        default_model: claude-sonnet-4

        models:
          my-custom-model:
            context: 100000
            tier: standard
            speed: fast
            capability: code
            vendor: internal
            family: custom

        aliases:
          fast: gpt-4o-mini
          smart: claude-opus-4
          cheap: claude-haiku-3

    Environment overrides:
        SDQCTL_MODEL_DEFAULT=claude-sonnet-4
        SDQCTL_MODEL_ALIAS_FAST=gpt-4-turbo

    Returns:
        Dict with 'default_model', 'models', 'aliases' keys
    """
    global _operator_config

    if _operator_config is not None:
        return _operator_config

    config: dict = {
        "default_model": None,
        "models": {},
        "aliases": {},
    }

    # Load from config file
    for path in _get_config_paths():
        if path and path.exists():
            try:
                with open(path) as f:
                    file_config = yaml.safe_load(f) or {}

                if "default_model" in file_config:
                    config["default_model"] = file_config["default_model"]
                if "models" in file_config:
                    config["models"].update(file_config["models"])
                if "aliases" in file_config:
                    config["aliases"].update(file_config["aliases"])
                break  # Use first found config
            except Exception:
                pass  # Silently ignore malformed config

    # Environment overrides
    env_default = os.environ.get(f"{ENV_PREFIX}DEFAULT")
    if env_default:
        config["default_model"] = env_default

    # Scan for SDQCTL_MODEL_ALIAS_* environment variables
    for key, value in os.environ.items():
        if key.startswith(f"{ENV_PREFIX}ALIAS_"):
            alias_name = key[len(f"{ENV_PREFIX}ALIAS_"):].lower()
            config["aliases"][alias_name] = value

    _operator_config = config
    return config


def get_operator_default_model() -> Optional[str]:
    """Get operator-configured default model.

    Returns:
        Model name or None if not configured
    """
    config = _load_operator_config()
    return config.get("default_model")


def resolve_model_alias(name: str) -> str:
    """Resolve a model alias to concrete model name.

    Args:
        name: Model name or alias

    Returns:
        Resolved model name (original if not an alias)
    """
    config = _load_operator_config()
    return config.get("aliases", {}).get(name.lower(), name)


def get_operator_models() -> dict:
    """Get operator-defined custom models.

    Returns:
        Dict mapping model name to capabilities
    """
    config = _load_operator_config()
    result = {}

    for name, caps in config.get("models", {}).items():
        # Convert string values to enums where needed
        parsed = {"vendor": "operator", "family": "custom"}

        if "context" in caps:
            parsed["context"] = _parse_context_size(str(caps["context"]))

        if "tier" in caps:
            tier_map = {
                "economy": CostTier.ECONOMY,
                "standard": CostTier.STANDARD,
                "premium": CostTier.PREMIUM,
            }
            parsed["tier"] = tier_map.get(caps["tier"].lower(), CostTier.STANDARD)

        if "speed" in caps:
            speed_map = {
                "fast": SpeedTier.FAST,
                "standard": SpeedTier.STANDARD,
                "deliberate": SpeedTier.DELIBERATE,
            }
            parsed["speed"] = speed_map.get(caps["speed"].lower(), SpeedTier.STANDARD)

        if "capability" in caps:
            cap_map = {
                "code": CapabilityClass.CODE,
                "reasoning": CapabilityClass.REASONING,
                "general": CapabilityClass.GENERAL,
            }
            parsed["capability"] = cap_map.get(caps["capability"].lower(), CapabilityClass.GENERAL)

        if "vendor" in caps:
            parsed["vendor"] = caps["vendor"]
        if "family" in caps:
            parsed["family"] = caps["family"]

        result[name] = parsed

    return result


def get_effective_capabilities() -> dict:
    """Get merged model capabilities (built-in + operator).

    Operator models override built-in models with same name.

    Returns:
        Dict mapping model name to capabilities
    """
    result = dict(MODEL_CAPABILITIES)
    result.update(get_operator_models())
    return result


def reset_operator_config() -> None:
    """Reset cached operator config (for testing)."""
    global _operator_config
    _operator_config = None


# Known model capabilities (static registry)
# This can be extended by operator configuration
MODEL_CAPABILITIES = {
    # Anthropic
    "claude-opus-4": {
        "context": 200000,
        "tier": CostTier.PREMIUM,
        "speed": SpeedTier.DELIBERATE,
        "capability": CapabilityClass.REASONING,
        "vendor": "anthropic",
        "family": "claude",
    },
    "claude-sonnet-4": {
        "context": 200000,
        "tier": CostTier.STANDARD,
        "speed": SpeedTier.STANDARD,
        "capability": CapabilityClass.GENERAL,
        "vendor": "anthropic",
        "family": "claude",
    },
    "claude-haiku-3": {
        "context": 200000,
        "tier": CostTier.ECONOMY,
        "speed": SpeedTier.FAST,
        "capability": CapabilityClass.GENERAL,
        "vendor": "anthropic",
        "family": "claude",
    },
    # OpenAI
    "gpt-4": {
        "context": 128000,
        "tier": CostTier.STANDARD,
        "speed": SpeedTier.STANDARD,
        "capability": CapabilityClass.GENERAL,
        "vendor": "openai",
        "family": "gpt",
    },
    "gpt-4-turbo": {
        "context": 128000,
        "tier": CostTier.STANDARD,
        "speed": SpeedTier.FAST,
        "capability": CapabilityClass.GENERAL,
        "vendor": "openai",
        "family": "gpt",
    },
    "gpt-4o": {
        "context": 128000,
        "tier": CostTier.STANDARD,
        "speed": SpeedTier.FAST,
        "capability": CapabilityClass.GENERAL,
        "vendor": "openai",
        "family": "gpt",
    },
    "gpt-4o-mini": {
        "context": 128000,
        "tier": CostTier.ECONOMY,
        "speed": SpeedTier.FAST,
        "capability": CapabilityClass.GENERAL,
        "vendor": "openai",
        "family": "gpt",
    },
    "o1": {
        "context": 128000,
        "tier": CostTier.PREMIUM,
        "speed": SpeedTier.DELIBERATE,
        "capability": CapabilityClass.REASONING,
        "vendor": "openai",
        "family": "gpt",
    },
}


def resolve_model(
    requirements: ModelRequirements,
    available_models: Optional[list[str]] = None,
    fallback: Optional[str] = None,
) -> Optional[str]:
    """Resolve model requirements to a concrete model name.

    This is the basic resolution logic. Adapters may implement
    their own resolution using their available models list.

    Resolution order:
    1. Check operator aliases for fallback model
    2. If OPERATOR_DEFAULT policy, use operator's default model
    3. Filter available models by requirements
    4. Apply preferences and policy to select best match

    Args:
        requirements: Model requirements to satisfy
        available_models: List of available model names (defaults to registry keys)
        fallback: Fallback model if no match found

    Returns:
        Model name that satisfies requirements, or fallback/None
    """
    # Resolve fallback alias
    if fallback:
        fallback = resolve_model_alias(fallback)

    # Handle OPERATOR_DEFAULT policy
    if requirements.policy == ResolutionPolicy.OPERATOR_DEFAULT:
        operator_default = get_operator_default_model()
        if operator_default:
            return resolve_model_alias(operator_default)
        # Fall through to normal resolution if no operator default

    if requirements.is_empty():
        return fallback

    # Get merged capabilities (built-in + operator models)
    effective_caps = get_effective_capabilities()

    if available_models is None:
        available_models = list(effective_caps.keys())

    # Filter models by requirements
    candidates = []
    for model in available_models:
        if model not in effective_caps:
            continue

        caps = effective_caps[model]

        # Check hard requirements
        context_req = requirements.get_context_requirement()
        if context_req and caps.get("context", 0) < context_req:
            continue

        tier_req = requirements.get_tier_requirement()
        if tier_req and caps.get("tier") != tier_req:
            continue

        speed_req = requirements.get_speed_requirement()
        if speed_req and caps.get("speed") != speed_req:
            continue

        capability_req = requirements.get_capability_requirement()
        if capability_req and caps.get("capability") != capability_req:
            continue

        candidates.append(model)

    if not candidates:
        return fallback

    # Apply preferences to score candidates
    scored = []
    for model in candidates:
        caps = effective_caps[model]
        score = 0

        for pref in requirements.preferences:
            if pref.dimension == "vendor" and caps.get("vendor") == pref.value:
                score += 10
            elif pref.dimension == "family" and caps.get("family") == pref.value:
                score += 5

        scored.append((score, model))

    # Sort by score (descending) and apply policy
    scored.sort(key=lambda x: (-x[0], x[1]))

    if requirements.policy == ResolutionPolicy.CHEAPEST:
        # Among top-scored, pick economy tier if available
        top_score = scored[0][0]
        top_candidates = [m for s, m in scored if s == top_score]
        for model in top_candidates:
            if effective_caps[model].get("tier") == CostTier.ECONOMY:
                return model
        return top_candidates[0]

    elif requirements.policy == ResolutionPolicy.FASTEST:
        # Among top-scored, pick fast speed if available
        top_score = scored[0][0]
        top_candidates = [m for s, m in scored if s == top_score]
        for model in top_candidates:
            if effective_caps[model].get("speed") == SpeedTier.FAST:
                return model
        return top_candidates[0]

    else:
        # BEST_FIT: return highest scored
        return scored[0][1]
