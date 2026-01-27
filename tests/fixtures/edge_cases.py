"""
Edge case fixtures for error handling tests.

Source: externals/rag-nightscout-ecosystem-alignment/docs/60-research/fixtures/edge-cases.js

These fixtures test edge cases that should be handled gracefully:
- Empty arrays
- Null/undefined fields
- Mixed validity batches
- Extended emulated temp basals
- Large profile JSON
"""

import pytest
from datetime import datetime, timezone


@pytest.fixture
def empty_array():
    """Empty array - should handle gracefully without error."""
    return []


@pytest.fixture
def single_item_array():
    """Single item array - boundary case."""
    return [
        {
            "type": "sgv",
            "sgv": 120,
            "date": int(datetime.now(timezone.utc).timestamp() * 1000),
            "direction": "Flat",
            "device": "test",
        }
    ]


@pytest.fixture
def null_fields_entry():
    """Entry with null/None fields - should handle gracefully."""
    return {
        "type": "sgv",
        "sgv": 120,
        "date": int(datetime.now(timezone.utc).timestamp() * 1000),
        "direction": None,
        "device": None,
        "noise": None,
        "filtered": None,
    }


@pytest.fixture
def mixed_validity_batch():
    """Batch with mixed isValid states - test filtering."""
    now = datetime.now(timezone.utc)
    base_time = int(now.timestamp() * 1000)
    return [
        {"type": "sgv", "sgv": 120, "date": base_time,
         "direction": "Flat", "isValid": True},
        {"type": "sgv", "sgv": 115, "date": base_time - 300000,
         "direction": "Flat", "isValid": False},
        {"type": "sgv", "sgv": 125, "date": base_time + 300000,
         "direction": "FortyFiveUp", "isValid": True},
    ]


@pytest.fixture
def extended_emulated_temp_basal():
    """Extended bolus emulated as temp basal - complex nested structure."""
    now = datetime.now(timezone.utc)
    return {
        "eventType": "Temp Basal",
        "created_at": now.isoformat(),
        "enteredBy": "openaps://AndroidAPS",
        "isValid": True,
        "duration": 3,
        "rate": 2.4391549295774646,
        "type": "FAKE_EXTENDED",
        "absolute": 2.4391549295774646,
        "pumpId": 4147,
        "pumpType": "ACCU_CHEK_INSIGHT_BLUETOOTH",
        "pumpSerial": "33013206",
        "extendedEmulated": {
            "created_at": now.isoformat(),
            "enteredBy": "openaps://AndroidAPS",
            "eventType": "Combo Bolus",
            "duration": 3,
            "splitNow": 0,
            "splitExt": 100,
            "enteredinsulin": 0.11,
            "relative": 1.8591549295774648,
            "isValid": True,
            "isEmulatingTempBasal": True,
            "pumpId": 4147,
            "pumpType": "ACCU_CHEK_INSIGHT_BLUETOOTH",
            "pumpSerial": "33013206",
        },
    }


@pytest.fixture
def large_profile_json():
    """Large profile with 24-hour schedules - tests size handling."""
    now = datetime.now(timezone.utc)
    
    # Generate 24-hour sensitivity schedule
    sens_schedule = [
        {
            "time": f"{str(i).zfill(2)}:00",
            "timeAsSeconds": i * 3600,
            "value": 40 + (i * 2 if i < 12 else (24 - i) * 2),
        }
        for i in range(24)
    ]
    
    # Generate 24-hour carb ratio schedule
    carbratio_schedule = [
        {
            "time": f"{str(i).zfill(2)}:00",
            "timeAsSeconds": i * 3600,
            "value": 8 + (i * 0.5 if i < 12 else (24 - i) * 0.5),
        }
        for i in range(24)
    ]
    
    # Generate 24-hour basal schedule
    basal_schedule = [
        {
            "time": f"{str(i).zfill(2)}:00",
            "timeAsSeconds": i * 3600,
            "value": 0.5 + (0.3 if 6 <= i <= 10 else 0) + (0.2 if 14 <= i <= 18 else 0),
        }
        for i in range(24)
    ]
    
    import json
    profile_json = json.dumps({
        "units": "mg/dl",
        "dia": 5,
        "timezone": "America/New_York",
        "sens": sens_schedule,
        "carbratio": carbratio_schedule,
        "basal": basal_schedule,
    })
    
    return {
        "eventType": "Profile Switch",
        "created_at": now.isoformat(),
        "enteredBy": "openaps://AndroidAPS",
        "isValid": True,
        "duration": 0,
        "profile": "ComplexProfile",
        "profileJson": profile_json,
    }


@pytest.fixture
def missing_required_fields():
    """Entry missing typically required fields - test validation."""
    return {
        "type": "sgv",
        # Missing: sgv, date, device
    }


@pytest.fixture
def future_timestamp():
    """Entry with future timestamp - test time validation."""
    future = datetime(2099, 1, 1, tzinfo=timezone.utc)
    return {
        "type": "sgv",
        "sgv": 120,
        "date": int(future.timestamp() * 1000),
        "dateString": future.isoformat(),
        "device": "test",
        "direction": "Flat",
    }


@pytest.fixture
def negative_values():
    """Entry with negative values - test value validation."""
    now = datetime.now(timezone.utc)
    return {
        "type": "sgv",
        "sgv": -50,  # Invalid negative glucose
        "date": int(now.timestamp() * 1000),
        "device": "test",
        "direction": "Flat",
    }


@pytest.fixture
def edge_case_collection(
    empty_array,
    single_item_array,
    null_fields_entry,
    mixed_validity_batch,
    extended_emulated_temp_basal,
    large_profile_json,
    missing_required_fields,
    future_timestamp,
    negative_values,
):
    """Collection of all edge case fixtures for comprehensive testing."""
    return {
        "empty_and_null": {
            "empty_array": empty_array,
            "single_item": single_item_array,
            "null_fields": null_fields_entry,
        },
        "validity": {
            "mixed_validity": mixed_validity_batch,
        },
        "complex_structures": {
            "extended_emulated": extended_emulated_temp_basal,
            "large_profile": large_profile_json,
        },
        "validation_failures": {
            "missing_required": missing_required_fields,
            "future_timestamp": future_timestamp,
            "negative_values": negative_values,
        },
    }
