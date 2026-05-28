"""Tests for the Storyflow select platform and TaskEntity UI interactions."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.storyflow.const import DOMAIN
from custom_components.storyflow.select import async_setup_entry
from custom_components.storyflow.task_entity import TaskEntity

# =============================================================================
# Helpers / shared fixtures
# =============================================================================


def _make_mock_entry(story_id="story-1", story_name="Test Story", tasks=None):
    """Return a minimal mock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = "test-entry-id"
    entry.data = {
        "story_id": story_id,
        "story_name": story_name,
        "tasks": tasks or [],
    }
    return entry


def _make_mock_storage(story_data):
    """Return an AsyncMock storage handler that returns *story_data* from load_story."""
    storage = AsyncMock()
    storage.load_story = AsyncMock(return_value=story_data)
    storage.async_update_task = AsyncMock(return_value=None)
    return storage


def _make_hass(storage, story_id="story-1"):
    """Return a minimal mock hass with domain data pre-populated."""
    hass = MagicMock()
    hass.data = {
        DOMAIN: {
            "task_entities": {},
            "entries": {
                "test-entry-id": {
                    "storage": storage,
                    "manager": MagicMock(),
                }
            },
        }
    }
    return hass


# =============================================================================
# Tests for async_setup_entry (select platform)
# =============================================================================


@pytest.mark.asyncio
async def test_select_setup_entry_loads_tasks_from_storage():
    """select.async_setup_entry should load tasks from storage, not entry.data."""
    stored_tasks = [
        {"id": "task-1", "title": "Stored Task 1", "state": "todo"},
        {"id": "task-2", "title": "Stored Task 2", "state": "done"},
    ]
    storage = _make_mock_storage(
        {
            "id": "story-1",
            "title": "Test Story",
            "tasks": stored_tasks,
        }
    )
    hass = _make_hass(storage)
    entry = _make_mock_entry(tasks=[])  # entry.data has no tasks → must use storage
    async_add_entities = MagicMock()

    result = await async_setup_entry(hass, entry, async_add_entities)

    assert result is True
    storage.load_story.assert_called_once_with("story-1")
    # Two entities (one per task) should be registered
    added = async_add_entities.call_args[0][0]
    assert len(added) == 2
    task_ids = {e.task_id for e in added}
    assert task_ids == {"task-1", "task-2"}


@pytest.mark.asyncio
async def test_select_setup_entry_falls_back_to_entry_data_when_storage_empty():
    """When storage returns None, tasks should be read from entry.data."""
    storage = _make_mock_storage(None)  # storage has no data
    hass = _make_hass(storage)
    entry = _make_mock_entry(
        tasks=[{"id": "entry-task-1", "title": "Entry Task", "state": "todo"}]
    )
    async_add_entities = MagicMock()

    result = await async_setup_entry(hass, entry, async_add_entities)

    assert result is True
    added = async_add_entities.call_args[0][0]
    assert len(added) == 1
    assert added[0].task_id == "entry-task-1"


@pytest.mark.asyncio
async def test_select_setup_entry_handles_legacy_tasks_without_id():
    """Tasks without an 'id' field should get a generated id (migration path)."""
    stored_tasks = [
        {"title": "Legacy Task 1"},  # no id
        {"title": "Legacy Task 2"},  # no id
    ]
    storage = _make_mock_storage({"tasks": stored_tasks})
    hass = _make_hass(storage)
    entry = _make_mock_entry()
    async_add_entities = MagicMock()

    await async_setup_entry(hass, entry, async_add_entities)

    added = async_add_entities.call_args[0][0]
    assert len(added) == 2
    # Every entity must have a non-empty task_id
    for entity in added:
        assert entity.task_id
        assert entity.task_id != ""


@pytest.mark.asyncio
async def test_select_setup_entry_registers_entity_callbacks():
    """async_setup_entry should register async_add_entities under entity_callbacks."""
    storage = _make_mock_storage({"tasks": []})
    hass = _make_hass(storage)
    entry = _make_mock_entry()
    async_add_entities = MagicMock()

    await async_setup_entry(hass, entry, async_add_entities)

    callbacks = hass.data[DOMAIN].get("entity_callbacks", {})
    assert "story-1" in callbacks
    assert callbacks["story-1"] is async_add_entities


@pytest.mark.asyncio
async def test_select_setup_entry_registers_task_entities_in_hass_data():
    """Each created TaskEntity should be stored in hass.data[DOMAIN]['task_entities']."""
    stored_tasks = [
        {"id": "task-a", "title": "Task A", "state": "todo"},
        {"id": "task-b", "title": "Task B", "state": "progress"},
    ]
    storage = _make_mock_storage({"tasks": stored_tasks})
    hass = _make_hass(storage)
    entry = _make_mock_entry()
    async_add_entities = MagicMock()

    await async_setup_entry(hass, entry, async_add_entities)

    task_entities = hass.data[DOMAIN]["task_entities"]
    assert "task-a" in task_entities
    assert "task-b" in task_entities
    assert isinstance(task_entities["task-a"], TaskEntity)
    assert isinstance(task_entities["task-b"], TaskEntity)


# =============================================================================
# Tests for TaskEntity._async_refresh_progress
# =============================================================================


@pytest.mark.asyncio
async def test_async_refresh_progress_updates_progress_entity():
    """_async_refresh_progress should push the latest task list to the progress entity."""
    storage = AsyncMock()
    storage.load_story = AsyncMock(
        return_value={"tasks": [{"id": "t1", "state": "done"}]}
    )
    storage.async_update_task = AsyncMock(return_value=None)

    progress_entity = MagicMock()
    progress_entity.async_write_ha_state = MagicMock()

    entity = TaskEntity(
        story_id="story-1",
        task_id="t1",
        title="My Task",
        description="",
        storage_handler=storage,
        state="todo",
        progress_entity=progress_entity,
    )

    await entity._async_refresh_progress()

    assert progress_entity.tasks == [{"id": "t1", "state": "done"}]
    progress_entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_async_refresh_progress_handles_none_story_data():
    """When load_story returns None, tasks should be treated as empty list."""
    storage = AsyncMock()
    storage.load_story = AsyncMock(return_value=None)

    progress_entity = MagicMock()
    progress_entity.async_write_ha_state = MagicMock()

    entity = TaskEntity(
        story_id="story-1",
        task_id="t1",
        title="My Task",
        description="",
        storage_handler=storage,
        state="todo",
        progress_entity=progress_entity,
    )

    # Should not raise; should treat missing story as empty task list
    await entity._async_refresh_progress()

    assert progress_entity.tasks == []
    progress_entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_async_refresh_progress_handles_non_dict_story_data():
    """When load_story returns a non-dict, tasks should be treated as empty list."""
    storage = AsyncMock()
    storage.load_story = AsyncMock(return_value="unexpected string")

    progress_entity = MagicMock()
    progress_entity.async_write_ha_state = MagicMock()

    entity = TaskEntity(
        story_id="story-1",
        task_id="t1",
        title="My Task",
        description="",
        storage_handler=storage,
        state="todo",
        progress_entity=progress_entity,
    )

    await entity._async_refresh_progress()

    assert progress_entity.tasks == []
    progress_entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_async_refresh_progress_skips_when_no_progress_entity():
    """_async_refresh_progress should be a no-op when progress_entity is None."""
    storage = AsyncMock()
    storage.load_story = AsyncMock(return_value={"tasks": []})

    entity = TaskEntity(
        story_id="story-1",
        task_id="t1",
        title="My Task",
        description="",
        storage_handler=storage,
        state="todo",
        progress_entity=None,
    )

    # Should not raise and should not call load_story
    await entity._async_refresh_progress()

    storage.load_story.assert_not_called()


@pytest.mark.asyncio
async def test_async_refresh_progress_logs_warning_on_storage_error():
    """Storage errors in _async_refresh_progress should be caught and logged."""
    import logging

    storage = AsyncMock()
    storage.load_story = AsyncMock(side_effect=OSError("disk failure"))

    progress_entity = MagicMock()
    progress_entity.async_write_ha_state = MagicMock()

    entity = TaskEntity(
        story_id="story-1",
        task_id="t1",
        title="My Task",
        description="",
        storage_handler=storage,
        state="todo",
        progress_entity=progress_entity,
    )

    # Should not raise; warning should be logged instead
    with patch("custom_components.storyflow.task_entity._LOGGER") as mock_logger:
        await entity._async_refresh_progress()
        mock_logger.warning.assert_called_once()

    # Progress entity state must NOT have been written on error
    progress_entity.async_write_ha_state.assert_not_called()


# =============================================================================
# Tests for TaskEntity.async_select_option (UI dropdown interaction)
# =============================================================================


@pytest.mark.asyncio
async def test_async_select_option_persists_state_and_refreshes_progress():
    """async_select_option should update storage, in-memory state, and progress entity."""
    storage = AsyncMock()
    storage.async_update_task = AsyncMock(return_value=None)
    storage.load_story = AsyncMock(
        return_value={"tasks": [{"id": "t1", "state": "done"}]}
    )

    progress_entity = MagicMock()
    progress_entity.async_write_ha_state = MagicMock()

    entity = TaskEntity(
        story_id="story-1",
        task_id="t1",
        title="My Task",
        description="",
        storage_handler=storage,
        state="todo",
        progress_entity=progress_entity,
    )
    entity.async_write_ha_state = MagicMock()

    await entity.async_select_option("done")

    # Storage should have been called to persist the new state
    storage.async_update_task.assert_called_once_with(
        "story-1", "t1", {"state": "done"}
    )
    # In-memory state should reflect the new value
    assert entity._state == "done"
    # Task entity's own HA state should be written
    entity.async_write_ha_state.assert_called_once()
    # Progress entity should have been refreshed
    progress_entity.async_write_ha_state.assert_called_once()
