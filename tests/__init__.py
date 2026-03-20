"""Initialize StoryFlow integration test suite."""

# This file ensures that pytest can discover tests in this directory
# and that pytest-homeassistant-custom-component works correctly.

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Automatically enable custom_components for all tests."""
    yield


# Optional: define constants or reusable fixtures for the whole suite
TEST_DOMAIN = "storyflow"
