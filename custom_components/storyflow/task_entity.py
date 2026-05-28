"""Task entity for StoryFlow."""

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, TASK_STATES

_LOGGER = logging.getLogger(__name__)


def get_task_unique_id(task_id: str) -> str:
    """Generate the unique_id for a task entity.

    Centralised so that both the entity and any service-layer lookups
    always use the same format.  Change this function when the format
    changes – all callers stay in sync automatically.
    """
    return f"{DOMAIN}_{task_id}"


class TaskEntity(SelectEntity):
    """Representation of a Task as a selectable state entity."""

    def __init__(
        self,
        story_id,
        task_id,
        title,
        description,
        storage_handler,
        assigned_to=None,
        state="todo",
        order=None,
        story_name=None,
        progress_entity=None,
    ):
        """Initialize the task entity."""
        self.story_id = story_id
        self.story_name = story_name or story_id
        self.task_id = task_id
        self.title = title
        self.description = description
        self.assigned_to = assigned_to
        self.order = order
        self.storage_handler = storage_handler
        self._progress_entity = progress_entity

        if state not in TASK_STATES:
            raise ValueError(f"Invalid state '{state}'. Must be one of {TASK_STATES}")
        self._state = state

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return get_task_unique_id(self.task_id)

    @property
    def name(self) -> str:
        """Return the name of the task."""
        return f"{self.story_name}: {self.title}"

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:timeline-check-outline"

    @property
    def options(self) -> list[str]:
        """Return the list of available states."""
        return list(TASK_STATES)

    @property
    def current_option(self) -> str:
        """Return the current state."""
        return self._state

    # Keep state property for backward compatibility with services/tests
    @property
    def state(self):
        """Return the state (alias for current_option)."""
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
            name=self.story_name,
            manufacturer="StoryFlow",
            model="Story",
        )

    async def async_select_option(self, option: str) -> None:
        """Handle state change from the HA UI dropdown.

        This is called when the user picks a value from the select dropdown
        in the Home Assistant frontend.  It persists the new state to storage
        and refreshes the progress entity so the percentage updates immediately.
        """
        await self.async_update_state(option)
        await self._async_refresh_progress()

    async def _async_refresh_progress(self) -> None:
        """Reload tasks from storage and push update to the progress entity."""
        if self._progress_entity is None:
            return
        try:
            story_data = await self.storage_handler.load_story(self.story_id)

            if not isinstance(story_data, dict):
                _LOGGER.warning(
                    "Story data for %s is missing or malformed while refreshing "
                    "progress; treating as no tasks",
                    self.story_id,
                )
                tasks: list = []
            else:
                tasks = story_data.get("tasks", [])

            self._progress_entity.tasks = tasks
            self._progress_entity.async_write_ha_state()
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning(
                "Could not refresh progress for story %s: %s", self.story_id, err
            )

    async def async_update_state(self, new_state: str) -> None:
        """Update the task state and persist to storage.

        Args:
            new_state: New state value (must be in TASK_STATES)

        Raises:
            ValueError: If state is invalid or storage update fails
        """
        if new_state not in TASK_STATES:
            raise ValueError(
                f"Invalid state '{new_state}'. Must be one of {TASK_STATES}"
            )

        try:
            # Persist to storage FIRST
            await self.storage_handler.async_update_task(
                self.story_id, self.task_id, {"state": new_state}
            )

            # Only update in-memory state on successful storage update
            self._state = new_state
            self.async_write_ha_state()

        except ValueError as err:
            _LOGGER.error(
                "Failed to update task %s state to '%s': %s",
                self.task_id,
                new_state,
                err,
            )
            raise

    async def async_update_assignment(self, person_id: str | None) -> None:
        """Update the task assignment and persist to storage.

        Args:
            person_id: ID of person to assign task to, or None to unassign

        Raises:
            ValueError: If storage update fails
        """
        try:
            # Persist to storage FIRST
            await self.storage_handler.async_update_task(
                self.story_id, self.task_id, {"assigned_to": person_id}
            )

            # Only update in-memory attribute on successful storage update
            self.assigned_to = person_id
            self.async_write_ha_state()

        except ValueError as err:
            _LOGGER.error(
                "Failed to update task %s assignment to '%s': %s",
                self.task_id,
                person_id,
                err,
            )
            raise

    async def async_update_attributes(self, **kwargs) -> None:
        """Update multiple task attributes at once.

        Args:
            **kwargs: Attributes to update (title, description, assigned_to, state, order)

        Raises:
            ValueError: If attribute name is invalid, state value is invalid, or storage update fails
        """
        valid_attrs = ["title", "description", "assigned_to", "state", "order"]

        # Validate all inputs before any updates
        for key, value in kwargs.items():
            if key not in valid_attrs:
                raise ValueError(
                    f"Invalid attribute '{key}'. Must be one of {valid_attrs}"
                )

            if key == "state" and value not in TASK_STATES:
                raise ValueError(
                    f"Invalid state '{value}'. Must be one of {TASK_STATES}"
                )

        try:
            # Persist to storage FIRST
            await self.storage_handler.async_update_task(
                self.story_id, self.task_id, kwargs
            )

            # Only update in-memory attributes on successful storage update
            for key, value in kwargs.items():
                if key == "state":
                    self._state = value
                else:
                    setattr(self, key, value)

            self.async_write_ha_state()

        except ValueError as err:
            _LOGGER.error(
                "Failed to update task %s attributes %s: %s",
                self.task_id,
                list(kwargs.keys()),
                err,
            )
            raise
