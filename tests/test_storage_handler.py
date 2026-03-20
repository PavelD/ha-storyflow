"""Test StorageHandler for StoryFlow."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.storyflow.storage_handler import StorageHandler


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    return hass


@pytest.fixture
def storage_handler(mock_hass):
    """Create a StorageHandler instance with mocked store."""
    handler = StorageHandler(mock_hass)
    handler.store.async_load = AsyncMock()
    handler.store.async_save = AsyncMock()
    return handler


@pytest.fixture
def sample_storage_data():
    """Create sample storage data with multiple stories."""
    return {
        "test_story": {
            "title": "Test Story",
            "description": "A test story",
            "tasks": [
                {
                    "id": "test_story_task_0",
                    "title": "Task 1",
                    "description": "First task",
                    "state": "todo",
                    "assigned_to": "person.john",
                },
                {
                    "id": "test_story_task_1",
                    "title": "Task 2",
                    "description": "Second task",
                    "state": "progress",
                    "assigned_to": None,
                },
            ],
        },
        "another_story": {
            "title": "Another Story",
            "description": "Another test story",
            "tasks": [
                {
                    "id": "another_story_task_0",
                    "title": "Task A",
                    "description": "Task in another story",
                    "state": "done",
                    "assigned_to": "person.jane",
                }
            ],
        },
    }


# =============================================================================
# Tests for save_story and load_story (existing methods)
# =============================================================================


@pytest.mark.asyncio
async def test_save_story(storage_handler):
    """Test saving a story to storage."""
    storage_handler.store.async_load.return_value = {}

    story_data = {
        "title": "New Story",
        "description": "A new story",
        "tasks": [],
    }

    await storage_handler.save_story("new_story", story_data)

    # Verify store was loaded and saved
    storage_handler.store.async_load.assert_called_once()
    storage_handler.store.async_save.assert_called_once()

    # Verify saved data includes our story
    saved_data = storage_handler.store.async_save.call_args[0][0]
    assert "new_story" in saved_data
    assert saved_data["new_story"] == story_data


@pytest.mark.asyncio
async def test_load_story_exists(storage_handler, sample_storage_data):
    """Test loading an existing story."""
    storage_handler.store.async_load.return_value = sample_storage_data

    result = await storage_handler.load_story("test_story")

    assert result is not None
    assert result["title"] == "Test Story"
    assert len(result["tasks"]) == 2


@pytest.mark.asyncio
async def test_load_story_not_found(storage_handler, sample_storage_data):
    """Test loading a non-existent story returns None."""
    storage_handler.store.async_load.return_value = sample_storage_data

    result = await storage_handler.load_story("missing_story")

    assert result is None


@pytest.mark.asyncio
async def test_load_story_empty_storage(storage_handler):
    """Test loading from empty storage returns None."""
    storage_handler.store.async_load.return_value = None

    result = await storage_handler.load_story("any_story")

    assert result is None


# =============================================================================
# Tests for async_load_all_stories
# =============================================================================


@pytest.mark.asyncio
async def test_async_load_all_stories(storage_handler, sample_storage_data):
    """Test loading all stories from storage."""
    storage_handler.store.async_load.return_value = sample_storage_data

    result = await storage_handler.async_load_all_stories()

    assert result == sample_storage_data
    assert len(result) == 2
    assert "test_story" in result
    assert "another_story" in result


@pytest.mark.asyncio
async def test_async_load_all_stories_empty(storage_handler):
    """Test loading all stories when storage is empty."""
    storage_handler.store.async_load.return_value = None

    result = await storage_handler.async_load_all_stories()

    assert result == {}


# =============================================================================
# Tests for async_story_exists
# =============================================================================


@pytest.mark.asyncio
async def test_async_story_exists_true(storage_handler, sample_storage_data):
    """Test story exists check returns True for existing story."""
    storage_handler.store.async_load.return_value = sample_storage_data

    result = await storage_handler.async_story_exists("test_story")

    assert result is True


@pytest.mark.asyncio
async def test_async_story_exists_false(storage_handler, sample_storage_data):
    """Test story exists check returns False for missing story."""
    storage_handler.store.async_load.return_value = sample_storage_data

    result = await storage_handler.async_story_exists("missing_story")

    assert result is False


@pytest.mark.asyncio
async def test_async_story_exists_empty_storage(storage_handler):
    """Test story exists check with empty storage."""
    storage_handler.store.async_load.return_value = None

    result = await storage_handler.async_story_exists("any_story")

    assert result is False


# =============================================================================
# Tests for async_get_task
# =============================================================================


@pytest.mark.asyncio
async def test_async_get_task_success(storage_handler, sample_storage_data):
    """Test getting a task that exists."""
    storage_handler.store.async_load.return_value = sample_storage_data

    result = await storage_handler.async_get_task("test_story", "test_story_task_0")

    assert result is not None
    assert result["id"] == "test_story_task_0"
    assert result["title"] == "Task 1"
    assert result["state"] == "todo"


@pytest.mark.asyncio
async def test_async_get_task_story_not_found(storage_handler, sample_storage_data):
    """Test getting a task from non-existent story returns None."""
    storage_handler.store.async_load.return_value = sample_storage_data

    result = await storage_handler.async_get_task("missing_story", "some_task")

    assert result is None


@pytest.mark.asyncio
async def test_async_get_task_task_not_found(storage_handler, sample_storage_data):
    """Test getting a non-existent task returns None."""
    storage_handler.store.async_load.return_value = sample_storage_data

    result = await storage_handler.async_get_task("test_story", "missing_task")

    assert result is None


# =============================================================================
# Tests for async_update_task
# =============================================================================


@pytest.mark.asyncio
async def test_async_update_task_success(storage_handler, sample_storage_data):
    """Test updating a task successfully."""
    storage_handler.store.async_load.return_value = sample_storage_data

    await storage_handler.async_update_task(
        "test_story",
        "test_story_task_0",
        {"state": "progress", "assigned_to": "person.jane"},
    )

    # Verify save was called
    storage_handler.store.async_save.assert_called_once()

    # Verify the task was updated in saved data
    saved_data = storage_handler.store.async_save.call_args[0][0]
    task = saved_data["test_story"]["tasks"][0]
    assert task["state"] == "progress"
    assert task["assigned_to"] == "person.jane"
    # Verify other fields unchanged
    assert task["title"] == "Task 1"


@pytest.mark.asyncio
async def test_async_update_task_story_not_found(storage_handler, sample_storage_data):
    """Test updating task in non-existent story raises ValueError."""
    storage_handler.store.async_load.return_value = sample_storage_data

    with pytest.raises(ValueError) as exc_info:
        await storage_handler.async_update_task(
            "missing_story", "some_task", {"state": "done"}
        )

    assert "missing_story" in str(exc_info.value)
    assert "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_async_update_task_task_not_found(storage_handler, sample_storage_data):
    """Test updating non-existent task raises ValueError."""
    storage_handler.store.async_load.return_value = sample_storage_data

    with pytest.raises(ValueError) as exc_info:
        await storage_handler.async_update_task(
            "test_story", "missing_task", {"state": "done"}
        )

    assert "missing_task" in str(exc_info.value)
    assert "not found" in str(exc_info.value).lower()


# =============================================================================
# Tests for async_add_task
# =============================================================================


@pytest.mark.asyncio
async def test_async_add_task_success(storage_handler, sample_storage_data):
    """Test adding a new task to a story."""
    storage_handler.store.async_load.return_value = sample_storage_data

    new_task = {
        "id": "test_story_task_2",
        "title": "New Task",
        "description": "A new task",
        "state": "todo",
        "assigned_to": None,
    }

    await storage_handler.async_add_task("test_story", new_task)

    # Verify save was called
    storage_handler.store.async_save.assert_called_once()

    # Verify task was added
    saved_data = storage_handler.store.async_save.call_args[0][0]
    assert len(saved_data["test_story"]["tasks"]) == 3
    assert saved_data["test_story"]["tasks"][2] == new_task


@pytest.mark.asyncio
async def test_async_add_task_story_not_found(storage_handler, sample_storage_data):
    """Test adding task to non-existent story raises ValueError."""
    storage_handler.store.async_load.return_value = sample_storage_data

    new_task = {"id": "some_task", "title": "Task"}

    with pytest.raises(ValueError) as exc_info:
        await storage_handler.async_add_task("missing_story", new_task)

    assert "missing_story" in str(exc_info.value)
    assert "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_async_add_task_missing_id(storage_handler, sample_storage_data):
    """Test adding task without ID raises ValueError."""
    storage_handler.store.async_load.return_value = sample_storage_data

    invalid_task = {"title": "Task without ID"}

    with pytest.raises(ValueError) as exc_info:
        await storage_handler.async_add_task("test_story", invalid_task)

    assert "id" in str(exc_info.value).lower()


# =============================================================================
# Tests for async_delete_task
# =============================================================================


@pytest.mark.asyncio
async def test_async_delete_task_success(storage_handler, sample_storage_data):
    """Test deleting a task successfully."""
    storage_handler.store.async_load.return_value = sample_storage_data

    await storage_handler.async_delete_task("test_story", "test_story_task_0")

    # Verify save was called
    storage_handler.store.async_save.assert_called_once()

    # Verify task was removed
    saved_data = storage_handler.store.async_save.call_args[0][0]
    assert len(saved_data["test_story"]["tasks"]) == 1
    assert saved_data["test_story"]["tasks"][0]["id"] == "test_story_task_1"


@pytest.mark.asyncio
async def test_async_delete_task_story_not_found(storage_handler, sample_storage_data):
    """Test deleting task from non-existent story raises ValueError."""
    storage_handler.store.async_load.return_value = sample_storage_data

    with pytest.raises(ValueError) as exc_info:
        await storage_handler.async_delete_task("missing_story", "some_task")

    assert "missing_story" in str(exc_info.value)
    assert "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_async_delete_task_task_not_found(storage_handler, sample_storage_data):
    """Test deleting non-existent task raises ValueError."""
    storage_handler.store.async_load.return_value = sample_storage_data

    with pytest.raises(ValueError) as exc_info:
        await storage_handler.async_delete_task("test_story", "missing_task")

    assert "missing_task" in str(exc_info.value)
    assert "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_async_delete_last_task(storage_handler):
    """Test deleting the last task from a story."""
    storage_data = {
        "single_task_story": {
            "title": "Story",
            "description": "Story with one task",
            "tasks": [{"id": "task_0", "title": "Only Task", "state": "todo"}],
        }
    }
    storage_handler.store.async_load.return_value = storage_data

    await storage_handler.async_delete_task("single_task_story", "task_0")

    # Verify task list is now empty
    saved_data = storage_handler.store.async_save.call_args[0][0]
    assert len(saved_data["single_task_story"]["tasks"]) == 0
