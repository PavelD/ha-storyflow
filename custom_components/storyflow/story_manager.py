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

    async def async_generate_task_id(self, story_id: str) -> str:
        """Generate a unique task_id for a new task within a story.

        Args:
            story_id: The story identifier

        Returns:
            A unique task_id in the format "{story_id}_task_{index}"

        Raises:
            ValueError: If story does not exist
        """
        await self.async_validate_story_exists(story_id)

        story_data = await self.storage.load_story(story_id)
        tasks = story_data.get("tasks", [])

        # Find the highest existing task index
        max_index = -1
        for task in tasks:
            task_id = task.get("id", "")
            # Extract index from task_id format: "{story_id}_task_{index}"
            if task_id.startswith(f"{story_id}_task_"):
                try:
                    index = int(task_id.split("_task_")[-1])
                    max_index = max(max_index, index)
                except ValueError:
                    pass  # Skip malformed task IDs

        # Generate new task_id with next index
        new_index = max_index + 1
        return f"{story_id}_task_{new_index}"

    async def async_add_task(
        self,
        story_id: str,
        title: str,
        description: str = "",
        assigned_to: str | None = None,
        state: str = "todo",
    ) -> dict:
        """Add a new task to a story.

        Args:
            story_id: The story identifier
            title: Task title
            description: Task description (optional)
            assigned_to: Person entity ID to assign task to (optional)
            state: Initial task state (default: "todo")

        Returns:
            Dictionary containing the created task data including generated task_id

        Raises:
            ValueError: If story does not exist or state is invalid
        """
        await self.async_validate_story_exists(story_id)

        # Validate state
        valid_states = ["todo", "progress", "review", "done", "rejected"]
        if state not in valid_states:
            raise ValueError(
                f"Invalid state '{state}'. Must be one of: {', '.join(valid_states)}"
            )

        # Generate unique task_id
        task_id = await self.async_generate_task_id(story_id)

        # Get current tasks to determine order
        story_data = await self.storage.load_story(story_id)
        tasks = story_data.get("tasks", [])
        order = len(tasks)  # New task goes at the end

        # Create task data structure
        task_data = {
            "id": task_id,
            "title": title,
            "description": description,
            "assigned_to": assigned_to,
            "state": state,
            "order": order,
        }

        # Add task to storage
        await self.storage.async_add_task(story_id, task_data)

        return task_data

    def clone_story(self, story_id, new_title):
        """Clone a story: tasks reset to todo + assigned_to=None."""
        raise NotImplementedError("clone_story is not implemented yet.")
