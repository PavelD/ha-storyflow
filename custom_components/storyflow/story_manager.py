import re

from .const import TASK_STATES


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

    def generate_story_id(self, title: str) -> str:
        """Generate a normalized, stable story_id from a human-readable title.

        - Lowercase
        - Collapse whitespace
        - Replace non-alphanumeric characters with underscores
        - Collapse repeated underscores
        - Strip leading/trailing underscores
        """
        slug = title.strip().lower()
        slug = re.sub(r"\s+", " ", slug)
        slug = re.sub(r"[^\w]+", "_", slug)
        slug = re.sub(r"_+", "_", slug).strip("_")
        return slug or "story"

    async def create_story(self, title, description, tasks):
        """Create a new story and save it to storage.

        Generates ``id`` and ``order`` for any tasks that are missing them so
        that sensor.py can always rely on every persisted task having an id.

        Raises:
            ValueError: If a story with the generated ID already exists.
        """
        story_id = self.generate_story_id(title)

        if await self.storage.async_story_exists(story_id):
            raise ValueError(
                f"Story '{story_id}' already exists. "
                "Use a unique title or update the existing story."
            )

        # Ensure every task has an id and an order before persisting
        tasks_with_ids = []
        for idx, task in enumerate(tasks):
            task_data = dict(task)
            if not task_data.get("id"):
                task_data["id"] = f"{story_id}_task_{idx}"
            if "order" not in task_data:
                task_data["order"] = idx
            tasks_with_ids.append(task_data)

        data = {
            "title": title,
            "description": description,
            "tasks": tasks_with_ids,
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
        # Validate state first (cheap, avoids unnecessary storage round-trip)
        if state not in TASK_STATES:
            raise ValueError(
                f"Invalid state '{state}'. Must be one of: {', '.join(TASK_STATES)}"
            )

        # Validate story exists, then load data in a single round-trip to avoid
        # a race condition where separate calls to async_generate_task_id and
        # load_story could see different task lists if a concurrent add happens
        # between them.
        await self.async_validate_story_exists(story_id)
        story_data = await self.storage.load_story(story_id)
        tasks = story_data.get("tasks", [])

        # Derive task_id and order from the same snapshot of the task list
        max_index = -1
        for existing_task in tasks:
            existing_id = existing_task.get("id", "")
            if existing_id.startswith(f"{story_id}_task_"):
                try:
                    index = int(existing_id.split("_task_")[-1])
                    max_index = max(max_index, index)
                except ValueError:
                    pass  # Skip malformed task IDs
        task_id = f"{story_id}_task_{max_index + 1}"
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

    async def async_delete_task(self, story_id: str, task_id: str) -> None:
        """Delete a task from a story.

        Args:
            story_id: The story identifier
            task_id: The task identifier

        Raises:
            ValueError: If story or task not found
        """
        # Validate task exists before deletion
        await self.async_validate_task_exists(story_id, task_id)

        # Delete via storage
        await self.storage.async_delete_task(story_id, task_id)

    async def async_update_task_details(
        self,
        story_id: str,
        task_id: str,
        title: str | None = None,
        description: str | None = None,
    ) -> None:
        """Update the title and/or description of a task.

        Args:
            story_id: The story identifier
            task_id: The task identifier
            title: New task title (optional)
            description: New task description (optional)

        Raises:
            ValueError: If story/task not found or no fields provided
        """
        # Validate at least one field is provided
        updates = {}
        if title is not None:
            updates["title"] = title
        if description is not None:
            updates["description"] = description

        if not updates:
            raise ValueError(
                "At least one field (title, description) must be provided to update"
            )

        # Validate task exists
        await self.async_validate_task_exists(story_id, task_id)

        # Update via storage
        await self.storage.async_update_task(story_id, task_id, updates)

    async def async_clone_story(
        self,
        story_id: str,
        new_story_name: str | None = None,
    ) -> dict:
        """Clone a story, resetting all tasks to todo and clearing assignments.

        Args:
            story_id: The story identifier to clone
            new_story_name: Name for the cloned story. Defaults to
                            "{original title} (Copy)" if not provided.

        Returns:
            Dictionary with ``story_id`` and ``story_data`` keys for the new story.

        Raises:
            ValueError: If source story does not exist or new story_id already exists
        """
        # Validate source story exists and load it
        await self.async_validate_story_exists(story_id)
        source_data = await self.storage.load_story(story_id)

        # Determine the new story title and id
        if new_story_name:
            new_title = new_story_name
        else:
            source_title = source_data.get("title", story_id)
            new_title = f"{source_title} (Copy)"

        new_story_id = self.generate_story_id(new_title)

        # Ensure the new story_id does not clash with an existing one
        if await self.storage.async_story_exists(new_story_id):
            raise ValueError(
                f"A story with ID '{new_story_id}' already exists. "
                "Provide a unique new_story_name."
            )

        # Deep-copy tasks: reset state → todo, clear assignment, renumber IDs
        cloned_tasks = []
        for order, original_task in enumerate(source_data.get("tasks", [])):
            cloned_task = {
                "id": f"{new_story_id}_task_{order}",
                "title": original_task.get("title", ""),
                "description": original_task.get("description", ""),
                "assigned_to": None,
                "state": "todo",
                "order": order,
            }
            cloned_tasks.append(cloned_task)

        # Build the new story data
        new_story_data = {
            "title": new_title,
            "description": source_data.get("description", ""),
            "tasks": cloned_tasks,
        }

        # Persist the cloned story
        await self.storage.save_story(new_story_id, new_story_data)

        return {
            "story_id": new_story_id,
            "story_data": new_story_data,
        }
