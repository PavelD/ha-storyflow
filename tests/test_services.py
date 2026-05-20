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
    SERVICE_ADD_TASK,
    SERVICE_DELETE_TASK,
    SERVICE_UPDATE_TASK,
    SERVICE_CLONE_STORY,
)
from custom_components.storyflow.const import DOMAIN, TASK_STATES
from custom_components.storyflow.exceptions import TaskNotFoundError


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
    """Test that all services are registered correctly."""
    # Initialize domain data
    hass.data[DOMAIN] = {"service_ref_count": 0}

    await async_setup_services(hass)

    # Verify all services are registered
    assert hass.services.has_service(DOMAIN, SERVICE_SET_STATE)
    assert hass.services.has_service(DOMAIN, SERVICE_ASSIGN)
    assert hass.services.has_service(DOMAIN, SERVICE_ADD_TASK)
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
    with pytest.raises(TaskNotFoundError, match="Task 'nonexistent_task' not found"):
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


async def test_assign_task_updates_entity(hass: HomeAssistant, mock_task_entity):
    """Test that assign_task actually updates the entity."""
    # Setup
    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {"test_task_1": mock_task_entity},
    }
    await async_setup_services(hass)

    # Call service
    await hass.services.async_call(
        DOMAIN,
        SERVICE_ASSIGN,
        {"task_id": "test_task_1", "person_id": "person.john"},
        blocking=True,
    )

    # Verify entity was updated
    mock_task_entity.async_update_assignment.assert_called_once_with("person.john")


async def test_assign_task_unassign(hass: HomeAssistant, mock_task_entity):
    """Test that assign_task with None unassigns the task."""
    # Setup
    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {"test_task_1": mock_task_entity},
    }
    await async_setup_services(hass)

    # Call service without person_id (should unassign)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_ASSIGN,
        {"task_id": "test_task_1"},
        blocking=True,
    )

    # Verify entity was updated with None
    mock_task_entity.async_update_assignment.assert_called_once_with(None)


async def test_assign_task_not_found(hass: HomeAssistant):
    """Test assign_task service with non-existent task."""
    # Setup with empty task registry
    hass.data[DOMAIN] = {"service_ref_count": 0, "task_entities": {}}
    await async_setup_services(hass)

    # Call service with non-existent task
    with pytest.raises(TaskNotFoundError, match="Task 'nonexistent_task' not found"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_ASSIGN,
            {"task_id": "nonexistent_task", "person_id": "person.john"},
            blocking=True,
        )


async def test_assign_task_storage_failure(hass: HomeAssistant, mock_task_entity):
    """Test assign_task handles storage failure gracefully."""
    # Setup entity that raises ValueError on update
    mock_task_entity.async_update_assignment.side_effect = ValueError("Storage error")

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {"test_task_1": mock_task_entity},
    }
    await async_setup_services(hass)

    # Call service should propagate the error
    with pytest.raises(ValueError, match="Storage error"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_ASSIGN,
            {"task_id": "test_task_1", "person_id": "person.john"},
            blocking=True,
        )


async def test_assign_task_missing_task_id(hass: HomeAssistant):
    """Test assign_task service with missing required task_id."""
    hass.data[DOMAIN] = {"service_ref_count": 0}
    await async_setup_services(hass)

    # task_id is required - omitting it should fail schema validation
    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_ASSIGN,
            {"person_id": "person.john"},
            blocking=True,
        )


async def test_assign_task_invalid_task_id_type(hass: HomeAssistant):
    """Test assign_task service with invalid task_id type (schema coerces but task not found)."""
    hass.data[DOMAIN] = {"service_ref_count": 0, "task_entities": {}}
    await async_setup_services(hass)

    # task_id as int will be coerced to string by cv.string, but task won't be found
    with pytest.raises(TaskNotFoundError):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_ASSIGN,
            {"task_id": 123, "person_id": "person.john"},
            blocking=True,
        )


async def test_assign_task_multiple_stories(hass: HomeAssistant):
    """Test assign_task works across multiple stories."""
    # Create tasks from different stories
    task1 = MagicMock()
    task1.task_id = "story1_task_0"
    task1.story_id = "story1"
    task1.async_update_assignment = AsyncMock()

    task2 = MagicMock()
    task2.task_id = "story2_task_0"
    task2.story_id = "story2"
    task2.async_update_assignment = AsyncMock()

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {
            "story1_task_0": task1,
            "story2_task_0": task2,
        },
    }
    await async_setup_services(hass)

    # Assign task from story1
    await hass.services.async_call(
        DOMAIN,
        SERVICE_ASSIGN,
        {"task_id": "story1_task_0", "person_id": "person.alice"},
        blocking=True,
    )

    task1.async_update_assignment.assert_called_once_with("person.alice")
    task2.async_update_assignment.assert_not_called()

    # Assign task from story2
    await hass.services.async_call(
        DOMAIN,
        SERVICE_ASSIGN,
        {"task_id": "story2_task_0", "person_id": "person.bob"},
        blocking=True,
    )

    task2.async_update_assignment.assert_called_once_with("person.bob")


async def test_assign_task_logging(hass: HomeAssistant, mock_task_entity):
    """Test that assign_task logs appropriately."""
    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {"test_task_1": mock_task_entity},
    }
    await async_setup_services(hass)

    with patch("custom_components.storyflow.services._LOGGER") as mock_logger:
        # Test assignment
        await hass.services.async_call(
            DOMAIN,
            SERVICE_ASSIGN,
            {"task_id": "test_task_1", "person_id": "person.john"},
            blocking=True,
        )

        # Verify debug and info logging
        mock_logger.debug.assert_called_once()
        mock_logger.info.assert_called_once()

        # Verify log messages contain task_id and person
        debug_call = str(mock_logger.debug.call_args)
        assert "test_task_1" in debug_call
        assert "person.john" in debug_call

        info_call = str(mock_logger.info.call_args)
        assert "test_task_1" in info_call
        assert "assigned to person.john" in info_call

        # Reset mocks and test unassignment
        mock_logger.reset_mock()

        await hass.services.async_call(
            DOMAIN,
            SERVICE_ASSIGN,
            {"task_id": "test_task_1"},
            blocking=True,
        )

        # Verify unassignment logging
        info_call = str(mock_logger.info.call_args)
        assert "unassigned" in info_call


async def test_clone_story_valid(hass: HomeAssistant):
    """Test clone_story service with valid data."""
    mock_manager = MagicMock()
    mock_manager.async_clone_story = AsyncMock(
        return_value={
            "story_id": "Cloned Story",
            "story_data": {"tasks": []},
        }
    )
    mock_storage = MagicMock()
    mock_storage.async_story_exists = AsyncMock(return_value=True)

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "entry_data": {
            "manager": mock_manager,
            "storage": mock_storage,
        },
    }
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
    mock_manager = MagicMock()
    mock_manager.async_clone_story = AsyncMock(
        return_value={
            "story_id": "test_story_copy",
            "story_data": {"tasks": []},
        }
    )
    mock_storage = MagicMock()
    mock_storage.async_story_exists = AsyncMock(return_value=True)

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "entry_data": {
            "manager": mock_manager,
            "storage": mock_storage,
        },
    }
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
    assert hass.services.has_service(DOMAIN, SERVICE_ADD_TASK)
    assert hass.services.has_service(DOMAIN, SERVICE_CLONE_STORY)

    # Unload services
    await async_unload_services(hass)

    # Verify services are removed
    assert not hass.services.has_service(DOMAIN, SERVICE_SET_STATE)
    assert not hass.services.has_service(DOMAIN, SERVICE_ASSIGN)
    assert not hass.services.has_service(DOMAIN, SERVICE_ADD_TASK)
    assert not hass.services.has_service(DOMAIN, SERVICE_CLONE_STORY)


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


# =============================================================================
# Tests for add_task service
# =============================================================================


@pytest.fixture
def mock_manager():
    """Create a mock story manager for add_task tests."""
    manager = MagicMock()
    manager.async_add_task = AsyncMock(
        return_value={
            "id": "kitchen_task_1",
            "title": "Paint walls",
            "description": "Choose color",
            "assigned_to": None,
            "state": "todo",
            "order": 1,
        }
    )
    return manager


@pytest.fixture
def mock_add_task_storage():
    """Create a mock storage handler for add_task tests."""
    storage = AsyncMock()
    storage.async_story_exists = AsyncMock(return_value=True)
    storage.load_story = AsyncMock(
        return_value={
            "title": "Kitchen",
            "tasks": [{"id": "kitchen_task_0", "title": "Existing task"}],
        }
    )
    return storage


async def test_add_task_story_not_in_callbacks(hass: HomeAssistant):
    """Test add_task raises ValueError when story has no entity callback."""
    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "entity_callbacks": {},  # No callback for this story
        "task_entities": {},
        "progress_entities": {},
    }
    await async_setup_services(hass)

    with pytest.raises(ValueError, match="Story 'unknown_story' not found"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_ADD_TASK,
            {"story_id": "unknown_story", "title": "New task"},
            blocking=True,
        )


async def test_add_task_missing_required_fields(hass: HomeAssistant):
    """Test add_task service schema requires story_id and title."""
    hass.data[DOMAIN] = {"service_ref_count": 0}
    await async_setup_services(hass)

    # Missing title
    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_ADD_TASK,
            {"story_id": "kitchen"},
            blocking=True,
        )

    # Missing story_id
    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_ADD_TASK,
            {"title": "Paint walls"},
            blocking=True,
        )


async def test_add_task_invalid_state_schema(hass: HomeAssistant):
    """Test add_task service schema rejects invalid state values."""
    hass.data[DOMAIN] = {"service_ref_count": 0}
    await async_setup_services(hass)

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_ADD_TASK,
            {"story_id": "kitchen", "title": "Paint walls", "state": "blocked"},
            blocking=True,
        )


async def test_add_task_success_creates_entity(
    hass: HomeAssistant, mock_manager, mock_add_task_storage
):
    """Test add_task service successfully creates and registers an entity."""
    add_entities_calls = []

    def mock_add_entities(entities):
        add_entities_calls.extend(entities)

    mock_progress = MagicMock()
    mock_progress.tasks = []
    mock_progress.async_write_ha_state = MagicMock()

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "entity_callbacks": {"kitchen": mock_add_entities},
        "task_entities": {},
        "progress_entities": {"kitchen": mock_progress},
        "entry_data": {
            "manager": mock_manager,
            "storage": mock_add_task_storage,
        },
    }
    await async_setup_services(hass)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ADD_TASK,
        {"story_id": "kitchen", "title": "Paint walls"},
        blocking=True,
    )

    # Verify manager was called
    mock_manager.async_add_task.assert_called_once()
    call_kwargs = mock_manager.async_add_task.call_args[1]
    assert call_kwargs["story_id"] == "kitchen"
    assert call_kwargs["title"] == "Paint walls"

    # Verify entity was registered
    assert len(add_entities_calls) == 1
    assert "kitchen_task_1" in hass.data[DOMAIN]["task_entities"]


async def test_add_task_success_updates_progress(
    hass: HomeAssistant, mock_manager, mock_add_task_storage
):
    """Test add_task service updates progress entity after task creation."""
    mock_progress = MagicMock()
    mock_progress.tasks = []
    mock_progress.async_write_ha_state = MagicMock()

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "entity_callbacks": {"kitchen": MagicMock()},
        "task_entities": {},
        "progress_entities": {"kitchen": mock_progress},
        "entry_data": {
            "manager": mock_manager,
            "storage": mock_add_task_storage,
        },
    }
    await async_setup_services(hass)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ADD_TASK,
        {"story_id": "kitchen", "title": "Paint walls"},
        blocking=True,
    )

    # Verify progress entity was refreshed
    mock_progress.async_write_ha_state.assert_called_once()


async def test_add_task_with_all_optional_fields(
    hass: HomeAssistant, mock_manager, mock_add_task_storage
):
    """Test add_task service passes all optional fields to manager."""
    mock_manager.async_add_task = AsyncMock(
        return_value={
            "id": "kitchen_task_1",
            "title": "Paint walls",
            "description": "Choose color and paint",
            "assigned_to": "person.john",
            "state": "progress",
            "order": 1,
        }
    )

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "entity_callbacks": {"kitchen": MagicMock()},
        "task_entities": {},
        "progress_entities": {"kitchen": MagicMock()},
        "entry_data": {
            "manager": mock_manager,
            "storage": mock_add_task_storage,
        },
    }
    await async_setup_services(hass)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ADD_TASK,
        {
            "story_id": "kitchen",
            "title": "Paint walls",
            "description": "Choose color and paint",
            "assigned_to": "person.john",
            "state": "progress",
        },
        blocking=True,
    )

    # Verify manager was called with all fields
    mock_manager.async_add_task.assert_called_once_with(
        story_id="kitchen",
        title="Paint walls",
        description="Choose color and paint",
        assigned_to="person.john",
        state="progress",
    )


async def test_add_task_default_state_passed_to_manager(
    hass: HomeAssistant, mock_manager, mock_add_task_storage
):
    """Test add_task service uses 'todo' as default state."""
    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "entity_callbacks": {"kitchen": MagicMock()},
        "task_entities": {},
        "progress_entities": {"kitchen": MagicMock()},
        "entry_data": {
            "manager": mock_manager,
            "storage": mock_add_task_storage,
        },
    }
    await async_setup_services(hass)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ADD_TASK,
        {"story_id": "kitchen", "title": "New task"},
        blocking=True,
    )

    call_kwargs = mock_manager.async_add_task.call_args[1]
    assert call_kwargs["state"] == "todo"
    assert call_kwargs["description"] == ""
    assert call_kwargs["assigned_to"] is None


async def test_add_task_manager_not_found_raises(hass: HomeAssistant):
    """Test add_task raises ValueError when no manager entry found for story."""
    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "entity_callbacks": {"kitchen": MagicMock()},
        "task_entities": {},
        "progress_entities": {},
        # No entry_data with manager + matching storage
    }
    await async_setup_services(hass)

    with pytest.raises(ValueError, match="Story 'kitchen' not found"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_ADD_TASK,
            {"story_id": "kitchen", "title": "Paint walls"},
            blocking=True,
        )


async def test_add_task_all_valid_states_pass_schema(hass: HomeAssistant):
    """Test add_task service schema accepts all valid state values."""
    for state in TASK_STATES:
        hass.data[DOMAIN] = {
            "service_ref_count": 0,
            "entity_callbacks": {},  # Will fail at story lookup, but schema is valid
        }
        await async_setup_services(hass)

        # Schema should not raise - ValueError from story lookup is expected
        with pytest.raises(ValueError):
            await hass.services.async_call(
                DOMAIN,
                SERVICE_ADD_TASK,
                {"story_id": "kitchen", "title": "Task", "state": state},
                blocking=True,
            )


async def test_add_task_manager_raises_value_error(
    hass: HomeAssistant, mock_manager, mock_add_task_storage
):
    """Test add_task service propagates ValueError from manager and leaves state clean.

    Covers the error path where manager.async_add_task raises ValueError (e.g. invalid
    story or state rejected by business logic). No new entity should be registered and
    the progress entity must not be refreshed.
    """
    mock_manager.async_add_task.side_effect = ValueError("some message")

    mock_progress = MagicMock()
    mock_progress.tasks = []
    mock_progress.async_write_ha_state = MagicMock()

    initial_task_entities: dict = {}

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "entity_callbacks": {"kitchen": MagicMock()},
        "task_entities": initial_task_entities,
        "progress_entities": {"kitchen": mock_progress},
        "entry_data": {
            "manager": mock_manager,
            "storage": mock_add_task_storage,
        },
    }
    await async_setup_services(hass)

    # The ValueError raised by the manager must propagate to the caller
    with pytest.raises(ValueError, match="some message"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_ADD_TASK,
            {"story_id": "kitchen", "title": "Paint walls"},
            blocking=True,
        )

    # No new entity must have been added to the task registry
    assert initial_task_entities == {}

    # Progress entity must NOT have been refreshed
    mock_progress.async_write_ha_state.assert_not_called()


# =============================================================================
# Tests for delete_task service
# =============================================================================


@pytest.fixture
def mock_delete_storage():
    """Create a mock storage handler for delete_task tests."""
    storage = MagicMock()
    storage.async_story_exists = AsyncMock(return_value=True)
    storage.load_story = AsyncMock(return_value={"tasks": []})
    return storage


@pytest.fixture
def mock_delete_manager():
    """Create a mock manager for delete_task tests."""
    manager = MagicMock()
    manager.async_delete_task = AsyncMock()
    return manager


@pytest.fixture
def mock_task_entity_for_delete():
    """Create a mock task entity for delete_task tests."""
    entity = MagicMock()
    entity.task_id = "kitchen_task_0"
    entity.story_id = "kitchen"
    entity.entity_id = "sensor.storyflow_kitchen_task_0"
    return entity


async def test_services_registered_includes_delete_and_update(hass: HomeAssistant):
    """Test that delete_task and update_task services are registered."""
    hass.data[DOMAIN] = {"service_ref_count": 0}
    await async_setup_services(hass)

    assert hass.services.has_service(DOMAIN, SERVICE_DELETE_TASK)
    assert hass.services.has_service(DOMAIN, SERVICE_UPDATE_TASK)


async def test_delete_task_calls_manager(
    hass: HomeAssistant,
    mock_task_entity_for_delete,
    mock_delete_manager,
    mock_delete_storage,
):
    """Test delete_task service calls the manager to remove from storage."""
    task_id = "kitchen_task_0"

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {task_id: mock_task_entity_for_delete},
        "progress_entities": {},
        "entry_data": {
            "manager": mock_delete_manager,
            "storage": mock_delete_storage,
        },
    }
    await async_setup_services(hass)

    with patch("homeassistant.helpers.entity_registry.async_get") as mock_er:
        mock_reg = MagicMock()
        mock_reg.async_get_entity_id.return_value = None
        mock_er.return_value = mock_reg

        await hass.services.async_call(
            DOMAIN,
            SERVICE_DELETE_TASK,
            {"task_id": task_id},
            blocking=True,
        )

    mock_delete_manager.async_delete_task.assert_called_once_with("kitchen", task_id)


async def test_delete_task_removes_from_task_entities(
    hass: HomeAssistant,
    mock_task_entity_for_delete,
    mock_delete_manager,
    mock_delete_storage,
):
    """Test delete_task removes the task from the task_entities registry."""
    task_id = "kitchen_task_0"
    task_entities = {task_id: mock_task_entity_for_delete}

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": task_entities,
        "progress_entities": {},
        "entry_data": {
            "manager": mock_delete_manager,
            "storage": mock_delete_storage,
        },
    }
    await async_setup_services(hass)

    with patch("homeassistant.helpers.entity_registry.async_get") as mock_er:
        mock_reg = MagicMock()
        mock_reg.async_get_entity_id.return_value = None
        mock_er.return_value = mock_reg

        await hass.services.async_call(
            DOMAIN,
            SERVICE_DELETE_TASK,
            {"task_id": task_id},
            blocking=True,
        )

    # Task must be removed from the registry
    assert task_id not in hass.data[DOMAIN]["task_entities"]


async def test_delete_task_removes_entity_from_registry(
    hass: HomeAssistant,
    mock_task_entity_for_delete,
    mock_delete_manager,
    mock_delete_storage,
):
    """Test delete_task removes the HA entity from the entity registry."""
    task_id = "kitchen_task_0"
    ha_entity_id = "sensor.storyflow_kitchen_task_0"

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {task_id: mock_task_entity_for_delete},
        "progress_entities": {},
        "entry_data": {
            "manager": mock_delete_manager,
            "storage": mock_delete_storage,
        },
    }
    await async_setup_services(hass)

    with patch("homeassistant.helpers.entity_registry.async_get") as mock_er:
        mock_reg = MagicMock()
        mock_reg.async_get_entity_id.return_value = ha_entity_id
        mock_er.return_value = mock_reg

        await hass.services.async_call(
            DOMAIN,
            SERVICE_DELETE_TASK,
            {"task_id": task_id},
            blocking=True,
        )

        # Entity registry remove should be called with the found entity_id
        mock_reg.async_remove.assert_called_once_with(ha_entity_id)


async def test_delete_task_updates_progress_entity(
    hass: HomeAssistant,
    mock_task_entity_for_delete,
    mock_delete_manager,
    mock_delete_storage,
):
    """Test delete_task refreshes the progress entity after deletion."""
    task_id = "kitchen_task_0"

    mock_progress = MagicMock()
    mock_progress.tasks = [{"id": task_id, "state": "done"}]
    mock_progress.async_write_ha_state = MagicMock()

    # After deletion, storage returns empty task list
    mock_delete_storage.load_story.return_value = {"tasks": []}

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {task_id: mock_task_entity_for_delete},
        "progress_entities": {"kitchen": mock_progress},
        "entry_data": {
            "manager": mock_delete_manager,
            "storage": mock_delete_storage,
        },
    }
    await async_setup_services(hass)

    with patch("homeassistant.helpers.entity_registry.async_get") as mock_er:
        mock_reg = MagicMock()
        mock_reg.async_get_entity_id.return_value = None
        mock_er.return_value = mock_reg

        await hass.services.async_call(
            DOMAIN,
            SERVICE_DELETE_TASK,
            {"task_id": task_id},
            blocking=True,
        )

    # Progress entity should have been refreshed with updated task list
    mock_progress.async_write_ha_state.assert_called_once()
    assert mock_progress.tasks == []


async def test_delete_task_no_progress_entity_no_error(
    hass: HomeAssistant,
    mock_task_entity_for_delete,
    mock_delete_manager,
    mock_delete_storage,
):
    """Test delete_task works fine even when there is no progress entity."""
    task_id = "kitchen_task_0"

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {task_id: mock_task_entity_for_delete},
        "progress_entities": {},  # No progress entity for this story
        "entry_data": {
            "manager": mock_delete_manager,
            "storage": mock_delete_storage,
        },
    }
    await async_setup_services(hass)

    with patch("homeassistant.helpers.entity_registry.async_get") as mock_er:
        mock_reg = MagicMock()
        mock_reg.async_get_entity_id.return_value = None
        mock_er.return_value = mock_reg

        # Should not raise even without a progress entity
        await hass.services.async_call(
            DOMAIN,
            SERVICE_DELETE_TASK,
            {"task_id": task_id},
            blocking=True,
        )

    mock_delete_manager.async_delete_task.assert_called_once()


async def test_delete_task_story_not_found(
    hass: HomeAssistant,
    mock_delete_manager,
    mock_delete_storage,
    mock_task_entity_for_delete,
) -> None:
    """Test delete_task raises ValueError when no story/entry_data can be resolved.

    The task exists in the registry but the underlying storage returns False for
    async_story_exists, so _get_manager_and_storage_for_story raises ValueError.
    """
    task_id = mock_task_entity_for_delete.task_id

    # Make storage unable to find the story
    mock_delete_storage.async_story_exists = AsyncMock(return_value=False)

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {task_id: mock_task_entity_for_delete},
        "progress_entities": {},
        "entry_data": {
            "manager": mock_delete_manager,
            "storage": mock_delete_storage,
        },
    }
    await async_setup_services(hass)

    with pytest.raises(
        ValueError,
        match=f"Story '{mock_task_entity_for_delete.story_id}' not found",
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_DELETE_TASK,
            {"task_id": task_id},
            blocking=True,
        )

    # Task must still be present in the registry (nothing was deleted)
    assert hass.data[DOMAIN]["task_entities"][task_id] is mock_task_entity_for_delete
    mock_delete_manager.async_delete_task.assert_not_called()


async def test_delete_task_task_not_found(hass: HomeAssistant):
    """Test delete_task raises TaskNotFoundError when task is not in registry."""
    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {},
    }
    await async_setup_services(hass)

    with pytest.raises(TaskNotFoundError, match="Task 'nonexistent_task' not found"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_DELETE_TASK,
            {"task_id": "nonexistent_task"},
            blocking=True,
        )


async def test_delete_task_manager_failure_propagates(
    hass: HomeAssistant,
    mock_task_entity_for_delete,
    mock_delete_storage,
):
    """Test delete_task propagates ValueError from manager."""
    task_id = "kitchen_task_0"

    failing_manager = MagicMock()
    failing_manager.async_delete_task = AsyncMock(
        side_effect=ValueError("Delete failed")
    )

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {task_id: mock_task_entity_for_delete},
        "progress_entities": {},
        "entry_data": {
            "manager": failing_manager,
            "storage": mock_delete_storage,
        },
    }
    await async_setup_services(hass)

    with pytest.raises(ValueError, match="Delete failed"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_DELETE_TASK,
            {"task_id": task_id},
            blocking=True,
        )


async def test_delete_task_missing_task_id_field(hass: HomeAssistant):
    """Test delete_task schema rejects missing task_id."""
    hass.data[DOMAIN] = {"service_ref_count": 0}
    await async_setup_services(hass)

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_DELETE_TASK,
            {},
            blocking=True,
        )


async def test_unload_services_removes_delete_and_update(hass: HomeAssistant):
    """Test that delete_task and update_task are removed when services are unloaded."""
    hass.data[DOMAIN] = {"service_ref_count": 0}
    await async_setup_services(hass)

    assert hass.services.has_service(DOMAIN, SERVICE_DELETE_TASK)
    assert hass.services.has_service(DOMAIN, SERVICE_UPDATE_TASK)

    await async_unload_services(hass)

    assert not hass.services.has_service(DOMAIN, SERVICE_DELETE_TASK)
    assert not hass.services.has_service(DOMAIN, SERVICE_UPDATE_TASK)


# =============================================================================
# Tests for update_task service
# =============================================================================


@pytest.fixture
def mock_task_entity_for_update():
    """Create a mock task entity for update_task tests."""
    entity = MagicMock()
    entity.task_id = "kitchen_task_0"
    entity.story_id = "kitchen"
    entity.title = "Old Title"
    entity.description = "Old Description"
    entity.async_update_attributes = AsyncMock()
    return entity


async def test_update_task_title_only(hass: HomeAssistant, mock_task_entity_for_update):
    """Test update_task service updates only the title."""
    task_id = "kitchen_task_0"

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {task_id: mock_task_entity_for_update},
    }
    await async_setup_services(hass)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_UPDATE_TASK,
        {"task_id": task_id, "title": "New Title"},
        blocking=True,
    )

    mock_task_entity_for_update.async_update_attributes.assert_called_once_with(
        title="New Title"
    )


async def test_update_task_description_only(
    hass: HomeAssistant, mock_task_entity_for_update
):
    """Test update_task service updates only the description."""
    task_id = "kitchen_task_0"

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {task_id: mock_task_entity_for_update},
    }
    await async_setup_services(hass)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_UPDATE_TASK,
        {"task_id": task_id, "description": "New description"},
        blocking=True,
    )

    mock_task_entity_for_update.async_update_attributes.assert_called_once_with(
        description="New description"
    )


async def test_update_task_both_fields(
    hass: HomeAssistant, mock_task_entity_for_update
):
    """Test update_task service updates both title and description."""
    task_id = "kitchen_task_0"

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {task_id: mock_task_entity_for_update},
    }
    await async_setup_services(hass)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_UPDATE_TASK,
        {"task_id": task_id, "title": "New Title", "description": "New Desc"},
        blocking=True,
    )

    mock_task_entity_for_update.async_update_attributes.assert_called_once_with(
        title="New Title", description="New Desc"
    )


async def test_update_task_no_fields_raises(hass: HomeAssistant):
    """Test update_task raises ValueError when neither title nor description is provided."""
    task_id = "kitchen_task_0"

    mock_entity = MagicMock()
    mock_entity.task_id = task_id
    mock_entity.story_id = "kitchen"
    mock_entity.async_update_attributes = AsyncMock()

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {task_id: mock_entity},
    }
    await async_setup_services(hass)

    with pytest.raises(
        ValueError, match="At least one of 'title' or 'description' must be provided"
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_UPDATE_TASK,
            {"task_id": task_id},
            blocking=True,
        )

    # Entity should not have been updated
    mock_entity.async_update_attributes.assert_not_called()


async def test_update_task_task_not_found(hass: HomeAssistant):
    """Test update_task raises TaskNotFoundError when task is not registered."""
    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {},
    }
    await async_setup_services(hass)

    with pytest.raises(TaskNotFoundError, match="Task 'nonexistent' not found"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_UPDATE_TASK,
            {"task_id": "nonexistent", "title": "New Title"},
            blocking=True,
        )


async def test_update_task_storage_failure_propagates(
    hass: HomeAssistant, mock_task_entity_for_update
):
    """Test update_task propagates ValueError from entity update."""
    task_id = "kitchen_task_0"
    mock_task_entity_for_update.async_update_attributes.side_effect = ValueError(
        "Storage error"
    )

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {task_id: mock_task_entity_for_update},
    }
    await async_setup_services(hass)

    with pytest.raises(ValueError, match="Storage error"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_UPDATE_TASK,
            {"task_id": task_id, "title": "New Title"},
            blocking=True,
        )


async def test_update_task_missing_task_id_field(hass: HomeAssistant):
    """Test update_task schema rejects missing task_id."""
    hass.data[DOMAIN] = {"service_ref_count": 0}
    await async_setup_services(hass)

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_UPDATE_TASK,
            {"title": "Title without task_id"},
            blocking=True,
        )


async def test_update_task_entity_state_reflects_update(
    hass: HomeAssistant, mock_task_entity_for_update
):
    """Test update_task correctly passes only provided fields to entity."""
    task_id = "kitchen_task_0"

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {task_id: mock_task_entity_for_update},
    }
    await async_setup_services(hass)

    # Update title only - description kwarg should NOT be passed
    await hass.services.async_call(
        DOMAIN,
        SERVICE_UPDATE_TASK,
        {"task_id": task_id, "title": "Updated Title"},
        blocking=True,
    )

    call_kwargs = mock_task_entity_for_update.async_update_attributes.call_args[1]
    assert "title" in call_kwargs
    assert "description" not in call_kwargs
    assert call_kwargs["title"] == "Updated Title"


# =============================================================================
# Tests for clone_story service
# =============================================================================


def _make_mock_manager_and_storage_for_clone(story_id, story_data):
    """Helper that returns (mock_manager, mock_storage) wired for clone tests."""
    mock_storage = AsyncMock()
    mock_storage.async_story_exists = AsyncMock(
        side_effect=lambda sid: sid == story_id  # source exists, new one doesn't
    )
    mock_storage.load_story = AsyncMock(return_value=story_data)
    mock_storage.save_story = AsyncMock(return_value=None)

    mock_manager = AsyncMock()
    mock_manager.async_clone_story = AsyncMock(
        return_value={
            "story_id": "kitchen_copy",
            "story_data": {
                "title": "Kitchen Copy",
                "description": story_data.get("description", ""),
                "tasks": [
                    {
                        "id": "kitchen_copy_task_0",
                        "title": "Paint",
                        "description": "",
                        "assigned_to": None,
                        "state": "todo",
                        "order": 0,
                    }
                ],
            },
        }
    )

    return mock_manager, mock_storage


async def test_clone_story_success(hass: HomeAssistant):
    """Test clone_story service call succeeds and creates entities."""
    story_id = "kitchen"
    story_data = {
        "title": "Kitchen",
        "description": "",
        "tasks": [
            {
                "id": "kitchen_task_0",
                "title": "Paint",
                "description": "",
                "assigned_to": None,
                "state": "done",
                "order": 0,
            },
        ],
    }

    mock_manager, mock_storage = _make_mock_manager_and_storage_for_clone(
        story_id, story_data
    )
    mock_add_entities = MagicMock()

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {},
        "entity_callbacks": {story_id: mock_add_entities},
        "progress_entities": {},
        "entry_kitchen": {
            "manager": mock_manager,
            "storage": mock_storage,
        },
    }

    await async_setup_services(hass)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_CLONE_STORY,
        {"story_id": story_id, "new_story_name": "Kitchen Copy"},
        blocking=True,
    )

    # Manager's async_clone_story must have been called
    mock_manager.async_clone_story.assert_called_once_with(story_id, "Kitchen Copy")

    # async_add_entities must have been called with new entities
    assert mock_add_entities.call_count == 1
    new_entities = mock_add_entities.call_args[0][0]
    # Should include 1 progress entity + 1 task entity
    assert len(new_entities) == 2

    cloned_story_id = "kitchen_copy"

    # Verify progress_entities registry is populated for the cloned story
    assert cloned_story_id in hass.data[DOMAIN]["progress_entities"]
    cloned_progress = hass.data[DOMAIN]["progress_entities"][cloned_story_id]
    assert cloned_progress.story_id == cloned_story_id

    # Verify task_entities registry is populated for the cloned task
    cloned_task_id = "kitchen_copy_task_0"
    assert cloned_task_id in hass.data[DOMAIN]["task_entities"]
    cloned_task = hass.data[DOMAIN]["task_entities"][cloned_task_id]
    assert cloned_task.story_id == cloned_story_id
    assert cloned_task.title == "Paint"
    # Tasks are reset to todo on clone
    assert cloned_task.state == "todo"


async def test_clone_story_source_not_found(hass: HomeAssistant):
    """Test clone_story raises ValueError when source story doesn't exist."""
    mock_storage = AsyncMock()
    mock_storage.async_story_exists = AsyncMock(return_value=False)
    mock_manager = AsyncMock()

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {},
        "entity_callbacks": {},
        "progress_entities": {},
        "entry_data": {
            "manager": mock_manager,
            "storage": mock_storage,
        },
    }

    await async_setup_services(hass)

    with pytest.raises(ValueError, match="not found"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_CLONE_STORY,
            {"story_id": "nonexistent"},
            blocking=True,
        )


async def test_clone_story_manager_raises_propagates(hass: HomeAssistant):
    """Test that ValueError from async_clone_story propagates to caller."""
    story_id = "kitchen"
    mock_storage = AsyncMock()
    mock_storage.async_story_exists = AsyncMock(return_value=True)
    mock_manager = AsyncMock()
    mock_manager.async_clone_story = AsyncMock(
        side_effect=ValueError("A story with ID 'kitchen_copy' already exists.")
    )
    mock_add_entities = MagicMock()

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {},
        "entity_callbacks": {story_id: mock_add_entities},
        "progress_entities": {},
        "entry_kitchen": {
            "manager": mock_manager,
            "storage": mock_storage,
        },
    }

    await async_setup_services(hass)

    with pytest.raises(ValueError, match="already exists"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_CLONE_STORY,
            {"story_id": story_id, "new_story_name": "Kitchen Copy"},
            blocking=True,
        )

    # No entities should have been added
    mock_add_entities.assert_not_called()


async def test_clone_story_no_entity_callback_does_not_raise(hass: HomeAssistant):
    """Test clone_story succeeds (with a warning) when no entity callback exists."""
    story_id = "kitchen"
    story_data = {"title": "Kitchen", "description": "", "tasks": []}
    mock_manager, mock_storage = _make_mock_manager_and_storage_for_clone(
        story_id, story_data
    )
    mock_manager.async_clone_story = AsyncMock(
        return_value={
            "story_id": "kitchen_copy",
            "story_data": {"title": "Kitchen Copy", "description": "", "tasks": []},
        }
    )

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {},
        "entity_callbacks": {},  # No callbacks at all
        "progress_entities": {},
        "entry_kitchen": {
            "manager": mock_manager,
            "storage": mock_storage,
        },
    }

    await async_setup_services(hass)

    # Should not raise; data is persisted even without live entity creation
    await hass.services.async_call(
        DOMAIN,
        SERVICE_CLONE_STORY,
        {"story_id": story_id},
        blocking=True,
    )

    mock_manager.async_clone_story.assert_called_once_with(story_id, None)


async def test_clone_story_registers_callback_for_new_story(hass: HomeAssistant):
    """Test that clone_story registers the entity callback for the new story_id."""
    story_id = "kitchen"
    story_data = {
        "title": "Kitchen",
        "description": "",
        "tasks": [],
    }
    mock_manager, mock_storage = _make_mock_manager_and_storage_for_clone(
        story_id, story_data
    )
    mock_manager.async_clone_story = AsyncMock(
        return_value={
            "story_id": "kitchen_copy",
            "story_data": {"title": "Kitchen Copy", "description": "", "tasks": []},
        }
    )
    mock_add_entities = MagicMock()

    hass.data[DOMAIN] = {
        "service_ref_count": 0,
        "task_entities": {},
        "entity_callbacks": {story_id: mock_add_entities},
        "progress_entities": {},
        "entry_kitchen": {
            "manager": mock_manager,
            "storage": mock_storage,
        },
    }

    await async_setup_services(hass)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_CLONE_STORY,
        {"story_id": story_id, "new_story_name": "Kitchen Copy"},
        blocking=True,
    )

    # The new story's callback must be registered so add_task works on the clone too
    assert "kitchen_copy" in hass.data[DOMAIN]["entity_callbacks"]


async def test_clone_story_schema_rejects_missing_story_id(hass: HomeAssistant):
    """Test clone_story schema rejects call with no story_id."""
    hass.data[DOMAIN] = {"service_ref_count": 0}
    await async_setup_services(hass)

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_CLONE_STORY,
            {},  # Missing required story_id
            blocking=True,
        )


async def test_clone_story_unloaded_with_last_entry(hass: HomeAssistant):
    """Test that clone_story service is removed when last entry unloads."""
    hass.data[DOMAIN] = {"service_ref_count": 0}
    await async_setup_services(hass)

    assert hass.services.has_service(DOMAIN, SERVICE_CLONE_STORY)

    await async_unload_services(hass)

    assert not hass.services.has_service(DOMAIN, SERVICE_CLONE_STORY)
