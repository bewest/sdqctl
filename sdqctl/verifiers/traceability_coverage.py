"""
Traceability coverage calculation utilities.

This module is separate from verifiers/traceability.py to:
1. Reduce traceability.py line count
2. Enable standalone coverage calculation
3. Improve testability of coverage metrics
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .traceability import TraceArtifact


def calculate_coverage(
    artifacts: dict[str, "TraceArtifact"],
    artifacts_by_type: dict[str, list[str]],
) -> dict[str, float]:
    """Calculate traceability coverage metrics.

    Returns a dict with:
    - total_* counts for each artifact type
    - *_to_* percentages for trace chain links
    - overall: average of all trace metrics
    """
    coverage: dict[str, float] = {
        # STPA artifacts
        "total_losses": len(artifacts_by_type.get("LOSS", [])),
        "total_hazards": len(artifacts_by_type.get("HAZ", [])),
        "total_ucas": len(artifacts_by_type.get("UCA", [])),
        "total_scs": len(artifacts_by_type.get("SC", [])),
        # Requirements/specifications
        "total_reqs": len(artifacts_by_type.get("REQ", [])),
        "total_specs": len(artifacts_by_type.get("SPEC", [])),
        "total_tests": len(artifacts_by_type.get("TEST", [])),
        # Development artifacts
        "total_bugs": len(artifacts_by_type.get("BUG", [])),
        "total_props": len(artifacts_by_type.get("PROP", [])),
        "total_quirks": len(artifacts_by_type.get("Q", [])),
    }

    # LOSS → HAZ coverage
    losses_with_haz = 0
    for loss_id in artifacts_by_type.get("LOSS", []):
        loss = artifacts[loss_id]
        has_haz = any(_is_type(lid, "HAZ", artifacts) for lid in loss.links_to)
        has_haz = has_haz or any(
            _is_type(lid, "HAZ", artifacts) for lid in loss.linked_from
        )
        if has_haz:
            losses_with_haz += 1

    if coverage["total_losses"] > 0:
        coverage["loss_to_haz"] = losses_with_haz / coverage["total_losses"] * 100
    else:
        coverage["loss_to_haz"] = 0.0

    # HAZ → UCA coverage
    hazards_with_uca = 0
    for haz_id in artifacts_by_type.get("HAZ", []):
        haz = artifacts[haz_id]
        has_uca = any(_is_type(lid, "UCA", artifacts) for lid in haz.links_to)
        has_uca = has_uca or any(
            _is_type(lid, "UCA", artifacts) for lid in haz.linked_from
        )
        if has_uca:
            hazards_with_uca += 1

    if coverage["total_hazards"] > 0:
        coverage["haz_to_uca"] = hazards_with_uca / coverage["total_hazards"] * 100
    else:
        coverage["haz_to_uca"] = 0.0

    # UCA → SC coverage
    ucas_with_sc = 0
    for uca_id in artifacts_by_type.get("UCA", []):
        uca = artifacts[uca_id]
        if any(_is_type(lid, "SC", artifacts) for lid in uca.links_to):
            ucas_with_sc += 1

    if coverage["total_ucas"] > 0:
        coverage["uca_to_sc"] = ucas_with_sc / coverage["total_ucas"] * 100
    else:
        coverage["uca_to_sc"] = 0.0

    # REQ → SPEC coverage
    reqs_with_spec = 0
    for req_id in artifacts_by_type.get("REQ", []):
        req = artifacts[req_id]
        has_spec = any(_is_type(lid, "SPEC", artifacts) for lid in req.links_to)
        has_spec = has_spec or any(
            _is_type(lid, "SPEC", artifacts) for lid in req.linked_from
        )
        if has_spec:
            reqs_with_spec += 1

    if coverage["total_reqs"] > 0:
        coverage["req_to_spec"] = reqs_with_spec / coverage["total_reqs"] * 100
    else:
        coverage["req_to_spec"] = 0.0

    # SPEC → TEST coverage
    specs_with_test = 0
    for spec_id in artifacts_by_type.get("SPEC", []):
        spec = artifacts[spec_id]
        has_test = any(_is_type(lid, "TEST", artifacts) for lid in spec.links_to)
        has_test = has_test or any(
            _is_type(lid, "TEST", artifacts) for lid in spec.linked_from
        )
        if has_test:
            specs_with_test += 1

    if coverage["total_specs"] > 0:
        coverage["spec_to_test"] = specs_with_test / coverage["total_specs"] * 100
    else:
        coverage["spec_to_test"] = 0.0

    # Overall coverage (average of available metrics)
    metrics = [v for k, v in coverage.items() if "_to_" in k]
    if metrics:
        valid_metrics = [m for m in metrics if isinstance(m, (int, float))]
        coverage["overall"] = sum(valid_metrics) / len(metrics)
    else:
        coverage["overall"] = 0.0

    return coverage


def _is_type(art_id: str, art_type: str, artifacts: dict[str, "TraceArtifact"]) -> bool:
    """Check if an artifact ID is of a given type."""
    if art_id in artifacts:
        return artifacts[art_id].type == art_type
    # Infer from ID prefix
    return art_id.startswith(art_type + "-")
