from homeassistant.helpers.storage import Store
from .const import DOMAIN


class StorageHandler:
    """Wrapper for HA storage .storage/storyflow"""

    VERSION = 1

    def __init__(self, hass):
        self.store = Store(hass, self.VERSION, f"{DOMAIN}.json")

    async def save_story(self, story_id, data):
        current = await self.store.async_load() or {}
        current[story_id] = data
        await self.store.async_save(current)

    async def load_story(self, story_id):
        current = await self.store.async_load() or {}
        return current.get(story_id)
