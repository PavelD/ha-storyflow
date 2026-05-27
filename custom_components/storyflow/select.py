"""Select platform for StoryFlow — registers task entities."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .task_entity import TaskEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up StoryFlow task select entities from a config entry."""
    entry_data = hass.data[DOMAIN]["entries"][entry.entry_id]
    storage_handler = entry_data["storage"]

    story_id = entry.data.get("story_id")
    story_name = entry.data.get("story_name", "")
    if story_id is None:
        story_id = story_name.lower().replace(" ", "_")

    # Load tasks from persistent storage so states survive reloads
    story_data = await storage_handler.load_story(story_id)
    if story_data is not None:
        tasks = story_data.get("tasks", [])
    else:
        tasks = entry.data.get("tasks", [])

    # Grab the progress entity created by sensor.py so task entities can
    # trigger a refresh when their state changes via the UI dropdown.
    progress_entity = hass.data[DOMAIN].get("progress_entities", {}).get(story_id)

    # Store the callback so dynamic add_task / clone_story services can add
    # new task entities to this platform without a full reload.
    hass.data[DOMAIN].setdefault("entity_callbacks", {})
    hass.data[DOMAIN]["entity_callbacks"][story_id] = async_add_entities

    entities = []
    for idx, task in enumerate(tasks):
        task_id = task.get("id")
        # Migration: generate id for legacy tasks saved without one
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
            order=task.get("order", idx),
            story_name=story_name,
            progress_entity=progress_entity,
        )
        entities.append(task_entity)

        # Register in the global task lookup used by services
        hass.data[DOMAIN]["task_entities"][task_id] = task_entity

    async_add_entities(entities)
    return True
