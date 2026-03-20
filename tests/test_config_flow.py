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
