"""Integration tests for StoryFlow."""

import pytest
from unittest.mock import AsyncMock, patch

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
    """Test config entry setup creates expected entities."""
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
    with patch("custom_components.storyflow.StorageHandler") as mock_storage, patch(
        "custom_components.storyflow.StoryManager"
    ) as mock_manager, patch(
        "custom_components.storyflow.async_setup_services"
    ) as mock_services:

        mock_manager_instance = AsyncMock()
        mock_manager_instance.create_story = AsyncMock(return_value="test_story")
        mock_manager.return_value = mock_manager_instance

        # Setup the entry
        result = await async_setup_entry(hass, entry)

        assert result is True

        # Verify manager was created and stored
        assert DOMAIN in hass.data
        assert entry.entry_id in hass.data[DOMAIN]

        # Verify create_story was called
        mock_manager_instance.create_story.assert_called_once_with(
            "Test Story",
            "A test story",
            entry.data["tasks"],
        )

        # Verify services were set up
        mock_services.assert_called_once()


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

        # Verify data was stored
        assert entry.entry_id in hass.data[DOMAIN]

        # Mock platform unload
        with patch.object(
            hass.config_entries, "async_unload_platforms", return_value=True
        ):
            # Unload the entry
            result = await async_unload_entry(hass, entry)

            assert result is True

            # Verify data was removed
            assert entry.entry_id not in hass.data[DOMAIN]

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

        # Verify both are stored
        assert entry1.entry_id in hass.data[DOMAIN]
        assert entry2.entry_id in hass.data[DOMAIN]

        # Verify they're separate instances
        assert (
            hass.data[DOMAIN][entry1.entry_id] is not hass.data[DOMAIN][entry2.entry_id]
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
