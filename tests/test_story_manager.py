"""Tests for StoryManager business logic."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.storyflow.story_manager import StoryManager
from custom_components.storyflow.storage_handler import StorageHandler


@pytest.fixture
def mock_hass():
    """Mock Home Assistant instance."""
    hass = MagicMock()
    hass.states.get = MagicMock(return_value=None)
    return hass


@pytest.fixture
def mock_storage():
    """Mock StorageHandler."""
    storage = AsyncMock(spec=StorageHandler)
    return storage


@pytest.fixture
def story_manager(mock_storage, mock_hass):
    """Create StoryManager with mocked dependencies."""
    return StoryManager(mock_storage, mock_hass)


@pytest.mark.asyncio
async def test_validate_story_exists_success(story_manager, mock_storage):
    """Test validating an existing story."""
    mock_storage.async_story_exists.return_value = True

    result = await story_manager.async_validate_story_exists("test_story")

    assert result is True
    mock_storage.async_story_exists.assert_called_once_with("test_story")


@pytest.mark.asyncio
async def test_validate_story_exists_failure(story_manager, mock_storage):
    """Test validating a non-existent story."""
    mock_storage.async_story_exists.return_value = False

    with pytest.raises(ValueError, match="Story 'test_story' not found"):
        await story_manager.async_validate_story_exists("test_story")


@pytest.mark.asyncio
async def test_validate_task_exists_success(story_manager, mock_storage):
    """Test validating an existing task."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.async_get_task.return_value = {"id": "task1", "title": "Test"}

    result = await story_manager.async_validate_task_exists("story1", "task1")

    assert result is True
    mock_storage.async_story_exists.assert_called_once_with("story1")
    mock_storage.async_get_task.assert_called_once_with("story1", "task1")


@pytest.mark.asyncio
async def test_validate_task_exists_story_not_found(story_manager, mock_storage):
    """Test validating task when story doesn't exist."""
    mock_storage.async_story_exists.return_value = False

    with pytest.raises(ValueError, match="Story 'story1' not found"):
        await story_manager.async_validate_task_exists("story1", "task1")


@pytest.mark.asyncio
async def test_validate_task_exists_task_not_found(story_manager, mock_storage):
    """Test validating a non-existent task."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.async_get_task.return_value = None

    with pytest.raises(ValueError, match="Task 'task1' not found in story 'story1'"):
        await story_manager.async_validate_task_exists("story1", "task1")


@pytest.mark.asyncio
async def test_update_task_state_valid_todo(story_manager, mock_storage):
    """Test updating task state to 'todo'."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.async_get_task.return_value = {"id": "task1", "state": "in_progress"}
    mock_storage.async_update_task.return_value = None

    await story_manager.async_update_task_state("story1", "task1", "todo")

    mock_storage.async_update_task.assert_called_once_with(
        "story1", "task1", {"state": "todo"}
    )


@pytest.mark.asyncio
async def test_update_task_state_valid_in_progress(story_manager, mock_storage):
    """Test updating task state to 'in_progress'."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.async_get_task.return_value = {"id": "task1", "state": "todo"}
    mock_storage.async_update_task.return_value = None

    await story_manager.async_update_task_state("story1", "task1", "in_progress")

    mock_storage.async_update_task.assert_called_once_with(
        "story1", "task1", {"state": "in_progress"}
    )


@pytest.mark.asyncio
async def test_update_task_state_valid_done(story_manager, mock_storage):
    """Test updating task state to 'done'."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.async_get_task.return_value = {"id": "task1", "state": "in_progress"}
    mock_storage.async_update_task.return_value = None

    await story_manager.async_update_task_state("story1", "task1", "done")

    mock_storage.async_update_task.assert_called_once_with(
        "story1", "task1", {"state": "done"}
    )


@pytest.mark.asyncio
async def test_update_task_state_invalid_state(story_manager, mock_storage):
    """Test updating task state with invalid state value."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.async_get_task.return_value = {"id": "task1", "state": "todo"}

    with pytest.raises(ValueError, match="Invalid state 'blocked'"):
        await story_manager.async_update_task_state("story1", "task1", "blocked")

    # Should not call update if state is invalid
    mock_storage.async_update_task.assert_not_called()


@pytest.mark.asyncio
async def test_update_task_state_task_not_found(story_manager, mock_storage):
    """Test updating state of non-existent task."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.async_get_task.return_value = None

    with pytest.raises(ValueError, match="Task 'task1' not found"):
        await story_manager.async_update_task_state("story1", "task1", "done")


@pytest.mark.asyncio
async def test_assign_task_valid_person(story_manager, mock_storage, mock_hass):
    """Test assigning task to a valid person."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.async_get_task.return_value = {"id": "task1", "assigned_to": None}
    mock_storage.async_update_task.return_value = None

    # Mock entity registry to show person exists
    with patch("homeassistant.helpers.entity_registry.async_get") as mock_async_get:
        mock_registry = MagicMock()
        mock_registry.async_is_registered.return_value = True
        mock_async_get.return_value = mock_registry

        await story_manager.async_assign_task("story1", "task1", "person.john")

    mock_storage.async_update_task.assert_called_once_with(
        "story1", "task1", {"assigned_to": "person.john"}
    )


@pytest.mark.asyncio
async def test_assign_task_unassign(story_manager, mock_storage):
    """Test unassigning a task (person_id = None)."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.async_get_task.return_value = {
        "id": "task1",
        "assigned_to": "person.john",
    }
    mock_storage.async_update_task.return_value = None

    await story_manager.async_assign_task("story1", "task1", None)

    mock_storage.async_update_task.assert_called_once_with(
        "story1", "task1", {"assigned_to": None}
    )


@pytest.mark.asyncio
async def test_assign_task_invalid_person_entity(
    story_manager, mock_storage, mock_hass
):
    """Test assigning task to non-existent person entity."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.async_get_task.return_value = {"id": "task1", "assigned_to": None}

    # Mock entity registry to show person doesn't exist
    with patch("homeassistant.helpers.entity_registry.async_get") as mock_async_get:
        mock_registry = MagicMock()
        mock_registry.async_is_registered.return_value = False
        mock_async_get.return_value = mock_registry
        mock_hass.states.get.return_value = None

        with pytest.raises(
            ValueError, match="Person entity 'person.unknown' not found"
        ):
            await story_manager.async_assign_task("story1", "task1", "person.unknown")

    # Should not call update if person is invalid
    mock_storage.async_update_task.assert_not_called()


@pytest.mark.asyncio
async def test_assign_task_person_in_state_registry(
    story_manager, mock_storage, mock_hass
):
    """Test assigning task to person that exists in state registry but not entity registry."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.async_get_task.return_value = {"id": "task1", "assigned_to": None}
    mock_storage.async_update_task.return_value = None

    # Mock entity registry to show person not registered
    # but state registry shows it exists
    with patch("homeassistant.helpers.entity_registry.async_get") as mock_async_get:
        mock_registry = MagicMock()
        mock_registry.async_is_registered.return_value = False
        mock_async_get.return_value = mock_registry

        mock_state = MagicMock()
        mock_hass.states.get.return_value = mock_state

        await story_manager.async_assign_task("story1", "task1", "person.jane")

    mock_storage.async_update_task.assert_called_once_with(
        "story1", "task1", {"assigned_to": "person.jane"}
    )


@pytest.mark.asyncio
async def test_assign_task_no_hass_instance(mock_storage):
    """Test assigning task when hass instance is not provided (no validation)."""
    # Create manager without hass
    manager = StoryManager(mock_storage, hass=None)

    mock_storage.async_story_exists.return_value = True
    mock_storage.async_get_task.return_value = {"id": "task1", "assigned_to": None}
    mock_storage.async_update_task.return_value = None

    # Should not validate person when hass is None
    await manager.async_assign_task("story1", "task1", "person.anyone")

    mock_storage.async_update_task.assert_called_once_with(
        "story1", "task1", {"assigned_to": "person.anyone"}
    )


@pytest.mark.asyncio
async def test_assign_task_task_not_found(story_manager, mock_storage):
    """Test assigning a non-existent task."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.async_get_task.return_value = None

    with pytest.raises(ValueError, match="Task 'task1' not found"):
        await story_manager.async_assign_task("story1", "task1", "person.john")


@pytest.mark.asyncio
async def test_create_story(story_manager, mock_storage):
    """Test creating a new story."""
    tasks = [
        {"id": "task1", "title": "Task 1", "state": "todo"},
        {"id": "task2", "title": "Task 2", "state": "todo"},
    ]

    story_id = await story_manager.create_story("Test Story", "Description", tasks)

    assert story_id == "test_story"
    mock_storage.save_story.assert_called_once_with(
        "test_story",
        {
            "title": "Test Story",
            "description": "Description",
            "tasks": tasks,
        },
    )


@pytest.mark.asyncio
async def test_state_transitions_all_allowed(story_manager, mock_storage):
    """Test that all state transitions are allowed."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.async_get_task.return_value = {"id": "task1", "state": "todo"}
    mock_storage.async_update_task.return_value = None

    # Test all possible transitions
    transitions = [
        ("todo", "in_progress"),
        ("in_progress", "done"),
        ("done", "todo"),  # Can go back
        ("done", "in_progress"),  # Can go back
        ("in_progress", "todo"),  # Can go back
    ]

    for from_state, to_state in transitions:
        mock_storage.async_get_task.return_value = {"id": "task1", "state": from_state}
        await story_manager.async_update_task_state("story1", "task1", to_state)
        mock_storage.async_update_task.assert_called_with(
            "story1", "task1", {"state": to_state}
        )
