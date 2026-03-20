"""Test TaskEntity for StoryFlow."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.storyflow.task_entity import TaskEntity
from custom_components.storyflow.const import DOMAIN, TASK_STATES


@pytest.fixture
def mock_storage_handler():
    """Create a mock storage handler for testing."""
    storage = MagicMock()
    storage.load_story = AsyncMock()
    storage.save_story = AsyncMock()
    storage.async_update_task = AsyncMock()
    return storage


@pytest.fixture
def sample_story_data():
    """Create sample story data for testing."""
    return {
        "title": "Test Story",
        "description": "A test story",
        "tasks": [
            {
                "id": "test_story_task_0",
                "title": "Test Task",
                "description": "This is a test task",
                "assigned_to": "person.john",
                "state": "todo",
            }
        ],
    }


def test_task_entity_init(mock_storage_handler):
    """Test TaskEntity initialization with valid data."""
    entity = TaskEntity(
        story_id="test_story",
        task_id="test_story_task_0",
        title="Test Task",
        description="This is a test task",
        storage_handler=mock_storage_handler,
        assigned_to="person.john",
        state="todo",
        order=0,
    )

    assert entity.story_id == "test_story"
    assert entity.task_id == "test_story_task_0"
    assert entity.title == "Test Task"
    assert entity.description == "This is a test task"
    assert entity.assigned_to == "person.john"
    assert entity.state == "todo"
    assert entity.order == 0


def test_task_entity_unique_id(mock_storage_handler):
    """Test TaskEntity unique_id format."""
    entity = TaskEntity(
        story_id="test_story",
        task_id="test_story_task_0",
        title="Test Task",
        description="Test",
        storage_handler=mock_storage_handler,
        state="todo",
    )

    # unique_id should include DOMAIN prefix
    assert entity.unique_id == f"{DOMAIN}_test_story_task_0"


def test_task_entity_name(mock_storage_handler):
    """Test TaskEntity name format."""
    entity = TaskEntity(
        story_id="test_story",
        task_id="test_story_task_0",
        title="Test Task",
        description="Test",
        storage_handler=mock_storage_handler,
        state="todo",
    )

    # Name should be "story_id: title"
    assert entity.name == "test_story: Test Task"


def test_task_entity_state(mock_storage_handler):
    """Test TaskEntity state property."""
    entity = TaskEntity(
        story_id="test_story",
        task_id="test_story_task_0",
        title="Test Task",
        description="Test",
        storage_handler=mock_storage_handler,
        state="progress",
    )

    assert entity.state == "progress"


def test_task_entity_invalid_state(mock_storage_handler):
    """Test TaskEntity raises ValueError for invalid state."""
    with pytest.raises(ValueError) as exc_info:
        TaskEntity(
            story_id="test_story",
            task_id="test_story_task_0",
            title="Test Task",
            description="Test",
            storage_handler=mock_storage_handler,
            state="invalid_state",
        )

    # Verify error message mentions the invalid state and valid states
    assert "invalid_state" in str(exc_info.value)
    assert str(TASK_STATES) in str(exc_info.value)


def test_task_entity_all_valid_states(mock_storage_handler):
    """Test TaskEntity accepts all defined task states."""
    for state in TASK_STATES:
        entity = TaskEntity(
            story_id="test_story",
            task_id="test_story_task_0",
            title="Test Task",
            description="Test",
            storage_handler=mock_storage_handler,
            state=state,
        )
        assert entity.state == state


def test_task_entity_extra_state_attributes(mock_storage_handler):
    """Test TaskEntity extra_state_attributes are complete."""
    entity = TaskEntity(
        story_id="test_story",
        task_id="test_story_task_0",
        title="Test Task",
        description="This is a test task",
        storage_handler=mock_storage_handler,
        assigned_to="person.john",
        state="progress",
        order=5,
    )

    attributes = entity.extra_state_attributes

    assert attributes["story_id"] == "test_story"
    assert attributes["task_id"] == "test_story_task_0"
    assert attributes["title"] == "Test Task"
    assert attributes["description"] == "This is a test task"
    assert attributes["assigned_to"] == "person.john"
    assert attributes["order"] == 5


def test_task_entity_optional_fields(mock_storage_handler):
    """Test TaskEntity with optional fields as None."""
    entity = TaskEntity(
        story_id="test_story",
        task_id="test_story_task_0",
        title="Test Task",
        description="Test",
        storage_handler=mock_storage_handler,
        assigned_to=None,
        state="todo",
        order=None,
    )

    attributes = entity.extra_state_attributes
    assert attributes["assigned_to"] is None
    assert attributes["order"] is None


def test_task_entity_device_info(mock_storage_handler):
    """Test TaskEntity device_info groups tasks under story."""
    entity = TaskEntity(
        story_id="my_story",
        task_id="my_story_task_0",
        title="Test Task",
        description="Test",
        storage_handler=mock_storage_handler,
        state="todo",
    )

    device_info = entity.device_info

    # Verify device identifiers include the story_id
    assert (DOMAIN, "my_story") in device_info["identifiers"]

    # Verify device name includes the story_id
    assert "my_story" in device_info["name"]

    # Verify manufacturer and model
    assert device_info["manufacturer"] == "StoryFlow"
    assert device_info["model"] == "Story"


def test_task_entity_device_info_grouping(mock_storage_handler):
    """Test that multiple tasks share the same device_info."""
    entity1 = TaskEntity(
        story_id="shared_story",
        task_id="shared_story_task_0",
        title="Task 1",
        description="Test",
        storage_handler=mock_storage_handler,
        state="todo",
    )

    entity2 = TaskEntity(
        story_id="shared_story",
        task_id="shared_story_task_1",
        title="Task 2",
        description="Test",
        storage_handler=mock_storage_handler,
        state="done",
    )

    # Both should have the same device identifiers
    assert entity1.device_info["identifiers"] == entity2.device_info["identifiers"]


# ============================================================================
# Tests for Writable Entity Methods (Phase 1.1)
# ============================================================================


@pytest.mark.asyncio
async def test_async_update_state(mock_storage_handler, sample_story_data):
    """Test updating task state persists to storage."""
    entity = TaskEntity(
        story_id="test_story",
        task_id="test_story_task_0",
        title="Test Task",
        description="Test",
        storage_handler=mock_storage_handler,
        state="todo",
    )

    with patch.object(entity, "async_write_ha_state") as mock_write_state:
        await entity.async_update_state("progress")

        # Verify state updated internally
        assert entity.state == "progress"

        # Verify async_update_task was called with correct arguments
        mock_storage_handler.async_update_task.assert_called_once_with(
            "test_story", "test_story_task_0", {"state": "progress"}
        )

        # Verify Home Assistant was notified
        mock_write_state.assert_called_once()


@pytest.mark.asyncio
async def test_async_update_state_invalid(mock_storage_handler, sample_story_data):
    """Test updating task state with invalid state raises ValueError."""
    entity = TaskEntity(
        story_id="test_story",
        task_id="test_story_task_0",
        title="Test Task",
        description="Test",
        storage_handler=mock_storage_handler,
        state="todo",
    )

    with pytest.raises(ValueError) as exc_info:
        await entity.async_update_state("invalid_state")

    assert "invalid_state" in str(exc_info.value)
    assert str(TASK_STATES) in str(exc_info.value)


@pytest.mark.asyncio
async def test_async_update_assignment(mock_storage_handler, sample_story_data):
    """Test updating task assignment persists to storage."""
    entity = TaskEntity(
        story_id="test_story",
        task_id="test_story_task_0",
        title="Test Task",
        description="Test",
        storage_handler=mock_storage_handler,
        state="todo",
        assigned_to=None,
    )

    with patch.object(entity, "async_write_ha_state") as mock_write_state:
        await entity.async_update_assignment("person.jane")

        # Verify assignment updated internally
        assert entity.assigned_to == "person.jane"

        # Verify async_update_task was called with correct arguments
        mock_storage_handler.async_update_task.assert_called_once_with(
            "test_story", "test_story_task_0", {"assigned_to": "person.jane"}
        )

        # Verify Home Assistant was notified
        mock_write_state.assert_called_once()


@pytest.mark.asyncio
async def test_async_update_assignment_unassign(
    mock_storage_handler, sample_story_data
):
    """Test unassigning a task (setting to None)."""
    entity = TaskEntity(
        story_id="test_story",
        task_id="test_story_task_0",
        title="Test Task",
        description="Test",
        storage_handler=mock_storage_handler,
        state="todo",
        assigned_to="person.john",
    )

    with patch.object(entity, "async_write_ha_state") as mock_write_state:
        await entity.async_update_assignment(None)

        # Verify assignment cleared
        assert entity.assigned_to is None

        # Verify async_update_task was called with None
        mock_storage_handler.async_update_task.assert_called_once_with(
            "test_story", "test_story_task_0", {"assigned_to": None}
        )


@pytest.mark.asyncio
async def test_async_update_attributes_single(mock_storage_handler, sample_story_data):
    """Test updating a single attribute."""
    entity = TaskEntity(
        story_id="test_story",
        task_id="test_story_task_0",
        title="Old Title",
        description="Test",
        storage_handler=mock_storage_handler,
        state="todo",
    )

    with patch.object(entity, "async_write_ha_state") as mock_write_state:
        await entity.async_update_attributes(title="New Title")

        # Verify attribute updated
        assert entity.title == "New Title"

        # Verify async_update_task was called
        mock_storage_handler.async_update_task.assert_called_once_with(
            "test_story", "test_story_task_0", {"title": "New Title"}
        )

        mock_write_state.assert_called_once()


@pytest.mark.asyncio
async def test_async_update_attributes_multiple(
    mock_storage_handler, sample_story_data
):
    """Test updating multiple attributes at once."""
    entity = TaskEntity(
        story_id="test_story",
        task_id="test_story_task_0",
        title="Old Title",
        description="Old Description",
        storage_handler=mock_storage_handler,
        state="todo",
        assigned_to=None,
        order=0,
    )

    with patch.object(entity, "async_write_ha_state") as mock_write_state:
        await entity.async_update_attributes(
            title="New Title",
            description="New Description",
            state="progress",
            assigned_to="person.john",
            order=5,
        )

        # Verify all attributes updated
        assert entity.title == "New Title"
        assert entity.description == "New Description"
        assert entity.state == "progress"
        assert entity.assigned_to == "person.john"
        assert entity.order == 5

        # Verify async_update_task was called with all updates
        mock_storage_handler.async_update_task.assert_called_once_with(
            "test_story",
            "test_story_task_0",
            {
                "title": "New Title",
                "description": "New Description",
                "state": "progress",
                "assigned_to": "person.john",
                "order": 5,
            },
        )


@pytest.mark.asyncio
async def test_async_update_attributes_invalid_attribute(mock_storage_handler):
    """Test updating with invalid attribute name raises ValueError."""
    entity = TaskEntity(
        story_id="test_story",
        task_id="test_story_task_0",
        title="Test Task",
        description="Test",
        storage_handler=mock_storage_handler,
        state="todo",
    )

    with pytest.raises(ValueError) as exc_info:
        await entity.async_update_attributes(invalid_field="value")

    assert "invalid_field" in str(exc_info.value)


@pytest.mark.asyncio
async def test_async_update_attributes_invalid_state(mock_storage_handler):
    """Test updating state to invalid value raises ValueError."""
    entity = TaskEntity(
        story_id="test_story",
        task_id="test_story_task_0",
        title="Test Task",
        description="Test",
        storage_handler=mock_storage_handler,
        state="todo",
    )

    with pytest.raises(ValueError) as exc_info:
        await entity.async_update_attributes(state="invalid_state")

    assert "invalid_state" in str(exc_info.value)


@pytest.mark.asyncio
async def test_persist_to_storage_story_not_found(mock_storage_handler):
    """Test error handling when story not found in storage."""
    # Configure async_update_task to raise ValueError
    mock_storage_handler.async_update_task.side_effect = ValueError(
        "Story 'missing_story' not found"
    )

    entity = TaskEntity(
        story_id="missing_story",
        task_id="missing_story_task_0",
        title="Test Task",
        description="Test",
        storage_handler=mock_storage_handler,
        state="todo",
    )

    with pytest.raises(ValueError) as exc_info:
        await entity.async_update_state("progress")

    assert "missing_story" in str(exc_info.value)
    assert "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_persist_to_storage_task_not_found(mock_storage_handler):
    """Test error handling when task not found in story."""
    # Configure async_update_task to raise ValueError
    mock_storage_handler.async_update_task.side_effect = ValueError(
        "Task 'missing_task_id' not found in story 'test_story'"
    )

    entity = TaskEntity(
        story_id="test_story",
        task_id="missing_task_id",
        title="Test Task",
        description="Test",
        storage_handler=mock_storage_handler,
        state="todo",
    )

    with pytest.raises(ValueError) as exc_info:
        await entity.async_update_state("progress")

    assert "missing_task_id" in str(exc_info.value)
    assert "not found" in str(exc_info.value).lower()
