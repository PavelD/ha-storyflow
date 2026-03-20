from homeassistant.helpers.entity import Entity
from .const import TASK_STATES


class TaskEntity(Entity):
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
    def state(self):
        return self._state
