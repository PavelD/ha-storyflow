"""Sensor platform for StoryFlow."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .story_progress_entity import StoryProgressEntity
from .task_entity import TaskEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up StoryFlow sensor entities."""
    # Get storage handler from hass.data
    entry_data = hass.data[DOMAIN]["entries"][entry.entry_id]
    storage_handler = entry_data["storage"]

    # Prefer persisted story_id; fall back to legacy derivation for existing entries
    story_id = entry.data.get("story_id")
    story_name = entry.data.get("story_name", "")
    if story_id is None:
        story_id = story_name.lower().replace(" ", "_")

    # Load tasks from persistent storage to preserve current state (e.g. after reload)
    story_data = await storage_handler.load_story(story_id)
    if story_data is not None:
        tasks = story_data.get("tasks", [])
    else:
        # Fallback to config entry data on very first setup (storage not yet written)
        tasks = entry.data.get("tasks", [])

    # Create progress sensor for the story
    progress_entity = StoryProgressEntity(story_id, tasks, story_name=story_name)
    sensors = [progress_entity]

    # Store callback and progress entity for dynamic entity management
    if "entity_callbacks" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["entity_callbacks"] = {}
    if "progress_entities" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["progress_entities"] = {}

    hass.data[DOMAIN]["entity_callbacks"][story_id] = async_add_entities
    hass.data[DOMAIN]["progress_entities"][story_id] = progress_entity

    # Create task entities from storage data to preserve current task states
    for idx, task in enumerate(tasks):
        task_id = task.get("id")
        # Migration: generate id for legacy tasks that were saved without one
        if not task_id:
            task_id = f"{story_id}_task_{idx}"
        task_entity = TaskEntity(
            story_id=story_id,
            task_id=task_id,
            title=task.get("title", ""),
            description=task.get("description", ""),
            storage_handler=storage_handler,
            assigned_to=task.get("assigned_to"),
            state=task.get("state", "todo"),
            order=task.get("order", 0),
            story_name=story_name,
        )
        sensors.append(task_entity)

        # Register task entity in the global lookup dictionary
        hass.data[DOMAIN]["task_entities"][task_id] = task_entity

    async_add_entities(sensors)

    return True
