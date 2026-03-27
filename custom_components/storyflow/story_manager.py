class StoryManager:
    """Handles stories and their tasks with business logic."""

    def __init__(self, storage_handler, hass=None):
        """Initialize StoryManager.

        Args:
            storage_handler: StorageHandler instance for data persistence
            hass: Home Assistant instance (optional, needed for person validation)
        """
        self.storage = storage_handler
        self.hass = hass

    async def create_story(self, title, description, tasks):
        """Create a new story and save it to storage."""
        story_id = title.lower().replace(" ", "_")
        data = {
            "title": title,
            "description": description,
            "tasks": tasks,
        }
        await self.storage.save_story(story_id, data)
        return story_id

    async def async_validate_story_exists(self, story_id: str) -> bool:
        """Validate that a story exists.

        Args:
            story_id: The story identifier

        Returns:
            True if story exists

        Raises:
            ValueError: If story does not exist
        """
        exists = await self.storage.async_story_exists(story_id)
        if not exists:
            raise ValueError(f"Story '{story_id}' not found")
        return True

    async def async_validate_task_exists(self, story_id: str, task_id: str) -> bool:
        """Validate that a task exists within a story.

        Args:
            story_id: The story identifier
            task_id: The task identifier

        Returns:
            True if task exists

        Raises:
            ValueError: If story or task does not exist
        """
        await self.async_validate_story_exists(story_id)
        task = await self.storage.async_get_task(story_id, task_id)
        if not task:
            raise ValueError(f"Task '{task_id}' not found in story '{story_id}'")
        return True

    async def async_update_task_state(
        self, story_id: str, task_id: str, new_state: str
    ) -> None:
        """Update the state of a task.

        Args:
            story_id: The story identifier
            task_id: The task identifier
            new_state: The new state value ('todo', 'in_progress', or 'done')

        Raises:
            ValueError: If story/task not found or state invalid
        """
        # Validate task exists
        await self.async_validate_task_exists(story_id, task_id)

        # Validate state
        valid_states = ["todo", "in_progress", "done"]
        if new_state not in valid_states:
            raise ValueError(
                f"Invalid state '{new_state}'. Must be one of: {', '.join(valid_states)}"
            )

        # Update via storage
        await self.storage.async_update_task(story_id, task_id, {"state": new_state})

    async def async_assign_task(
        self, story_id: str, task_id: str, person_id: str | None
    ) -> None:
        """Assign a task to a person or unassign it.

        Args:
            story_id: The story identifier
            task_id: The task identifier
            person_id: The person entity ID to assign, or None to unassign

        Raises:
            ValueError: If story/task not found or person entity doesn't exist
        """
        # Validate task exists
        await self.async_validate_task_exists(story_id, task_id)

        # Validate person entity exists (if assigning)
        if person_id is not None and self.hass is not None:
            from homeassistant.helpers import entity_registry

            # Check entity registry first
            ent_reg = entity_registry.async_get(self.hass)
            if not ent_reg.async_is_registered(person_id):
                # Fallback: check state registry
                state = self.hass.states.get(person_id)
                if state is None:
                    raise ValueError(
                        f"Person entity '{person_id}' not found in Home Assistant"
                    )

        # Update via storage
        await self.storage.async_update_task(
            story_id, task_id, {"assigned_to": person_id}
        )

    def clone_story(self, story_id, new_title):
        """Clone a story: tasks reset to todo + assigned_to=None."""
        raise NotImplementedError("clone_story is not implemented yet.")
