"""StoryFlow integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .services import async_setup_services, async_unload_services
from .storage_handler import StorageHandler
from .story_manager import StoryManager

PLATFORMS = ["sensor"]

# Integration can only be configured via config flow, not YAML
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up StoryFlow component."""
    # Initialize domain data with service reference counter
    hass.data.setdefault(DOMAIN, {"service_ref_count": 0})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from config entry."""
    storage = StorageHandler(hass)
    manager = StoryManager(storage, hass)

    story_name = entry.data.get("story_name")
    story_desc = entry.data.get("story_description", "")
    tasks = entry.data.get("tasks", [])

    # Save the story to persistent storage
    await manager.create_story(story_name, story_desc, tasks)

    # Store manager and storage in hass.data
    hass.data[DOMAIN][entry.entry_id] = {
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
    # Unload services
    await async_unload_services(hass)

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Remove data
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
