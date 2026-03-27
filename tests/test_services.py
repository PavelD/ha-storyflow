"""Test StoryFlow services."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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


@pytest.fixture
def mock_task_entity():
    """Create a mock task entity."""
    entity = MagicMock()
    entity.task_id = "test_task_1"
    entity.story_id = "test_story"
    entity._state = "todo"
    entity.async_update_state = AsyncMock()
    entity.async_update_assignment = AsyncMock()
    entity.async_write_ha_state = MagicMock()

    # Mock state property
    type(entity).state = property(lambda self: self._state)

    return entity


@pytest.fixture
def mock_storage_handler():
    """Create a mock storage handler."""
    storage = MagicMock()
    storage.async_update_task = AsyncMock()
    storage.async_load_all_stories = AsyncMock(return_value={})
    return storage


async def test_services_registered(hass: HomeAssistant):
    """Test that services are registered correctly."""
    # Initialize domain data
    hass.data[DOMAIN] = {"service_ref_count": 0}

    await async_setup_services(hass)

    # Verify all three services are registered
    assert hass.services.has_service(DOMAIN, SERVICE_SET_STATE)
    assert hass.services.has_service(DOMAIN, SERVICE_ASSIGN)
    assert hass.services.has_service(DOMAIN, SERVICE_CLONE_STORY)


async def test_set_task_state_updates_entity(hass: HomeAssistant, mock_task_entity):
    """Test that set_task_state actually updates the entity."""
    # Setup
    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {"test_task_1": mock_task_entity},
    }
    await async_setup_services(hass)

    # Call service
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_STATE,
        {"task_id": "test_task_1", "new_state": "done"},
        blocking=True,
    )

    # Verify entity was updated
    mock_task_entity.async_update_state.assert_called_once_with("done")


async def test_set_task_state_task_not_found(hass: HomeAssistant):
    """Test set_task_state service with non-existent task."""
    # Setup with empty task registry
    hass.data[DOMAIN] = {"service_ref_count": 0, "task_entities": {}}
    await async_setup_services(hass)

    # Call service with non-existent task
    with pytest.raises(ValueError, match="Task 'nonexistent_task' not found"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_STATE,
            {"task_id": "nonexistent_task", "new_state": "done"},
            blocking=True,
        )


async def test_set_task_state_storage_failure(hass: HomeAssistant, mock_task_entity):
    """Test set_task_state handles storage failure gracefully."""
    # Setup entity that raises ValueError on update
    mock_task_entity.async_update_state.side_effect = ValueError("Storage error")

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {"test_task_1": mock_task_entity},
    }
    await async_setup_services(hass)

    # Call service should propagate the error
    with pytest.raises(ValueError, match="Storage error"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_STATE,
            {"task_id": "test_task_1", "new_state": "done"},
            blocking=True,
        )


async def test_set_task_state_all_valid_states(hass: HomeAssistant, mock_task_entity):
    """Test set_task_state with all valid task states."""
    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {"test_task_1": mock_task_entity},
    }
    await async_setup_services(hass)

    # Test each valid state
    for state in TASK_STATES:
        mock_task_entity.async_update_state.reset_mock()

        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_STATE,
            {"task_id": "test_task_1", "new_state": state},
            blocking=True,
        )

        mock_task_entity.async_update_state.assert_called_once_with(state)


async def test_set_task_state_multiple_stories(hass: HomeAssistant, mock_task_entity):
    """Test set_task_state works across multiple stories."""
    # Create tasks from different stories
    task1 = MagicMock()
    task1.task_id = "story1_task_0"
    task1.story_id = "story1"
    task1.async_update_state = AsyncMock()

    task2 = MagicMock()
    task2.task_id = "story2_task_0"
    task2.story_id = "story2"
    task2.async_update_state = AsyncMock()

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {
            "story1_task_0": task1,
            "story2_task_0": task2,
        },
    }
    await async_setup_services(hass)

    # Update task from story1
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_STATE,
        {"task_id": "story1_task_0", "new_state": "done"},
        blocking=True,
    )

    task1.async_update_state.assert_called_once_with("done")
    task2.async_update_state.assert_not_called()

    # Update task from story2
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_STATE,
        {"task_id": "story2_task_0", "new_state": "progress"},
        blocking=True,
    )

    task2.async_update_state.assert_called_once_with("progress")


async def test_set_task_state_logging(hass: HomeAssistant, mock_task_entity):
    """Test that set_task_state logs appropriately."""
    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {"test_task_1": mock_task_entity},
    }
    await async_setup_services(hass)

    with patch("custom_components.storyflow.services._LOGGER") as mock_logger:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_STATE,
            {"task_id": "test_task_1", "new_state": "done"},
            blocking=True,
        )

        # Verify debug and info logging
        mock_logger.debug.assert_called_once()
        mock_logger.info.assert_called_once()

        # Verify log messages contain task_id and state
        debug_call = str(mock_logger.debug.call_args)
        assert "test_task_1" in debug_call
        assert "done" in debug_call

        info_call = str(mock_logger.info.call_args)
        assert "test_task_1" in info_call
        assert "done" in info_call


async def test_set_task_state_invalid_state(hass: HomeAssistant):
    """Test set_task_state service rejects invalid state."""
    hass.data[DOMAIN] = {"service_ref_count": 0}
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
    hass.data[DOMAIN] = {"service_ref_count": 0}
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
    hass.data[DOMAIN] = {"service_ref_count": 0}
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
    hass.data[DOMAIN] = {"service_ref_count": 0}
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
    hass.data[DOMAIN] = {"service_ref_count": 0}
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
    hass.data[DOMAIN] = {"service_ref_count": 0}
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
    hass.data[DOMAIN] = {"service_ref_count": 0}
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


async def test_all_task_states_valid(hass: HomeAssistant, mock_task_entity):
    """Test that all defined task states are accepted."""
    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {"test_task": mock_task_entity},
    }
    await async_setup_services(hass)

    for state in TASK_STATES:
        mock_task_entity.async_update_state.reset_mock()

        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_STATE,
            {"task_id": "test_task", "new_state": state},
            blocking=True,
        )

        # Verify the state was passed to the entity
        mock_task_entity.async_update_state.assert_called_once_with(state)


async def test_service_reference_counting_multiple_entries(hass: HomeAssistant):
    """Test that services are registered once for multiple config entries."""
    # Initialize domain data
    hass.data[DOMAIN] = {"service_ref_count": 0}

    # First entry - should register services
    await async_setup_services(hass)
    assert hass.data[DOMAIN]["service_ref_count"] == 1
    assert hass.services.has_service(DOMAIN, SERVICE_SET_STATE)

    # Second entry - should NOT re-register, just increment counter
    await async_setup_services(hass)
    assert hass.data[DOMAIN]["service_ref_count"] == 2
    assert hass.services.has_service(DOMAIN, SERVICE_SET_STATE)

    # Third entry
    await async_setup_services(hass)
    assert hass.data[DOMAIN]["service_ref_count"] == 3


async def test_service_unload_with_remaining_entries(hass: HomeAssistant):
    """Test that services remain when other entries still exist."""
    # Initialize and setup multiple entries
    hass.data[DOMAIN] = {"service_ref_count": 0}
    await async_setup_services(hass)  # Entry 1
    await async_setup_services(hass)  # Entry 2
    await async_setup_services(hass)  # Entry 3

    assert hass.data[DOMAIN]["service_ref_count"] == 3

    # Unload first entry - services should remain
    await async_unload_services(hass)
    assert hass.data[DOMAIN]["service_ref_count"] == 2
    assert hass.services.has_service(DOMAIN, SERVICE_SET_STATE)

    # Unload second entry - services should still remain
    await async_unload_services(hass)
    assert hass.data[DOMAIN]["service_ref_count"] == 1
    assert hass.services.has_service(DOMAIN, SERVICE_SET_STATE)


async def test_service_unload_last_entry(hass: HomeAssistant):
    """Test that services are removed when last entry is unloaded."""
    # Initialize and setup multiple entries
    hass.data[DOMAIN] = {"service_ref_count": 0}
    await async_setup_services(hass)  # Entry 1
    await async_setup_services(hass)  # Entry 2

    # Unload first entry
    await async_unload_services(hass)
    assert hass.services.has_service(DOMAIN, SERVICE_SET_STATE)

    # Unload last entry - services should be removed
    await async_unload_services(hass)
    assert hass.data[DOMAIN]["service_ref_count"] == 0
    assert not hass.services.has_service(DOMAIN, SERVICE_SET_STATE)
    assert not hass.services.has_service(DOMAIN, SERVICE_ASSIGN)
    assert not hass.services.has_service(DOMAIN, SERVICE_CLONE_STORY)


async def test_service_reference_count_starts_at_zero(hass: HomeAssistant):
    """Test that reference count is properly initialized."""
    hass.data[DOMAIN] = {"service_ref_count": 0}

    # Before any setup
    assert hass.data[DOMAIN]["service_ref_count"] == 0
    assert not hass.services.has_service(DOMAIN, SERVICE_SET_STATE)

    # After first setup
    await async_setup_services(hass)
    assert hass.data[DOMAIN]["service_ref_count"] == 1
    assert hass.services.has_service(DOMAIN, SERVICE_SET_STATE)
