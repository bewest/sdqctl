"""
Fixtures package for sdqctl testing.

Provides pytest fixtures converted from rag-nightscout-ecosystem-alignment
research fixtures for testing against real-world AID (Automated Insulin Delivery)
system data patterns.

Fixture modules:
- aaps_data: AAPS (AndroidAPS) upload patterns
- dedup_scenarios: Deduplication test scenarios
- edge_cases: Edge case and error handling fixtures

Usage:
    from sdqctl.tests.fixtures.aaps_data import aaps_sgv_entry
    
    def test_context_loading(aaps_sgv_entry):
        assert aaps_sgv_entry["type"] == "sgv"
"""

from .aaps_data import *
from .dedup_scenarios import *
from .edge_cases import *
