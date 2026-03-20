"""Test StoryProgressEntity for StoryFlow."""

from custom_components.storyflow.story_progress_entity import StoryProgressEntity
from custom_components.storyflow.const import DOMAIN


def test_progress_calculation_no_tasks():
    """Test progress calculation with no tasks."""
    entity = StoryProgressEntity("test_story", [])
    
    assert entity.state == 0


def test_progress_calculation_all_todo():
    """Test progress calculation when all tasks are todo."""
    tasks = [
        {"title": "Task 1", "state": "todo"},
        {"title": "Task 2", "state": "todo"},
        {"title": "Task 3", "state": "todo"},
    ]
    entity = StoryProgressEntity("test_story", tasks)
    
    assert entity.state == 0


def test_progress_calculation_one_done():
    """Test progress calculation with one task done."""
    tasks = [
        {"title": "Task 1", "state": "done"},
        {"title": "Task 2", "state": "todo"},
        {"title": "Task 3", "state": "todo"},
        {"title": "Task 4", "state": "todo"},
    ]
    entity = StoryProgressEntity("test_story", tasks)
    
    # 1/4 = 25%
    assert entity.state == 25


def test_progress_calculation_half_done():
    """Test progress calculation with half tasks done."""
    tasks = [
        {"title": "Task 1", "state": "done"},
        {"title": "Task 2", "state": "done"},
        {"title": "Task 3", "state": "todo"},
        {"title": "Task 4", "state": "todo"},
    ]
    entity = StoryProgressEntity("test_story", tasks)
    
    # 2/4 = 50%
    assert entity.state == 50


def test_progress_calculation_all_done():
    """Test progress calculation when all tasks are done."""
    tasks = [
        {"title": "Task 1", "state": "done"},
        {"title": "Task 2", "state": "done"},
        {"title": "Task 3", "state": "done"},
    ]
    entity = StoryProgressEntity("test_story", tasks)
    
    assert entity.state == 100


def test_progress_calculation_rejected_counted():
    """Test that rejected tasks are counted as done."""
    tasks = [
        {"title": "Task 1", "state": "done"},
        {"title": "Task 2", "state": "rejected"},
        {"title": "Task 3", "state": "todo"},
        {"title": "Task 4", "state": "todo"},
    ]
    entity = StoryProgressEntity("test_story", tasks)
    
    # 2/4 (done + rejected) = 50%
    assert entity.state == 50


def test_progress_calculation_mixed_states():
    """Test progress calculation with mixed task states."""
    tasks = [
        {"title": "Task 1", "state": "done"},
        {"title": "Task 2", "state": "progress"},
        {"title": "Task 3", "state": "review"},
        {"title": "Task 4", "state": "todo"},
    ]
    entity = StoryProgressEntity("test_story", tasks)
    
    # Only 1/4 done = 25%
    assert entity.state == 25


def test_progress_unit_of_measurement():
    """Test that unit of measurement is percentage."""
    entity = StoryProgressEntity("test_story", [])
    
    assert entity.unit_of_measurement == "%"


def test_progress_unique_id():
    """Test progress entity unique_id format."""
    entity = StoryProgressEntity("my_story", [])
    
    assert entity.unique_id == f"{DOMAIN}_my_story_progress"


def test_progress_name():
    """Test progress entity name format."""
    entity = StoryProgressEntity("my_story", [])
    
    assert entity.name == "my_story Progress"


def test_progress_extra_state_attributes_empty():
    """Test extra_state_attributes with no tasks."""
    entity = StoryProgressEntity("test_story", [])
    
    attributes = entity.extra_state_attributes
    
    assert attributes["story_id"] == "test_story"
    assert attributes["total_tasks"] == 0
    assert attributes["done_tasks"] == 0
    assert attributes["in_progress_tasks"] == 0
    assert attributes["todo_tasks"] == 0


def test_progress_extra_state_attributes_mixed():
    """Test extra_state_attributes with mixed task states."""
    tasks = [
        {"title": "Task 1", "state": "done"},
        {"title": "Task 2", "state": "done"},
        {"title": "Task 3", "state": "rejected"},
        {"title": "Task 4", "state": "progress"},
        {"title": "Task 5", "state": "progress"},
        {"title": "Task 6", "state": "review"},
        {"title": "Task 7", "state": "todo"},
        {"title": "Task 8", "state": "todo"},
        {"title": "Task 9", "state": "todo"},
    ]
    entity = StoryProgressEntity("test_story", tasks)
    
    attributes = entity.extra_state_attributes
    
    assert attributes["story_id"] == "test_story"
    assert attributes["total_tasks"] == 9
    assert attributes["done_tasks"] == 3  # done + rejected
    assert attributes["in_progress_tasks"] == 2
    assert attributes["todo_tasks"] == 3


def test_progress_extra_state_attributes_all_done():
    """Test extra_state_attributes when all tasks are done."""
    tasks = [
        {"title": "Task 1", "state": "done"},
        {"title": "Task 2", "state": "done"},
        {"title": "Task 3", "state": "done"},
    ]
    entity = StoryProgressEntity("test_story", tasks)
    
    attributes = entity.extra_state_attributes
    
    assert attributes["total_tasks"] == 3
    assert attributes["done_tasks"] == 3
    assert attributes["in_progress_tasks"] == 0
    assert attributes["todo_tasks"] == 0


def test_progress_device_info():
    """Test progress entity device_info."""
    entity = StoryProgressEntity("my_story", [])
    
    device_info = entity.device_info
    
    # Verify device identifiers include the story_id
    assert (DOMAIN, "my_story") in device_info["identifiers"]
    
    # Verify device name includes the story_id
    assert "my_story" in device_info["name"]
    
    # Verify manufacturer and model
    assert device_info["manufacturer"] == "StoryFlow"
    assert device_info["model"] == "Story"


def test_progress_rounding():
    """Test that progress percentage is rounded to integer."""
    tasks = [
        {"title": "Task 1", "state": "done"},
        {"title": "Task 2", "state": "todo"},
        {"title": "Task 3", "state": "todo"},
    ]
    entity = StoryProgressEntity("test_story", tasks)
    
    # 1/3 = 33.333... should be rounded to 33
    assert entity.state == 33
    assert isinstance(entity.state, int)
