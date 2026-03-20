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
    manager = hass.data[DOMAIN][entry.entry_id]
    story_id = entry.data.get("story_name", "").lower().replace(" ", "_")
    tasks = entry.data.get("tasks", [])

    # Create progress sensor for the story
    sensors = [StoryProgressEntity(story_id, tasks)]

    # Create task entities
    for idx, task in enumerate(tasks):
        task_id = f"{story_id}_task_{idx}"
        task_entity = TaskEntity(
            story_id=story_id,
            task_id=task_id,
            title=task["title"],
            description=task["description"],
            assigned_to=task.get("assigned_to"),
            state=task.get("state", "todo"),
            order=idx,
        )
        sensors.append(task_entity)

    async_add_entities(sensors)

    return True
