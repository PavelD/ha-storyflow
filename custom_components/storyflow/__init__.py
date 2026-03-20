from homeassistant.core import HomeAssistant
from .storage_handler import StorageHandler
from .story_manager import StoryManager
from .const import DOMAIN


async def async_setup(hass: HomeAssistant, config: dict):
    """Setup StoryFlow component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry):
    """Setup from config entry."""
    storage = StorageHandler(hass)
    manager = StoryManager(storage)

    story_name = entry.data.get("story_name")
    story_desc = entry.data.get("story_description", "")
    tasks = entry.data.get("tasks", [])

    # Save the story to persistent storage
    await manager.create_story(story_name, story_desc, tasks)

    hass.data[DOMAIN][entry.entry_id] = manager
    return True
