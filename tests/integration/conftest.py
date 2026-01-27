"""Pytest configuration for integration tests.

All tests in this directory are automatically marked as integration tests.
"""

import pytest


def pytest_collection_modifyitems(items):
    """Mark all tests in integration directory as integration tests."""
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
