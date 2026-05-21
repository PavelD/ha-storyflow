import pytest
from custom_components.storyflow.const import DOMAIN


async def test_config_flow_creates_entry(hass):
    """Test that config flow creates a StoryFlow entry with valid data."""

    # Start the config flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "user"

    # Simulate user input
    user_input = {
        "story_name": "Winterizing the pool",
        "story_description": "## Steps\n\n- Drain water\n- Turn off pump",
        "tasks_raw": "Drain water: Remove ~10 cm\nTurn off pump",
    }

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=user_input
    )

    # Validate that entry was created
    assert result2["type"] == "create_entry"
    assert result2["title"] == "Winterizing the pool"
    data = result2["data"]

    # Validate structure
    assert data["story_name"] == "Winterizing the pool"
    assert data["story_description"].startswith("## Steps")
    assert isinstance(data["tasks"], list)
    assert len(data["tasks"]) == 2

    # Validate tasks
    first_task = data["tasks"][0]
    assert first_task["title"] == "Drain water"
    assert first_task["state"] == "todo"
    assert first_task["assigned_to"] is None


async def _create_entry(hass):
    """Helper to create a StoryFlow config entry for options flow tests."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "story_name": "Winterizing the pool",
            "story_description": "## Steps",
            "tasks_raw": "Drain water: Remove ~10 cm\nTurn off pump",
        },
    )
    assert result2["type"] == "create_entry"
    return hass.config_entries.async_entries(DOMAIN)[0]


async def test_options_flow_shows_form_prepopulated(hass):
    """Test that options flow shows a form pre-populated with current entry data."""
    entry = await _create_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # Schema defaults should reflect current entry data
    schema = result["data_schema"].schema
    field_names = [str(k) for k in schema]
    assert "story_name" in field_names
    assert "story_description" in field_names
    assert "tasks_raw" in field_names


async def test_options_flow_updates_entry(hass):
    """Test that submitting options flow updates story name, description and tasks."""
    entry = await _create_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "form"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "story_name": "Winterizing the pool (updated)",
            "story_description": "## Updated Steps",
            "tasks_raw": "Drain water\nTurn off pump\nCover the pool",
        },
    )

    assert result2["type"] == "create_entry"

    # Reload the entry reference after update
    updated_entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert updated_entry.data["story_name"] == "Winterizing the pool (updated)"
    assert updated_entry.data["story_description"] == "## Updated Steps"
    assert len(updated_entry.data["tasks"]) == 3
    assert updated_entry.data["tasks"][2]["title"] == "Cover the pool"


async def test_options_flow_preserves_story_id(hass):
    """Test that options flow does not change the original story_id."""
    entry = await _create_entry(hass)
    original_story_id = entry.data["story_id"]

    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "story_name": "Completely different name",
            "story_description": "",
            "tasks_raw": "Task A",
        },
    )

    updated_entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert updated_entry.data["story_id"] == original_story_id


async def test_options_flow_requires_story_name(hass):
    """Test that options flow returns an error when story_name is empty."""
    entry = await _create_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "story_name": "",
            "story_description": "",
            "tasks_raw": "",
        },
    )

    assert result2["type"] == "form"
    assert "story_name" in result2["errors"]
