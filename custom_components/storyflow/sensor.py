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
    entry_data = hass.data[DOMAIN][entry.entry_id]
    storage_handler = entry_data["storage"]

    # Prefer persisted story_id; fall back to legacy derivation for existing entries
    story_id = entry.data.get("story_id")
    if story_id is None:
        story_name = entry.data.get("story_name", "")
        story_id = story_name.lower().replace(" ", "_")

    tasks = entry.data.get("tasks", [])

    # Create progress sensor for the story
    progress_entity = StoryProgressEntity(story_id, tasks)
    sensors = [progress_entity]

    # Store callback and progress entity for dynamic entity management
    if "entity_callbacks" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["entity_callbacks"] = {}
    if "progress_entities" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["progress_entities"] = {}

    hass.data[DOMAIN]["entity_callbacks"][story_id] = async_add_entities
    hass.data[DOMAIN]["progress_entities"][story_id] = progress_entity

    # Create task entities and register them in the entity lookup
    for idx, task in enumerate(tasks):
        task_id = f"{story_id}_task_{idx}"
        task_entity = TaskEntity(
            story_id=story_id,
            task_id=task_id,
            title=task["title"],
            description=task["description"],
            storage_handler=storage_handler,
            assigned_to=task.get("assigned_to"),
            state=task.get("state", "todo"),
            order=idx,
        )
        sensors.append(task_entity)

        # Register task entity in the global lookup dictionary
        hass.data[DOMAIN]["task_entities"][task_id] = task_entity

    async_add_entities(sensors)

    return True
