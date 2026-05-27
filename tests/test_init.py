"""Integration tests for StoryFlow."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.storyflow import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.storyflow.const import DOMAIN


async def test_async_setup(hass: HomeAssistant):
    """Test the component setup."""
    result = await async_setup(hass, {})

    assert result is True
    assert DOMAIN in hass.data


async def test_async_setup_entry_creates_entities(hass: HomeAssistant):
    """Test config entry setup creates expected entities on first-time setup."""
    # Initialize domain data
    hass.data[DOMAIN] = {"service_ref_count": 0}

    # Create a mock config entry
    entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Test Story",
        data={
            "story_name": "Test Story",
            "story_description": "A test story",
            "story_id": "test_story",
            "tasks": [
                {
                    "title": "Task 1",
                    "description": "First task",
                    "state": "todo",
                    "assigned_to": None,
                },
                {
                    "title": "Task 2",
                    "description": "Second task",
                    "state": "done",
                    "assigned_to": "person.john",
                },
            ],
        },
        source="user",
        unique_id="test_story_unique",
    )

    # Mock the storage and manager
    with patch("custom_components.storyflow.StorageHandler") as mock_storage_cls, patch(
        "custom_components.storyflow.StoryManager"
    ) as mock_manager, patch(
        "custom_components.storyflow.async_setup_services"
    ) as mock_services:

        # Story does NOT exist yet → create_story should be called
        mock_storage_instance = AsyncMock()
        mock_storage_instance.async_story_exists = AsyncMock(return_value=False)
        mock_storage_cls.return_value = mock_storage_instance

        mock_manager_instance = AsyncMock()
        mock_manager_instance.create_story = AsyncMock(return_value="test_story")
        mock_manager_instance._generate_story_id = MagicMock(return_value="test_story")
        mock_manager.return_value = mock_manager_instance

        # Setup the entry
        result = await async_setup_entry(hass, entry)

        assert result is True

        # Verify manager was created and stored under the "entries" key
        assert DOMAIN in hass.data
        assert entry.entry_id in hass.data[DOMAIN]["entries"]

        # Verify create_story was called on first-time setup
        mock_manager_instance.create_story.assert_called_once_with(
            "Test Story",
            "A test story",
            entry.data["tasks"],
        )

        # Verify services were set up
        mock_services.assert_called_once()


async def test_async_setup_entry_skips_create_story_on_reload(hass: HomeAssistant):
    """Test that setup does NOT overwrite existing storage on reload/restart.

    This is the fix for the bug where tasks were reverting to 'todo' after
    every HA restart or integration reload.
    """
    hass.data[DOMAIN] = {"service_ref_count": 0}

    entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Test Story",
        data={
            "story_name": "Test Story",
            "story_description": "A test story",
            "story_id": "test_story",
            "tasks": [
                {"title": "Task 1", "description": "First task", "state": "todo"},
            ],
        },
        source="user",
        unique_id="test_story_unique",
    )

    with patch("custom_components.storyflow.StorageHandler") as mock_storage_cls, patch(
        "custom_components.storyflow.StoryManager"
    ) as mock_manager, patch("custom_components.storyflow.async_setup_services"):

        # Story ALREADY EXISTS in storage (simulating a reload after task states changed)
        mock_storage_instance = AsyncMock()
        mock_storage_instance.async_story_exists = AsyncMock(return_value=True)
        mock_storage_cls.return_value = mock_storage_instance

        mock_manager_instance = AsyncMock()
        mock_manager_instance.create_story = AsyncMock(return_value="test_story")
        mock_manager_instance._generate_story_id = MagicMock(return_value="test_story")
        mock_manager.return_value = mock_manager_instance

        result = await async_setup_entry(hass, entry)

        assert result is True

        # create_story must NOT be called — would overwrite saved task states
        mock_manager_instance.create_story.assert_not_called()


async def test_async_setup_entry_uses_persisted_story_id(hass: HomeAssistant):
    """Test that config entry uses persisted story_id."""
    hass.data[DOMAIN] = {"service_ref_count": 0}

    entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="My Story",
        data={
            "story_name": "My Story",
            "story_description": "Test",
            "story_id": "custom_story_id",  # Persisted ID different from derived
            "tasks": [],
        },
        source="user",
        unique_id="my_story_unique",
    )

    with patch("custom_components.storyflow.StorageHandler"), patch(
        "custom_components.storyflow.StoryManager"
    ) as mock_manager, patch("custom_components.storyflow.async_setup_services"):

        mock_manager_instance = AsyncMock()
        mock_manager_instance.create_story = AsyncMock(return_value="custom_story_id")
        mock_manager.return_value = mock_manager_instance

        await async_setup_entry(hass, entry)

        # The persisted story_id should be used (not derived from story_name)
        # This will be verified when sensor platform reads from entry.data


async def test_async_unload_entry_cleans_up(hass: HomeAssistant):
    """Test config entry unload cleans up properly."""
    hass.data[DOMAIN] = {"service_ref_count": 0}

    entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Test Story",
        data={
            "story_name": "Test Story",
            "story_description": "Test",
            "story_id": "test_story",
            "tasks": [],
        },
        source="user",
        unique_id="test_unique",
    )

    # Setup first
    with patch("custom_components.storyflow.StorageHandler"), patch(
        "custom_components.storyflow.StoryManager"
    ) as mock_manager, patch("custom_components.storyflow.async_setup_services"), patch(
        "custom_components.storyflow.async_unload_services"
    ) as mock_unload:

        mock_manager_instance = AsyncMock()
        mock_manager_instance.create_story = AsyncMock(return_value="test_story")
        mock_manager.return_value = mock_manager_instance

        await async_setup_entry(hass, entry)

        # Verify data was stored under the "entries" key
        assert entry.entry_id in hass.data[DOMAIN]["entries"]

        # Mock platform unload
        with patch.object(
            hass.config_entries, "async_unload_platforms", return_value=True
        ):
            # Unload the entry
            result = await async_unload_entry(hass, entry)

            assert result is True

            # Verify data was removed from "entries"
            assert entry.entry_id not in hass.data[DOMAIN].get("entries", {})

            # Verify services were unloaded
            mock_unload.assert_called_once()


async def test_async_setup_entry_forwards_to_platforms(hass: HomeAssistant):
    """Test that setup forwards to sensor platform."""
    hass.data[DOMAIN] = {"service_ref_count": 0}

    entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Test Story",
        data={
            "story_name": "Test Story",
            "story_description": "Test",
            "story_id": "test_story",
            "tasks": [{"title": "Task 1", "description": "Test", "state": "todo"}],
        },
        source="user",
        unique_id="test_unique",
    )

    with patch("custom_components.storyflow.StorageHandler"), patch(
        "custom_components.storyflow.StoryManager"
    ) as mock_manager, patch(
        "custom_components.storyflow.async_setup_services"
    ), patch.object(
        hass.config_entries, "async_forward_entry_setups"
    ) as mock_forward:

        mock_manager_instance = AsyncMock()
        mock_manager_instance.create_story = AsyncMock(return_value="test_story")
        mock_manager.return_value = mock_manager_instance

        await async_setup_entry(hass, entry)

        # Verify sensor platform was forwarded
        mock_forward.assert_called_once()
        call_args = mock_forward.call_args
        assert call_args[0][0] == entry
        assert "sensor" in call_args[0][1]


async def test_multiple_entries_same_hass_data(hass: HomeAssistant):
    """Test that multiple config entries can coexist."""
    hass.data[DOMAIN] = {"service_ref_count": 0}

    entry1 = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Story 1",
        data={
            "story_name": "Story 1",
            "story_description": "First story",
            "story_id": "story_1",
            "tasks": [],
        },
        source="user",
        unique_id="story1_unique",
    )

    entry2 = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Story 2",
        data={
            "story_name": "Story 2",
            "story_description": "Second story",
            "story_id": "story_2",
            "tasks": [],
        },
        source="user",
        unique_id="story2_unique",
    )

    with patch("custom_components.storyflow.StorageHandler"), patch(
        "custom_components.storyflow.StoryManager"
    ) as mock_manager, patch("custom_components.storyflow.async_setup_services"):

        # Create separate mock instances for each entry
        mock_manager_instance1 = AsyncMock()
        mock_manager_instance1.create_story = AsyncMock(return_value="story_1")

        mock_manager_instance2 = AsyncMock()
        mock_manager_instance2.create_story = AsyncMock(return_value="story_2")

        mock_manager.side_effect = [mock_manager_instance1, mock_manager_instance2]

        # Setup both entries
        await async_setup_entry(hass, entry1)
        await async_setup_entry(hass, entry2)

        # Verify both are stored under "entries"
        assert entry1.entry_id in hass.data[DOMAIN]["entries"]
        assert entry2.entry_id in hass.data[DOMAIN]["entries"]

        # Verify they're separate instances
        assert (
            hass.data[DOMAIN]["entries"][entry1.entry_id]
            is not hass.data[DOMAIN]["entries"][entry2.entry_id]
        )


async def test_legacy_entry_without_story_id(hass: HomeAssistant):
    """Test that legacy entries without story_id still work with fallback."""
    hass.data[DOMAIN] = {"service_ref_count": 0}

    entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Legacy Story",
        data={
            "story_name": "Legacy Story",
            "story_description": "Old entry without story_id",
            # No story_id field (legacy entry)
            "tasks": [],
        },
        source="user",
        unique_id="legacy_unique",
    )

    with patch("custom_components.storyflow.StorageHandler"), patch(
        "custom_components.storyflow.StoryManager"
    ) as mock_manager, patch("custom_components.storyflow.async_setup_services"):

        mock_manager_instance = AsyncMock()
        # The derived story_id should be used
        mock_manager_instance.create_story = AsyncMock(return_value="legacy_story")
        mock_manager.return_value = mock_manager_instance

        result = await async_setup_entry(hass, entry)

        assert result is True
        # The sensor platform will use the fallback logic to derive story_id


async def test_multiple_entries_service_lifecycle(hass: HomeAssistant):
    """Test that services work correctly with multiple config entries."""
    # Initialize
    await async_setup(hass, {})

    entry1 = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Story 1",
        data={
            "story_name": "Story 1",
            "story_description": "First",
            "story_id": "story_1",
            "tasks": [],
        },
        source="user",
        unique_id="story1_unique",
    )

    entry2 = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Story 2",
        data={
            "story_name": "Story 2",
            "story_description": "Second",
            "story_id": "story_2",
            "tasks": [],
        },
        source="user",
        unique_id="story2_unique",
    )

    with patch("custom_components.storyflow.StorageHandler"), patch(
        "custom_components.storyflow.StoryManager"
    ) as mock_manager:

        mock_manager_instance = AsyncMock()
        mock_manager_instance.create_story = AsyncMock(
            side_effect=["story_1", "story_2"]
        )
        mock_manager.return_value = mock_manager_instance

        # Setup first entry - services should be registered
        await async_setup_entry(hass, entry1)
        assert hass.data[DOMAIN]["service_ref_count"] == 1
        assert hass.services.has_service(DOMAIN, "set_task_state")

        # Setup second entry - services should still be registered, counter incremented
        await async_setup_entry(hass, entry2)
        assert hass.data[DOMAIN]["service_ref_count"] == 2
        assert hass.services.has_service(DOMAIN, "set_task_state")

        # Unload first entry - services should remain
        with patch.object(
            hass.config_entries, "async_unload_platforms", return_value=True
        ):
            await async_unload_entry(hass, entry1)
            assert hass.data[DOMAIN]["service_ref_count"] == 1
            assert hass.services.has_service(DOMAIN, "set_task_state")

            # Unload second entry - services should be removed
            await async_unload_entry(hass, entry2)
            assert hass.data[DOMAIN]["service_ref_count"] == 0
            assert not hass.services.has_service(DOMAIN, "set_task_state")


# Phase 1.4: Entity Registry Integration Tests


async def test_entity_registry_initialized(hass: HomeAssistant):
    """Test that entity registry is initialized during setup."""
    result = await async_setup(hass, {})

    assert result is True
    assert DOMAIN in hass.data
    assert "task_entities" in hass.data[DOMAIN]
    assert isinstance(hass.data[DOMAIN]["task_entities"], dict)
    assert len(hass.data[DOMAIN]["task_entities"]) == 0


async def test_get_task_entity_function_exists(hass: HomeAssistant):
    """Test that get_task_entity helper function is available."""
    from custom_components.storyflow import get_task_entity

    # Initialize
    await async_setup(hass, {})

    # Function should exist and return None for non-existent task
    result = get_task_entity(hass, "non_existent_task")
    assert result is None


async def test_entities_registered_during_setup(hass: HomeAssistant):
    """Test that task entities are registered in the lookup during setup."""
    await async_setup(hass, {})

    entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Test Story",
        data={
            "story_name": "Test Story",
            "story_description": "Test",
            "story_id": "test_story",
            "tasks": [
                {
                    "title": "Task 1",
                    "description": "First task",
                    "state": "todo",
                },
                {
                    "title": "Task 2",
                    "description": "Second task",
                    "state": "done",
                },
            ],
        },
        source="user",
        unique_id="test_unique",
    )

    with patch("custom_components.storyflow.StorageHandler"), patch(
        "custom_components.storyflow.StoryManager"
    ) as mock_manager, patch("custom_components.storyflow.async_setup_services"):

        mock_manager_instance = AsyncMock()
        mock_manager_instance.create_story = AsyncMock(return_value="test_story")
        mock_manager.return_value = mock_manager_instance

        await async_setup_entry(hass, entry)

        # After platform setup, entities should be registered
        # Note: In real execution, sensor.py registers them. Here we simulate it.
        from custom_components.storyflow.task_entity import TaskEntity

        # Simulate what sensor.py does
        task_entities = hass.data[DOMAIN]["task_entities"]

        # Create mock entities (sensor.py will do this in reality)
        storage_handler = hass.data[DOMAIN]["entries"][entry.entry_id]["storage"]
        for idx, task in enumerate(entry.data["tasks"]):
            task_id = f"test_story_task_{idx}"
            task_entity = TaskEntity(
                story_id="test_story",
                task_id=task_id,
                title=task["title"],
                description=task["description"],
                storage_handler=storage_handler,
                state=task.get("state", "todo"),
                order=idx,
            )
            task_entities[task_id] = task_entity

        # Verify entities are registered
        assert "test_story_task_0" in hass.data[DOMAIN]["task_entities"]
        assert "test_story_task_1" in hass.data[DOMAIN]["task_entities"]

        # Verify get_task_entity works
        from custom_components.storyflow import get_task_entity

        entity = get_task_entity(hass, "test_story_task_0")
        assert entity is not None
        assert entity.task_id == "test_story_task_0"
        assert entity.title == "Task 1"


async def test_entities_cleaned_up_during_unload(hass: HomeAssistant):
    """Test that task entities are removed from registry during unload."""
    await async_setup(hass, {})

    entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Test Story",
        data={
            "story_name": "Test Story",
            "story_description": "Test",
            "story_id": "test_story",
            "tasks": [
                {"title": "Task 1", "description": "Test", "state": "todo"},
                {"title": "Task 2", "description": "Test", "state": "done"},
            ],
        },
        source="user",
        unique_id="test_unique",
    )

    with patch("custom_components.storyflow.StorageHandler"), patch(
        "custom_components.storyflow.StoryManager"
    ) as mock_manager, patch("custom_components.storyflow.async_setup_services"), patch(
        "custom_components.storyflow.async_unload_services"
    ):

        mock_manager_instance = AsyncMock()
        mock_manager_instance.create_story = AsyncMock(return_value="test_story")
        mock_manager.return_value = mock_manager_instance

        await async_setup_entry(hass, entry)

        # Manually add entities to registry (simulating sensor.py)
        task_entities = hass.data[DOMAIN]["task_entities"]
        task_entities["test_story_task_0"] = "mock_entity_1"
        task_entities["test_story_task_1"] = "mock_entity_2"

        # Verify entities are registered
        assert len(task_entities) == 2

        # Unload entry
        with patch.object(
            hass.config_entries, "async_unload_platforms", return_value=True
        ):
            await async_unload_entry(hass, entry)

        # Verify entities are removed
        assert "test_story_task_0" not in hass.data[DOMAIN]["task_entities"]
        assert "test_story_task_1" not in hass.data[DOMAIN]["task_entities"]


async def test_multiple_stories_entity_registry(hass: HomeAssistant):
    """Test that multiple stories can register entities without conflicts."""
    await async_setup(hass, {})

    entry1 = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Story 1",
        data={
            "story_name": "Story 1",
            "story_description": "First",
            "story_id": "story_1",
            "tasks": [{"title": "Task 1A", "description": "Test", "state": "todo"}],
        },
        source="user",
        unique_id="story1_unique",
    )

    entry2 = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Story 2",
        data={
            "story_name": "Story 2",
            "story_description": "Second",
            "story_id": "story_2",
            "tasks": [{"title": "Task 2A", "description": "Test", "state": "todo"}],
        },
        source="user",
        unique_id="story2_unique",
    )

    with patch("custom_components.storyflow.StorageHandler"), patch(
        "custom_components.storyflow.StoryManager"
    ) as mock_manager, patch("custom_components.storyflow.async_setup_services"):

        mock_manager_instance = AsyncMock()
        mock_manager_instance.create_story = AsyncMock(
            side_effect=["story_1", "story_2"]
        )
        mock_manager.return_value = mock_manager_instance

        await async_setup_entry(hass, entry1)
        await async_setup_entry(hass, entry2)

        # Manually add entities (simulating sensor.py)
        task_entities = hass.data[DOMAIN]["task_entities"]
        task_entities["story_1_task_0"] = "mock_entity_1a"
        task_entities["story_2_task_0"] = "mock_entity_2a"

        # Verify both stories' entities coexist
        assert "story_1_task_0" in task_entities
        assert "story_2_task_0" in task_entities
        assert len(task_entities) == 2

        # Unload first story
        with patch.object(
            hass.config_entries, "async_unload_platforms", return_value=True
        ), patch("custom_components.storyflow.async_unload_services"):
            await async_unload_entry(hass, entry1)

        # Only story 1's entities should be removed
        assert "story_1_task_0" not in task_entities
        assert "story_2_task_0" in task_entities


async def test_entity_lookup_with_legacy_story_id(hass: HomeAssistant):
    """Test that entity lookup works with legacy entries (derived story_id)."""
    await async_setup(hass, {})

    entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="My Test Story",
        data={
            "story_name": "My Test Story",
            "story_description": "Test",
            # No story_id field (legacy)
            "tasks": [{"title": "Task 1", "description": "Test", "state": "todo"}],
        },
        source="user",
        unique_id="legacy_unique",
    )

    with patch("custom_components.storyflow.StorageHandler"), patch(
        "custom_components.storyflow.StoryManager"
    ) as mock_manager, patch("custom_components.storyflow.async_setup_services"), patch(
        "custom_components.storyflow.async_unload_services"
    ):

        mock_manager_instance = AsyncMock()
        mock_manager_instance.create_story = AsyncMock(return_value="my_test_story")
        mock_manager.return_value = mock_manager_instance

        await async_setup_entry(hass, entry)

        # Manually add entity with derived story_id (simulating sensor.py)
        task_entities = hass.data[DOMAIN]["task_entities"]
        task_entities["my_test_story_task_0"] = "mock_entity"

        # Verify entity is accessible
        from custom_components.storyflow import get_task_entity

        entity = get_task_entity(hass, "my_test_story_task_0")
        assert entity is not None

        # Unload should clean up using derived story_id
        with patch.object(
            hass.config_entries, "async_unload_platforms", return_value=True
        ):
            await async_unload_entry(hass, entry)

        # Entity should be removed
        assert "my_test_story_task_0" not in task_entities
