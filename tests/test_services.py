"""Test StoryFlow services."""

import pytest
from unittest.mock import patch
import voluptuous as vol

from homeassistant.core import HomeAssistant
from custom_components.storyflow.services import (
    async_setup_services,
    async_unload_services,
    SERVICE_SET_STATE,
    SERVICE_ASSIGN,
    SERVICE_CLONE_STORY,
)
from custom_components.storyflow.const import DOMAIN, TASK_STATES


async def test_services_registered(hass: HomeAssistant):
    """Test that services are registered correctly."""
    await async_setup_services(hass)

    # Verify all three services are registered
    assert hass.services.has_service(DOMAIN, SERVICE_SET_STATE)
    assert hass.services.has_service(DOMAIN, SERVICE_ASSIGN)
    assert hass.services.has_service(DOMAIN, SERVICE_CLONE_STORY)


async def test_set_task_state_valid(hass: HomeAssistant):
    """Test set_task_state service with valid data."""
    await async_setup_services(hass)

    with patch("custom_components.storyflow.services._LOGGER") as mock_logger:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_STATE,
            {"task_id": "test_task_1", "new_state": "done"},
            blocking=True,
        )

        # Verify the service was called and logged
        mock_logger.info.assert_called_once()
        assert "test_task_1" in str(mock_logger.info.call_args)
        assert "done" in str(mock_logger.info.call_args)


async def test_set_task_state_invalid_state(hass: HomeAssistant):
    """Test set_task_state service rejects invalid state."""
    await async_setup_services(hass)

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_STATE,
            {"task_id": "test_task_1", "new_state": "invalid_state"},
            blocking=True,
        )


async def test_set_task_state_missing_fields(hass: HomeAssistant):
    """Test set_task_state service requires all fields."""
    await async_setup_services(hass)

    # Missing new_state
    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_STATE,
            {"task_id": "test_task_1"},
            blocking=True,
        )

    # Missing task_id
    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_STATE,
            {"new_state": "done"},
            blocking=True,
        )


async def test_assign_task_valid(hass: HomeAssistant):
    """Test assign_task service with valid data."""
    await async_setup_services(hass)

    with patch("custom_components.storyflow.services._LOGGER") as mock_logger:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_ASSIGN,
            {"task_id": "test_task_1", "person_id": "person.john"},
            blocking=True,
        )

        # Verify the service was called and logged
        mock_logger.info.assert_called_once()
        assert "test_task_1" in str(mock_logger.info.call_args)
        assert "person.john" in str(mock_logger.info.call_args)


async def test_assign_task_optional_person(hass: HomeAssistant):
    """Test assign_task service with optional person_id."""
    await async_setup_services(hass)

    with patch("custom_components.storyflow.services._LOGGER") as mock_logger:
        # person_id is optional, so this should work
        await hass.services.async_call(
            DOMAIN,
            SERVICE_ASSIGN,
            {"task_id": "test_task_1"},
            blocking=True,
        )

        # Verify the service was called
        mock_logger.info.assert_called_once()


async def test_clone_story_valid(hass: HomeAssistant):
    """Test clone_story service with valid data."""
    await async_setup_services(hass)

    with patch("custom_components.storyflow.services._LOGGER") as mock_logger:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_CLONE_STORY,
            {"story_id": "test_story", "new_story_name": "Cloned Story"},
            blocking=True,
        )

        # Verify the service was called and logged
        mock_logger.info.assert_called_once()
        assert "test_story" in str(mock_logger.info.call_args)
        assert "Cloned Story" in str(mock_logger.info.call_args)


async def test_clone_story_optional_name(hass: HomeAssistant):
    """Test clone_story service with optional new_story_name."""
    await async_setup_services(hass)

    with patch("custom_components.storyflow.services._LOGGER") as mock_logger:
        # new_story_name is optional
        await hass.services.async_call(
            DOMAIN,
            SERVICE_CLONE_STORY,
            {"story_id": "test_story"},
            blocking=True,
        )

        # Verify the service was called
        mock_logger.info.assert_called_once()


async def test_unload_services(hass: HomeAssistant):
    """Test that services are removed on unload."""
    await async_setup_services(hass)

    # Verify services are registered
    assert hass.services.has_service(DOMAIN, SERVICE_SET_STATE)
    assert hass.services.has_service(DOMAIN, SERVICE_ASSIGN)
    assert hass.services.has_service(DOMAIN, SERVICE_CLONE_STORY)

    # Unload services
    await async_unload_services(hass)

    # Verify services are removed
    assert not hass.services.has_service(DOMAIN, SERVICE_SET_STATE)
    assert not hass.services.has_service(DOMAIN, SERVICE_ASSIGN)
    assert not hass.services.has_service(DOMAIN, SERVICE_CLONE_STORY)


async def test_all_task_states_valid(hass: HomeAssistant):
    """Test that all defined task states are accepted."""
    await async_setup_services(hass)

    with patch("custom_components.storyflow.services._LOGGER"):
        for state in TASK_STATES:
            await hass.services.async_call(
                DOMAIN,
                SERVICE_SET_STATE,
                {"task_id": "test_task", "new_state": state},
                blocking=True,
            )
            # If we get here without exception, the state was valid
