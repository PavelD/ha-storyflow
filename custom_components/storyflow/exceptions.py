"""Custom exceptions for StoryFlow integration."""


class StoryFlowException(Exception):
    """Base exception for StoryFlow integration."""


class TaskNotFoundError(StoryFlowException):
    """Exception raised when a task cannot be found."""

    def __init__(self, task_id: str):
        """Initialize TaskNotFoundError.

        Args:
            task_id: The ID of the task that was not found
        """
        self.task_id = task_id
        super().__init__(f"Task '{task_id}' not found")


class InvalidStateError(StoryFlowException):
    """Exception raised when an invalid task state is provided."""

    def __init__(self, state: str, valid_states: list[str]):
        """Initialize InvalidStateError.

        Args:
            state: The invalid state that was provided
            valid_states: List of valid states
        """
        self.state = state
        self.valid_states = valid_states
        super().__init__(
            f"Invalid state '{state}'. Must be one of: {', '.join(valid_states)}"
        )


class StoryNotFoundError(StoryFlowException):
    """Exception raised when a story cannot be found."""

    def __init__(self, story_id: str):
        """Initialize StoryNotFoundError.

        Args:
            story_id: The ID of the story that was not found
        """
        self.story_id = story_id
        super().__init__(f"Story '{story_id}' not found")


class StorageError(StoryFlowException):
    """Exception raised when a storage operation fails."""

    def __init__(self, operation: str, reason: str):
        """Initialize StorageError.

        Args:
            operation: The operation that failed (e.g., 'update', 'save')
            reason: The reason for the failure
        """
        self.operation = operation
        self.reason = reason
        super().__init__(f"Storage {operation} failed: {reason}")
