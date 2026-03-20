class StoryManager:
    """Handles stories and their tasks."""

    def __init__(self, storage_handler):
        self.storage = storage_handler

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

    def clone_story(self, story_id, new_title):
        """Clone a story: tasks reset to todo + assigned_to=None."""
        raise NotImplementedError("clone_story is not implemented yet.")
