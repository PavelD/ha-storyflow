"""StoryFlow integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .services import async_setup_services, async_unload_services
from .storage_handler import StorageHandler
from .story_manager import StoryManager

PLATFORMS = ["sensor", "select"]


def get_task_entity(hass: HomeAssistant, task_id: str):
    """
    Find a task entity by task_id.

    Args:
        hass: Home Assistant instance
        task_id: Unique task identifier

    Returns:
        TaskEntity if found, None otherwise
    """
    return hass.data[DOMAIN]["task_entities"].get(task_id)


# Integration can only be configured via config flow, not YAML
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up StoryFlow component."""
    # Initialize domain data with service reference counter and entity registry
    hass.data.setdefault(
        DOMAIN,
        {
            "service_ref_count": 0,
            "task_entities": {},  # {task_id: TaskEntity}
            "entries": {},  # {entry_id: {"manager": ..., "storage": ...}}
        },
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from config entry."""
    storage = StorageHandler(hass)
    manager = StoryManager(storage, hass)

    story_name = entry.data.get("story_name")
    story_id = entry.data.get("story_id")
    if story_id is None:
        story_id = manager._generate_story_id(story_name)

    # Only create/save story on first-time setup; preserve existing task states
    if not await storage.async_story_exists(story_id):
        story_desc = entry.data.get("story_description", "")
        tasks = entry.data.get("tasks", [])
        await manager.create_story(story_name, story_desc, tasks)

    # Store manager and storage in hass.data under the dedicated "entries" key
    hass.data[DOMAIN].setdefault("entries", {})
    hass.data[DOMAIN]["entries"][entry.entry_id] = {
        "manager": manager,
        "storage": storage,
    }

    # Set up services
    await async_setup_services(hass)

    # Forward platform setup
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Get story_id to clean up task entities
    story_id = entry.data.get("story_id")
    if story_id is None:
        story_name = entry.data.get("story_name", "")
        story_id = story_name.lower().replace(" ", "_")

    # Remove task entities from the lookup registry
    tasks = entry.data.get("tasks", [])
    for idx in range(len(tasks)):
        task_id = f"{story_id}_task_{idx}"
        hass.data[DOMAIN]["task_entities"].pop(task_id, None)

    # Unload services
    await async_unload_services(hass)

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Remove data
        hass.data[DOMAIN].get("entries", {}).pop(entry.entry_id, None)

    return unload_ok
