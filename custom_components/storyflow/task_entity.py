"""Task entity for StoryFlow."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, TASK_STATES


class TaskEntity(SensorEntity):
    """Representation of a Task."""

    def __init__(
        self,
        story_id,
        task_id,
        title,
        description,
        assigned_to=None,
        state="todo",
        order=None,
    ):
        """Initialize the task entity."""
        self.story_id = story_id
        self.task_id = task_id
        self.title = title
        self.description = description
        self.assigned_to = assigned_to
        self.order = order

        if state not in TASK_STATES:
            raise ValueError(f"Invalid state '{state}'. Must be one of {TASK_STATES}")
        self._state = state

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{DOMAIN}_{self.task_id}"

    @property
    def name(self) -> str:
        """Return the name of the task."""
        return f"{self.story_id}: {self.title}"

    @property
    def state(self):
        """Return the state."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        return {
            "story_id": self.story_id,
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "assigned_to": self.assigned_to,
            "order": self.order,
        }

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info to group tasks under story."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.story_id)},
            name=f"Story: {self.story_id}",
            manufacturer="StoryFlow",
            model="Story",
        )
