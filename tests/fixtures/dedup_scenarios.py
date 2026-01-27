"""
Deduplication test scenarios - converted from JS research fixtures.

Source: externals/rag-nightscout-ecosystem-alignment/docs/60-research/fixtures/deduplication.js

These fixtures test deduplication strategies across AID systems:
- AAPS: pumpId + pumpSerial based deduplication
- Loop: syncIdentifier based deduplication
- Timestamp-based fallback strategies
"""

import pytest
from datetime import datetime, timezone


@pytest.fixture
def aaps_duplicate_pump_id():
    """Two AAPS entries with same pumpId - should be deduplicated."""
    now = datetime.now(timezone.utc)
    base = {
        "eventType": "Correction Bolus",
        "insulin": 0.25,
        "created_at": now.isoformat(),
        "date": int(now.timestamp() * 1000),
        "type": "SMB",
        "isValid": True,
        "isSMB": True,
        "pumpId": 4148,
        "pumpType": "ACCU_CHEK_INSIGHT_BLUETOOTH",
        "pumpSerial": "33013206",
        "app": "AAPS",
    }
    return {
        "first": base.copy(),
        "duplicate": base.copy(),
        "expected_dedup": True,
        "dedup_key": ("pumpId", "pumpSerial"),
    }


@pytest.fixture
def aaps_duplicate_sgv_entry():
    """Two AAPS SGV entries with same date - should be deduplicated."""
    fixed_date = 1705579200000  # 2024-01-18T12:00:00.000Z
    base = {
        "type": "sgv",
        "sgv": 120,
        "date": fixed_date,
        "dateString": "2024-01-18T12:00:00.000Z",
        "device": "AndroidAPS-DexcomG6",
        "direction": "Flat",
        "app": "AAPS",
    }
    return {
        "first": base.copy(),
        "duplicate": base.copy(),
        "expected_dedup": True,
        "dedup_key": ("date", "device"),
    }


@pytest.fixture
def loop_duplicate_sync_id():
    """Two Loop entries with same syncIdentifier - should be deduplicated."""
    base = {
        "eventType": "Carb Correction",
        "carbs": 15,
        "syncIdentifier": "loop-sync-abc123",
        "created_at": "2024-01-18T12:00:00.000Z",
        "enteredBy": "loop://iPhone",
    }
    return {
        "first": base.copy(),
        "duplicate": base.copy(),
        "expected_dedup": True,
        "dedup_key": ("syncIdentifier",),
    }


@pytest.fixture
def loop_duplicate_dose():
    """Two Loop dose entries with same syncIdentifier."""
    base = {
        "eventType": "Temp Basal",
        "duration": 30,
        "rate": 1.5,
        "absolute": 1.5,
        "syncIdentifier": "loop-dose-xyz789",
        "created_at": "2024-01-18T12:00:00.000Z",
        "enteredBy": "loop://iPhone",
    }
    return {
        "first": base.copy(),
        "duplicate": base.copy(),
        "expected_dedup": True,
        "dedup_key": ("syncIdentifier",),
    }


@pytest.fixture
def different_pump_ids():
    """Two AAPS entries with different pumpIds - should NOT be deduplicated."""
    now = datetime.now(timezone.utc)
    base = {
        "eventType": "Correction Bolus",
        "insulin": 0.25,
        "created_at": now.isoformat(),
        "type": "SMB",
        "isValid": True,
        "pumpType": "ACCU_CHEK_INSIGHT_BLUETOOTH",
        "pumpSerial": "33013206",
        "app": "AAPS",
    }
    first = base.copy()
    first["pumpId"] = 4148
    second = base.copy()
    second["pumpId"] = 4149
    return {
        "first": first,
        "second": second,
        "expected_dedup": False,
        "reason": "Different pumpId values",
    }


@pytest.fixture
def dedup_scenario_collection(
    aaps_duplicate_pump_id,
    aaps_duplicate_sgv_entry,
    loop_duplicate_sync_id,
    loop_duplicate_dose,
    different_pump_ids,
):
    """Collection of all deduplication test scenarios."""
    return {
        "should_dedup": [
            aaps_duplicate_pump_id,
            aaps_duplicate_sgv_entry,
            loop_duplicate_sync_id,
            loop_duplicate_dose,
        ],
        "should_not_dedup": [
            different_pump_ids,
        ],
    }
