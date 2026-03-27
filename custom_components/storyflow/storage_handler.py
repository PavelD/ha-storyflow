from homeassistant.helpers.storage import Store
from .const import DOMAIN


class StorageHandler:
    """Wrapper for HA storage .storage/storyflow"""

    VERSION = 1

    def __init__(self, hass):
        self.store = Store(hass, self.VERSION, f"{DOMAIN}.json")

    async def save_story(self, story_id, data):
        """Save a complete story to storage.

        Args:
            story_id: The story identifier
            data: Complete story data dictionary
        """
        current = await self.store.async_load() or {}
        current[story_id] = data
        await self.store.async_save(current)

    async def load_story(self, story_id):
        """Load a single story from storage.

        Args:
            story_id: The story identifier

        Returns:
            Story data dictionary or None if not found
        """
        current = await self.store.async_load() or {}
        return current.get(story_id)

    async def async_load_all_stories(self) -> dict:
        """Load all stories from storage.

        Returns:
            Dictionary with story_id as keys and story data as values
        """
        return await self.store.async_load() or {}

    async def async_story_exists(self, story_id: str) -> bool:
        """Check if a story exists in storage.

        Args:
            story_id: The story identifier

        Returns:
            True if story exists, False otherwise
        """
        story_data = await self.load_story(story_id)
        return story_data is not None

    async def async_get_task(self, story_id: str, task_id: str) -> dict | None:
        """Get a specific task from a story.

        Args:
            story_id: The story identifier
            task_id: The task identifier

        Returns:
            Task data dictionary or None if not found
        """
        story_data = await self.load_story(story_id)
        if not story_data:
            return None

        for task in story_data.get("tasks", []):
            if task.get("id") == task_id:
                return task

        return None

    async def async_update_task(
        self, story_id: str, task_id: str, updates: dict
    ) -> None:
        """Update a specific task within a story.

        Args:
            story_id: The story identifier
            task_id: The task identifier
            updates: Dictionary of task attributes to update

        Raises:
            ValueError: If story or task not found
        """
        story_data = await self.load_story(story_id)
        if not story_data:
            raise ValueError(f"Story '{story_id}' not found")

        tasks = story_data.get("tasks", [])
        task_found = False

        for task in tasks:
            if task.get("id") == task_id:
                task.update(updates)
                task_found = True
                break

        if not task_found:
            raise ValueError(f"Task '{task_id}' not found in story '{story_id}'")

        await self.save_story(story_id, story_data)

    async def async_add_task(self, story_id: str, task_data: dict) -> None:
        """Add a new task to a story.

        Args:
            story_id: The story identifier
            task_data: Complete task data dictionary

        Raises:
            ValueError: If story not found or task_data invalid
        """
        story_data = await self.load_story(story_id)
        if not story_data:
            raise ValueError(f"Story '{story_id}' not found")

        if "id" not in task_data:
            raise ValueError("Task data must include 'id' field")

        tasks = story_data.get("tasks", [])

        # Prevent duplicate task IDs within the same story
        if any(task.get("id") == task_data["id"] for task in tasks):
            raise ValueError(
                f"Task with id '{task_data['id']}' already exists in story '{story_id}'"
            )

        tasks.append(task_data)
        story_data["tasks"] = tasks

        await self.save_story(story_id, story_data)

    async def async_delete_task(self, story_id: str, task_id: str) -> None:
        """Delete a task from a story.

        Args:
            story_id: The story identifier
            task_id: The task identifier

        Raises:
            ValueError: If story or task not found
        """
        story_data = await self.load_story(story_id)
        if not story_data:
            raise ValueError(f"Story '{story_id}' not found")

        tasks = story_data.get("tasks", [])
        original_count = len(tasks)

        story_data["tasks"] = [t for t in tasks if t.get("id") != task_id]

        if len(story_data["tasks"]) == original_count:
            raise ValueError(f"Task '{task_id}' not found in story '{story_id}'")

        await self.save_story(story_id, story_data)
