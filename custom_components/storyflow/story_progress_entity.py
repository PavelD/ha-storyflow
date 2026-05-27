"""Story progress entity for StoryFlow."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


class StoryProgressEntity(SensorEntity):
    """Represents the progress of a story."""

    def __init__(self, story_id, tasks, story_name=None):
        """Initialize the progress entity."""
        self.story_id = story_id
        self.story_name = story_name or story_id
        self.tasks = tasks

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{DOMAIN}_{self.story_id}_progress"

    @property
    def name(self) -> str:
        """Return the name."""
        return f"{self.story_name} Progress"

    @property
    def state(self):
        """Calculate progress percentage."""
        if not self.tasks:
            return 0
        # FIX: Access dictionary keys, not object properties
        done = sum(1 for t in self.tasks if t.get("state") in ["done", "rejected"])
        return int(done / len(self.tasks) * 100)

    @property
    def unit_of_measurement(self) -> str:
        """Return unit of measurement."""
        return "%"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        total = len(self.tasks)
        done = sum(1 for t in self.tasks if t.get("state") in ["done", "rejected"])
        in_progress = sum(1 for t in self.tasks if t.get("state") == "progress")
        todo = sum(1 for t in self.tasks if t.get("state") == "todo")

        return {
            "story_id": self.story_id,
            "total_tasks": total,
            "done_tasks": done,
            "in_progress_tasks": in_progress,
            "todo_tasks": todo,
        }

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.story_id)},
            name=self.story_name,
            manufacturer="StoryFlow",
            model="Story",
        )
