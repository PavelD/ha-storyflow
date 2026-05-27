"""Sensor platform for StoryFlow — registers story progress entities."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .story_progress_entity import StoryProgressEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up StoryFlow progress sensor entity."""
    entry_data = hass.data[DOMAIN]["entries"][entry.entry_id]
    storage_handler = entry_data["storage"]

    story_id = entry.data.get("story_id")
    story_name = entry.data.get("story_name", "")
    if story_id is None:
        story_id = story_name.lower().replace(" ", "_")

    # Load tasks from persistent storage for the initial progress calculation
    story_data = await storage_handler.load_story(story_id)
    if story_data is not None:
        tasks = story_data.get("tasks", [])
    else:
        tasks = entry.data.get("tasks", [])

    progress_entity = StoryProgressEntity(story_id, tasks, story_name=story_name)

    # Store the progress entity so select.py and services can reach it for
    # refresh after task-state changes.
    hass.data[DOMAIN].setdefault("progress_entities", {})
    hass.data[DOMAIN]["progress_entities"][story_id] = progress_entity

    # Store the sensor-platform callback so clone_story_service can add cloned
    # progress entities to the correct platform (sensor, not select).
    hass.data[DOMAIN].setdefault("sensor_callbacks", {})
    hass.data[DOMAIN]["sensor_callbacks"][story_id] = async_add_entities

    async_add_entities([progress_entity])
    return True
