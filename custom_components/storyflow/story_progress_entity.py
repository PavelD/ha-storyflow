from homeassistant.helpers.entity import Entity


class StoryProgressEntity(Entity):
    """Represents the progress of a story."""

    def __init__(self, story_id, tasks):
        self.story_id = story_id
        self.tasks = tasks

    @property
    def state(self):
        done = sum(bool(t.state in ["done", "rejected"]) for t in self.tasks)
        return int(done / len(self.tasks) * 100) if self.tasks else 0
