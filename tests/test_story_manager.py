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
async def test_create_story_success(story_manager, mock_storage):
    """Test creating a new story when it does not exist yet."""
    mock_storage.async_story_exists.return_value = False
    mock_storage.save_story.return_value = None

    story_id = await story_manager.create_story(
        "My Story", "A description", [{"title": "Task 1"}]
    )

    assert story_id == "my_story"
    mock_storage.save_story.assert_called_once_with(
        "my_story",
        {
            "title": "My Story",
            "description": "A description",
            "tasks": [{"title": "Task 1", "id": "my_story_task_0", "order": 0}],
        },
    )


@pytest.mark.asyncio
async def test_create_story_raises_if_already_exists(story_manager, mock_storage):
    """Test that create_story raises ValueError if the story ID already exists.

    This prevents task states from being overwritten on HA restart/reload.
    """
    mock_storage.async_story_exists.return_value = True

    with pytest.raises(ValueError, match="already exists"):
        await story_manager.create_story("My Story", "desc", [])

    # Save must never be called when story already exists
    mock_storage.save_story.assert_not_called()


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
    """Test creating a new story (story does not exist yet)."""
    mock_storage.async_story_exists.return_value = False
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
            "tasks": [
                {"id": "task1", "title": "Task 1", "state": "todo", "order": 0},
                {"id": "task2", "title": "Task 2", "state": "todo", "order": 1},
            ],
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


# =============================================================================
# Tests for async_generate_task_id
# =============================================================================


@pytest.mark.asyncio
async def test_generate_task_id_empty_story(story_manager, mock_storage):
    """Test task ID generation when story has no tasks."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.load_story.return_value = {"title": "Test", "tasks": []}

    task_id = await story_manager.async_generate_task_id("kitchen")

    assert task_id == "kitchen_task_0"


@pytest.mark.asyncio
async def test_generate_task_id_with_existing_tasks(story_manager, mock_storage):
    """Test task ID generation increments beyond existing tasks."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.load_story.return_value = {
        "title": "Test",
        "tasks": [
            {"id": "kitchen_task_0", "title": "Task 0"},
            {"id": "kitchen_task_1", "title": "Task 1"},
        ],
    }

    task_id = await story_manager.async_generate_task_id("kitchen")

    assert task_id == "kitchen_task_2"


@pytest.mark.asyncio
async def test_generate_task_id_with_gaps_in_numbering(story_manager, mock_storage):
    """Test task ID generation uses max index + 1 (handles gaps)."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.load_story.return_value = {
        "title": "Test",
        "tasks": [
            {"id": "kitchen_task_0", "title": "Task 0"},
            {"id": "kitchen_task_5", "title": "Task 5"},  # Gap: 1-4 missing
        ],
    }

    task_id = await story_manager.async_generate_task_id("kitchen")

    assert task_id == "kitchen_task_6"


@pytest.mark.asyncio
async def test_generate_task_id_ignores_malformed_ids(story_manager, mock_storage):
    """Test task ID generation ignores tasks with malformed IDs."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.load_story.return_value = {
        "title": "Test",
        "tasks": [
            {"id": "kitchen_task_0", "title": "Task 0"},
            {"id": "malformed_id", "title": "Malformed"},
            {"id": "kitchen_task_bad", "title": "Non-numeric"},
        ],
    }

    task_id = await story_manager.async_generate_task_id("kitchen")

    assert task_id == "kitchen_task_1"


@pytest.mark.asyncio
async def test_generate_task_id_story_not_found(story_manager, mock_storage):
    """Test task ID generation raises ValueError when story not found."""
    mock_storage.async_story_exists.return_value = False

    with pytest.raises(ValueError, match="Story 'unknown_story' not found"):
        await story_manager.async_generate_task_id("unknown_story")


# =============================================================================
# Tests for async_add_task
# =============================================================================


@pytest.mark.asyncio
async def test_add_task_success_all_fields(story_manager, mock_storage):
    """Test adding a task with all fields provided."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.load_story.return_value = {
        "title": "Kitchen",
        "tasks": [{"id": "kitchen_task_0", "title": "Existing"}],
    }
    mock_storage.async_add_task.return_value = None

    result = await story_manager.async_add_task(
        story_id="kitchen",
        title="Paint walls",
        description="Choose color and paint",
        assigned_to="person.john",
        state="progress",
    )

    assert result["id"] == "kitchen_task_1"
    assert result["title"] == "Paint walls"
    assert result["description"] == "Choose color and paint"
    assert result["assigned_to"] == "person.john"
    assert result["state"] == "progress"
    assert result["order"] == 1  # Second task, index 1

    mock_storage.async_add_task.assert_called_once_with("kitchen", result)


@pytest.mark.asyncio
async def test_add_task_success_minimal_fields(story_manager, mock_storage):
    """Test adding a task with only required fields (title, story_id)."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.load_story.return_value = {"title": "Kitchen", "tasks": []}
    mock_storage.async_add_task.return_value = None

    result = await story_manager.async_add_task(
        story_id="kitchen",
        title="Buy materials",
    )

    assert result["id"] == "kitchen_task_0"
    assert result["title"] == "Buy materials"
    assert result["description"] == ""
    assert result["assigned_to"] is None
    assert result["state"] == "todo"
    assert result["order"] == 0


@pytest.mark.asyncio
async def test_add_task_default_state_is_todo(story_manager, mock_storage):
    """Test that default state is 'todo' when not specified."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.load_story.return_value = {"title": "Test", "tasks": []}
    mock_storage.async_add_task.return_value = None

    result = await story_manager.async_add_task(story_id="myStory", title="New Task")

    assert result["state"] == "todo"


@pytest.mark.asyncio
async def test_add_task_all_valid_states(story_manager, mock_storage):
    """Test adding a task with each valid state."""
    valid_states = ["todo", "progress", "review", "done", "rejected"]

    for state in valid_states:
        mock_storage.async_story_exists.return_value = True
        mock_storage.load_story.return_value = {"title": "Test", "tasks": []}
        mock_storage.async_add_task.return_value = None

        result = await story_manager.async_add_task(
            story_id="myStory",
            title="Task",
            state=state,
        )

        assert result["state"] == state, f"Failed for state: {state}"


@pytest.mark.asyncio
async def test_add_task_invalid_state(story_manager, mock_storage):
    """Test adding a task with an invalid state raises ValueError."""
    mock_storage.async_story_exists.return_value = True

    with pytest.raises(ValueError, match="Invalid state 'blocked'"):
        await story_manager.async_add_task(
            story_id="kitchen",
            title="Paint walls",
            state="blocked",
        )

    # Storage should not be called when state is invalid
    mock_storage.async_add_task.assert_not_called()


@pytest.mark.asyncio
async def test_add_task_story_not_found(story_manager, mock_storage):
    """Test adding a task to a non-existent story raises ValueError."""
    mock_storage.async_story_exists.return_value = False

    with pytest.raises(ValueError, match="Story 'unknown' not found"):
        await story_manager.async_add_task(
            story_id="unknown",
            title="Task",
        )

    mock_storage.async_add_task.assert_not_called()


@pytest.mark.asyncio
async def test_add_task_order_reflects_current_task_count(story_manager, mock_storage):
    """Test that the order field equals the current number of existing tasks."""
    mock_storage.async_story_exists.return_value = True
    existing_tasks = [
        {"id": "story_task_0", "title": "Task 0"},
        {"id": "story_task_1", "title": "Task 1"},
        {"id": "story_task_2", "title": "Task 2"},
    ]
    mock_storage.load_story.return_value = {
        "title": "My Story",
        "tasks": existing_tasks,
    }
    mock_storage.async_add_task.return_value = None

    result = await story_manager.async_add_task(
        story_id="story",
        title="New Task",
    )

    assert result["order"] == 3  # 3 existing tasks → order index 3


@pytest.mark.asyncio
async def test_add_task_persists_to_storage(story_manager, mock_storage):
    """Test that async_add_task calls storage to persist the task."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.load_story.return_value = {"title": "Test", "tasks": []}
    mock_storage.async_add_task.return_value = None

    await story_manager.async_add_task(story_id="mystory", title="New Task")

    # Verify storage was called with correct task data
    mock_storage.async_add_task.assert_called_once()
    call_args = mock_storage.async_add_task.call_args
    assert call_args[0][0] == "mystory"
    task_data = call_args[0][1]
    assert task_data["id"] == "mystory_task_0"
    assert task_data["title"] == "New Task"


# =============================================================================
# Tests for async_delete_task
# =============================================================================


@pytest.mark.asyncio
async def test_delete_task_success(story_manager, mock_storage):
    """Test successfully deleting an existing task."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.async_get_task.return_value = {"id": "task1", "title": "Test"}
    mock_storage.async_delete_task.return_value = None

    await story_manager.async_delete_task("story1", "task1")

    mock_storage.async_delete_task.assert_called_once_with("story1", "task1")


@pytest.mark.asyncio
async def test_delete_task_story_not_found(story_manager, mock_storage):
    """Test deleting a task from a non-existent story raises ValueError."""
    mock_storage.async_story_exists.return_value = False

    with pytest.raises(ValueError, match="Story 'story1' not found"):
        await story_manager.async_delete_task("story1", "task1")

    mock_storage.async_delete_task.assert_not_called()


@pytest.mark.asyncio
async def test_delete_task_task_not_found(story_manager, mock_storage):
    """Test deleting a non-existent task raises ValueError."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.async_get_task.return_value = None

    with pytest.raises(ValueError, match="Task 'task1' not found in story 'story1'"):
        await story_manager.async_delete_task("story1", "task1")

    mock_storage.async_delete_task.assert_not_called()


@pytest.mark.asyncio
async def test_delete_task_validates_before_deleting(story_manager, mock_storage):
    """Test that story and task are validated before deletion is called."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.async_get_task.return_value = {"id": "task1", "title": "Test"}
    mock_storage.async_delete_task.return_value = None

    await story_manager.async_delete_task("story1", "task1")

    # Both story and task must have been validated before deletion
    mock_storage.async_story_exists.assert_called_once_with("story1")
    mock_storage.async_get_task.assert_called_once_with("story1", "task1")
    mock_storage.async_delete_task.assert_called_once_with("story1", "task1")


@pytest.mark.asyncio
async def test_delete_task_storage_propagates_error(story_manager, mock_storage):
    """Test that a storage error during delete propagates to the caller."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.async_get_task.return_value = {"id": "task1", "title": "Test"}
    mock_storage.async_delete_task.side_effect = ValueError("Storage error")

    with pytest.raises(ValueError, match="Storage error"):
        await story_manager.async_delete_task("story1", "task1")


# =============================================================================
# Tests for async_update_task_details
# =============================================================================


@pytest.mark.asyncio
async def test_update_task_details_title_only(story_manager, mock_storage):
    """Test updating only the title of a task."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.async_get_task.return_value = {"id": "task1", "title": "Old Title"}
    mock_storage.async_update_task.return_value = None

    await story_manager.async_update_task_details("story1", "task1", title="New Title")

    mock_storage.async_update_task.assert_called_once_with(
        "story1", "task1", {"title": "New Title"}
    )


@pytest.mark.asyncio
async def test_update_task_details_description_only(story_manager, mock_storage):
    """Test updating only the description of a task."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.async_get_task.return_value = {
        "id": "task1",
        "description": "Old desc",
    }
    mock_storage.async_update_task.return_value = None

    await story_manager.async_update_task_details(
        "story1", "task1", description="New description"
    )

    mock_storage.async_update_task.assert_called_once_with(
        "story1", "task1", {"description": "New description"}
    )


@pytest.mark.asyncio
async def test_update_task_details_both_fields(story_manager, mock_storage):
    """Test updating both title and description of a task."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.async_get_task.return_value = {"id": "task1", "title": "Old"}
    mock_storage.async_update_task.return_value = None

    await story_manager.async_update_task_details(
        "story1", "task1", title="New Title", description="New Desc"
    )

    mock_storage.async_update_task.assert_called_once_with(
        "story1", "task1", {"title": "New Title", "description": "New Desc"}
    )


@pytest.mark.asyncio
async def test_update_task_details_no_fields_raises(story_manager, mock_storage):
    """Test that providing no fields raises ValueError before any storage access."""
    with pytest.raises(ValueError, match="At least one field.*must be provided"):
        await story_manager.async_update_task_details("story1", "task1")

    # No storage calls should happen when no fields are provided
    mock_storage.async_story_exists.assert_not_called()
    mock_storage.async_update_task.assert_not_called()


@pytest.mark.asyncio
async def test_update_task_details_story_not_found(story_manager, mock_storage):
    """Test updating a task in a non-existent story raises ValueError."""
    mock_storage.async_story_exists.return_value = False

    with pytest.raises(ValueError, match="Story 'story1' not found"):
        await story_manager.async_update_task_details(
            "story1", "task1", title="New Title"
        )

    mock_storage.async_update_task.assert_not_called()


@pytest.mark.asyncio
async def test_update_task_details_task_not_found(story_manager, mock_storage):
    """Test updating a non-existent task raises ValueError."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.async_get_task.return_value = None

    with pytest.raises(ValueError, match="Task 'task1' not found"):
        await story_manager.async_update_task_details(
            "story1", "task1", title="New Title"
        )

    mock_storage.async_update_task.assert_not_called()


@pytest.mark.asyncio
async def test_update_task_details_validates_existence_before_update(
    story_manager, mock_storage
):
    """Test that task existence is validated before the storage update call."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.async_get_task.return_value = {"id": "task1", "title": "Old"}
    mock_storage.async_update_task.return_value = None

    await story_manager.async_update_task_details("story1", "task1", title="New Title")

    # Validation calls must precede the update call
    mock_storage.async_story_exists.assert_called_once_with("story1")
    mock_storage.async_get_task.assert_called_once_with("story1", "task1")
    mock_storage.async_update_task.assert_called_once()


@pytest.mark.asyncio
async def test_update_task_details_storage_error_propagates(
    story_manager, mock_storage
):
    """Test that a storage error during update propagates to the caller."""
    mock_storage.async_story_exists.return_value = True
    mock_storage.async_get_task.return_value = {"id": "task1", "title": "Old"}
    mock_storage.async_update_task.side_effect = ValueError("Storage error")

    with pytest.raises(ValueError, match="Storage error"):
        await story_manager.async_update_task_details(
            "story1", "task1", title="New Title"
        )


# =============================================================================
# Tests for async_clone_story
# =============================================================================


@pytest.mark.asyncio
async def test_clone_story_success_with_custom_name(story_manager, mock_storage):
    """Test cloning a story with a custom name."""
    mock_storage.async_story_exists.side_effect = [
        True,  # source story exists
        False,  # new story does NOT exist yet
    ]
    mock_storage.load_story.return_value = {
        "title": "Kitchen",
        "description": "Renovation project",
        "tasks": [
            {
                "id": "kitchen_task_0",
                "title": "Paint",
                "description": "",
                "assigned_to": "person.john",
                "state": "done",
                "order": 0,
            },
        ],
    }
    mock_storage.save_story.return_value = None

    result = await story_manager.async_clone_story("kitchen", "Kitchen Round 2")

    assert result["story_id"] == "kitchen_round_2"
    assert result["story_data"]["title"] == "Kitchen Round 2"
    mock_storage.save_story.assert_called_once()


@pytest.mark.asyncio
async def test_clone_story_success_default_name(story_manager, mock_storage):
    """Test cloning uses '{original title} (Copy)' when no name is given."""
    mock_storage.async_story_exists.side_effect = [True, False]
    mock_storage.load_story.return_value = {
        "title": "Kitchen",
        "description": "",
        "tasks": [],
    }
    mock_storage.save_story.return_value = None

    result = await story_manager.async_clone_story("kitchen")

    assert result["story_data"]["title"] == "Kitchen (Copy)"
    assert result["story_id"] == "kitchen_copy"


@pytest.mark.asyncio
async def test_clone_story_resets_tasks_to_todo(story_manager, mock_storage):
    """Test that all cloned tasks are reset to 'todo' state."""
    mock_storage.async_story_exists.side_effect = [True, False]
    mock_storage.load_story.return_value = {
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
            {
                "id": "kitchen_task_1",
                "title": "Fix",
                "description": "",
                "assigned_to": None,
                "state": "progress",
                "order": 1,
            },
            {
                "id": "kitchen_task_2",
                "title": "Clean",
                "description": "",
                "assigned_to": None,
                "state": "rejected",
                "order": 2,
            },
        ],
    }
    mock_storage.save_story.return_value = None

    result = await story_manager.async_clone_story("kitchen", "Kitchen Copy")

    for task in result["story_data"]["tasks"]:
        assert task["state"] == "todo", f"Task '{task['title']}' was not reset to todo"


@pytest.mark.asyncio
async def test_clone_story_clears_assignments(story_manager, mock_storage):
    """Test that all cloned tasks have assigned_to cleared."""
    mock_storage.async_story_exists.side_effect = [True, False]
    mock_storage.load_story.return_value = {
        "title": "Kitchen",
        "description": "",
        "tasks": [
            {
                "id": "kitchen_task_0",
                "title": "Paint",
                "description": "",
                "assigned_to": "person.john",
                "state": "done",
                "order": 0,
            },
            {
                "id": "kitchen_task_1",
                "title": "Fix",
                "description": "",
                "assigned_to": "person.jane",
                "state": "todo",
                "order": 1,
            },
        ],
    }
    mock_storage.save_story.return_value = None

    result = await story_manager.async_clone_story("kitchen", "Kitchen Copy")

    for task in result["story_data"]["tasks"]:
        assert task["assigned_to"] is None


@pytest.mark.asyncio
async def test_clone_story_renumbers_task_ids(story_manager, mock_storage):
    """Test that cloned task IDs use the new story_id as prefix."""
    mock_storage.async_story_exists.side_effect = [True, False]
    mock_storage.load_story.return_value = {
        "title": "Kitchen",
        "description": "",
        "tasks": [
            {
                "id": "kitchen_task_0",
                "title": "Task A",
                "description": "",
                "assigned_to": None,
                "state": "done",
                "order": 0,
            },
            {
                "id": "kitchen_task_1",
                "title": "Task B",
                "description": "",
                "assigned_to": None,
                "state": "done",
                "order": 1,
            },
        ],
    }
    mock_storage.save_story.return_value = None

    result = await story_manager.async_clone_story("kitchen", "Kitchen Copy")

    task_ids = [t["id"] for t in result["story_data"]["tasks"]]
    assert task_ids == ["kitchen_copy_task_0", "kitchen_copy_task_1"]


@pytest.mark.asyncio
async def test_clone_story_source_not_found(story_manager, mock_storage):
    """Test that cloning a non-existent story raises ValueError."""
    mock_storage.async_story_exists.return_value = False

    with pytest.raises(ValueError, match="Story 'nonexistent' not found"):
        await story_manager.async_clone_story("nonexistent")

    mock_storage.save_story.assert_not_called()


@pytest.mark.asyncio
async def test_clone_story_target_already_exists(story_manager, mock_storage):
    """Test that cloning to an existing story_id raises ValueError."""
    mock_storage.async_story_exists.side_effect = [
        True,  # source story exists
        True,  # new story ALREADY exists → conflict
    ]
    mock_storage.load_story.return_value = {
        "title": "Kitchen",
        "description": "",
        "tasks": [],
    }

    with pytest.raises(ValueError, match="already exists"):
        await story_manager.async_clone_story("kitchen", "Kitchen")

    mock_storage.save_story.assert_not_called()


@pytest.mark.asyncio
async def test_clone_story_persists_to_storage(story_manager, mock_storage):
    """Test that clone_story calls storage.save_story with the new story data."""
    mock_storage.async_story_exists.side_effect = [True, False]
    mock_storage.load_story.return_value = {
        "title": "Kitchen",
        "description": "My kitchen",
        "tasks": [
            {
                "id": "kitchen_task_0",
                "title": "Paint",
                "description": "Walls",
                "assigned_to": None,
                "state": "todo",
                "order": 0,
            },
        ],
    }
    mock_storage.save_story.return_value = None

    await story_manager.async_clone_story("kitchen", "Kitchen Copy")

    mock_storage.save_story.assert_called_once()
    call_args = mock_storage.save_story.call_args
    new_story_id = call_args[0][0]
    new_story_data = call_args[0][1]

    assert new_story_id == "kitchen_copy"
    assert new_story_data["title"] == "Kitchen Copy"
    assert new_story_data["description"] == "My kitchen"
    assert len(new_story_data["tasks"]) == 1
    assert new_story_data["tasks"][0]["state"] == "todo"


@pytest.mark.asyncio
async def test_clone_story_preserves_task_content(story_manager, mock_storage):
    """Test that task titles and descriptions are preserved in the clone."""
    mock_storage.async_story_exists.side_effect = [True, False]
    mock_storage.load_story.return_value = {
        "title": "Kitchen",
        "description": "",
        "tasks": [
            {
                "id": "kitchen_task_0",
                "title": "Paint walls",
                "description": "Use white paint",
                "assigned_to": None,
                "state": "done",
                "order": 0,
            },
        ],
    }
    mock_storage.save_story.return_value = None

    result = await story_manager.async_clone_story("kitchen", "Kitchen Copy")

    task = result["story_data"]["tasks"][0]
    assert task["title"] == "Paint walls"
    assert task["description"] == "Use white paint"


@pytest.mark.asyncio
async def test_clone_story_deep_copy_semantics(story_manager, mock_storage):
    """Test that cloned story data does not share references with the original.

    Mutating the cloned result must not affect the original source data that
    was returned by the storage layer, ensuring the clone operation performs a
    deep copy rather than a shallow one.
    """
    original_story_data = {
        "title": "Kitchen",
        "description": "Original description",
        "tasks": [
            {
                "id": "kitchen_task_0",
                "title": "Original Task",
                "description": "Original desc",
                "assigned_to": "person.john",
                "state": "done",
                "order": 0,
            }
        ],
    }

    mock_storage.async_story_exists.side_effect = [
        True,  # source story "kitchen" exists
        False,  # target story "kitchen_copy" does not yet exist
    ]
    mock_storage.load_story.return_value = original_story_data
    mock_storage.save_story.return_value = None

    result = await story_manager.async_clone_story("kitchen", "Kitchen Copy")

    # Mutate the cloned data
    result["story_data"]["tasks"][0]["title"] = "MUTATED TITLE"
    result["story_data"]["tasks"][0]["state"] = "MUTATED STATE"
    result["story_data"]["tasks"][0]["description"] = "MUTATED DESC"

    # Verify original source data is unchanged (deep copy semantics)
    assert original_story_data["tasks"][0]["title"] == "Original Task"
    assert original_story_data["tasks"][0]["state"] == "done"
    assert original_story_data["tasks"][0]["description"] == "Original desc"
