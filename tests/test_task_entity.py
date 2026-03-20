"""Test TaskEntity for StoryFlow."""

import pytest

from custom_components.storyflow.task_entity import TaskEntity
from custom_components.storyflow.const import DOMAIN, TASK_STATES


def test_task_entity_init():
    """Test TaskEntity initialization with valid data."""
    entity = TaskEntity(
        story_id="test_story",
        task_id="test_story_task_0",
        title="Test Task",
        description="This is a test task",
        assigned_to="person.john",
        state="todo",
        order=0,
    )

    assert entity.story_id == "test_story"
    assert entity.task_id == "test_story_task_0"
    assert entity.title == "Test Task"
    assert entity.description == "This is a test task"
    assert entity.assigned_to == "person.john"
    assert entity.state == "todo"
    assert entity.order == 0


def test_task_entity_unique_id():
    """Test TaskEntity unique_id format."""
    entity = TaskEntity(
        story_id="test_story",
        task_id="test_story_task_0",
        title="Test Task",
        description="Test",
        state="todo",
    )

    # unique_id should include DOMAIN prefix
    assert entity.unique_id == f"{DOMAIN}_test_story_task_0"


def test_task_entity_name():
    """Test TaskEntity name format."""
    entity = TaskEntity(
        story_id="test_story",
        task_id="test_story_task_0",
        title="Test Task",
        description="Test",
        state="todo",
    )

    # Name should be "story_id: title"
    assert entity.name == "test_story: Test Task"


def test_task_entity_state():
    """Test TaskEntity state property."""
    entity = TaskEntity(
        story_id="test_story",
        task_id="test_story_task_0",
        title="Test Task",
        description="Test",
        state="progress",
    )

    assert entity.state == "progress"


def test_task_entity_invalid_state():
    """Test TaskEntity raises ValueError for invalid state."""
    with pytest.raises(ValueError) as exc_info:
        TaskEntity(
            story_id="test_story",
            task_id="test_story_task_0",
            title="Test Task",
            description="Test",
            state="invalid_state",
        )

    # Verify error message mentions the invalid state and valid states
    assert "invalid_state" in str(exc_info.value)
    assert str(TASK_STATES) in str(exc_info.value)


def test_task_entity_all_valid_states():
    """Test TaskEntity accepts all defined task states."""
    for state in TASK_STATES:
        entity = TaskEntity(
            story_id="test_story",
            task_id="test_story_task_0",
            title="Test Task",
            description="Test",
            state=state,
        )
        assert entity.state == state


def test_task_entity_extra_state_attributes():
    """Test TaskEntity extra_state_attributes are complete."""
    entity = TaskEntity(
        story_id="test_story",
        task_id="test_story_task_0",
        title="Test Task",
        description="This is a test task",
        assigned_to="person.john",
        state="progress",
        order=5,
    )

    attributes = entity.extra_state_attributes

    assert attributes["story_id"] == "test_story"
    assert attributes["task_id"] == "test_story_task_0"
    assert attributes["title"] == "Test Task"
    assert attributes["description"] == "This is a test task"
    assert attributes["assigned_to"] == "person.john"
    assert attributes["order"] == 5


def test_task_entity_optional_fields():
    """Test TaskEntity with optional fields as None."""
    entity = TaskEntity(
        story_id="test_story",
        task_id="test_story_task_0",
        title="Test Task",
        description="Test",
        assigned_to=None,
        state="todo",
        order=None,
    )

    attributes = entity.extra_state_attributes
    assert attributes["assigned_to"] is None
    assert attributes["order"] is None


def test_task_entity_device_info():
    """Test TaskEntity device_info groups tasks under story."""
    entity = TaskEntity(
        story_id="my_story",
        task_id="my_story_task_0",
        title="Test Task",
        description="Test",
        state="todo",
    )

    device_info = entity.device_info

    # Verify device identifiers include the story_id
    assert (DOMAIN, "my_story") in device_info["identifiers"]
    
    # Verify device name includes the story_id
    assert "my_story" in device_info["name"]
    
    # Verify manufacturer and model
    assert device_info["manufacturer"] == "StoryFlow"
    assert device_info["model"] == "Story"


def test_task_entity_device_info_grouping():
    """Test that multiple tasks share the same device_info."""
    entity1 = TaskEntity(
        story_id="shared_story",
        task_id="shared_story_task_0",
        title="Task 1",
        description="Test",
        state="todo",
    )

    entity2 = TaskEntity(
        story_id="shared_story",
        task_id="shared_story_task_1",
        title="Task 2",
        description="Test",
        state="done",
    )

    # Both should have the same device identifiers
    assert entity1.device_info["identifiers"] == entity2.device_info["identifiers"]
