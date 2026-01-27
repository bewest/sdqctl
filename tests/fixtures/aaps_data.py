"""
AAPS upload pattern fixtures - converted from JS research fixtures.

Source: externals/rag-nightscout-ecosystem-alignment/docs/60-research/fixtures/aaps-single-doc.js

These fixtures represent real-world AAPS (AndroidAPS) data upload patterns
to Nightscout, useful for testing context loading, schema validation,
and workflow execution.
"""

import pytest
from datetime import datetime, timezone


@pytest.fixture
def aaps_sgv_entry():
    """AAPS-style SGV (sensor glucose value) entry."""
    now = datetime.now(timezone.utc)
    return {
        "type": "sgv",
        "sgv": 120,
        "date": int(now.timestamp() * 1000),
        "dateString": now.isoformat(),
        "device": "AndroidAPS-DexcomG6",
        "direction": "Flat",
        "app": "AAPS",
        "utcOffset": 120,
    }


@pytest.fixture
def aaps_smb_bolus():
    """AAPS SMB (Super Micro Bolus) correction entry."""
    now = datetime.now(timezone.utc)
    return {
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


@pytest.fixture
def aaps_meal_bolus():
    """AAPS meal bolus with carbs entry."""
    now = datetime.now(timezone.utc)
    return {
        "eventType": "Meal Bolus",
        "insulin": 8.1,
        "carbs": 45,
        "created_at": now.isoformat(),
        "date": int(now.timestamp() * 1000),
        "type": "NORMAL",
        "isValid": True,
        "isSMB": False,
        "pumpId": 4102,
        "pumpType": "ACCU_CHEK_INSIGHT_BLUETOOTH",
        "pumpSerial": "33013206",
        "app": "AAPS",
    }


@pytest.fixture
def aaps_temp_basal():
    """AAPS temporary basal rate entry."""
    now = datetime.now(timezone.utc)
    return {
        "eventType": "Temp Basal",
        "created_at": now.isoformat(),
        "enteredBy": "openaps://AndroidAPS",
        "isValid": True,
        "duration": 60,
        "rate": 0,
        "type": "NORMAL",
        "absolute": 0,
        "pumpId": 284835,
        "pumpType": "ACCU_CHEK_INSIGHT_BLUETOOTH",
        "pumpSerial": "33013206",
        "app": "AAPS",
    }


@pytest.fixture
def aaps_carb_correction():
    """AAPS carb correction (rescue carbs) entry."""
    now = datetime.now(timezone.utc)
    return {
        "eventType": "Carb Correction",
        "carbs": 15,
        "created_at": now.isoformat(),
        "isValid": True,
        "date": int(now.timestamp() * 1000),
        "app": "AAPS",
    }


@pytest.fixture
def aaps_temporary_target():
    """AAPS temporary target entry."""
    now = datetime.now(timezone.utc)
    return {
        "eventType": "Temporary Target",
        "duration": 60,
        "isValid": True,
        "created_at": now.isoformat(),
        "enteredBy": "AndroidAPS",
        "reason": "Eating Soon",
        "targetBottom": 80,
        "targetTop": 80,
        "units": "mg/dl",
        "app": "AAPS",
    }


@pytest.fixture
def aaps_full_upload_batch(
    aaps_sgv_entry,
    aaps_smb_bolus,
    aaps_meal_bolus,
    aaps_temp_basal,
    aaps_carb_correction,
    aaps_temporary_target,
):
    """Complete AAPS upload batch with all entry types."""
    return {
        "sgv": aaps_sgv_entry,
        "smb_bolus": aaps_smb_bolus,
        "meal_bolus": aaps_meal_bolus,
        "temp_basal": aaps_temp_basal,
        "carb_correction": aaps_carb_correction,
        "temporary_target": aaps_temporary_target,
    }
