from custom_components.storyflow.const import DOMAIN
from custom_components.storyflow.config_flow import _encode_task_line


def _get_schema_defaults(result):
    """Return a dict of field-name -> actual default value from a flow form result.

    Voluptuous stores defaults as callables, so we call each one to get the value.
    """
    return {str(field): field.default() for field in result["data_schema"].schema}


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
    assert first_task["description"] == "Remove ~10 cm"
    assert first_task["state"] == "todo"
    assert first_task["assigned_to"] is None

    second_task = data["tasks"][1]
    assert second_task["title"] == "Turn off pump"
    assert second_task["description"] == ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Options flow tests
# ---------------------------------------------------------------------------


async def test_options_flow_shows_form_prepopulated(hass):
    """Test that options flow shows a form pre-populated with current entry data."""
    entry = await _create_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # Voluptuous stores defaults as callables — call them to get the actual values
    defaults = _get_schema_defaults(result)

    assert "story_name" in defaults
    assert "story_description" in defaults
    assert "tasks_raw" in defaults

    # Story fields should be pre-populated from the entry data
    assert defaults["story_name"] == entry.data["story_name"]
    assert defaults["story_description"] == entry.data["story_description"]

    # tasks_raw should be pre-populated from the entry tasks using the same
    # encoding used by the options flow (colon-safe round-trip format)
    expected_tasks_raw = "\n".join(_encode_task_line(t) for t in entry.data["tasks"])
    assert defaults["tasks_raw"] == expected_tasks_raw


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
            # Include whitespace variation and a title-only line to exercise parsing
            "tasks_raw": (
                "Drain water\n"
                "Turn off pump\n"
                "Cover the pool: Use the winter cover\n"
            ),
        },
    )

    assert result2["type"] == "create_entry"

    updated_entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert updated_entry.data["story_name"] == "Winterizing the pool (updated)"
    assert updated_entry.data["story_description"] == "## Updated Steps"

    tasks = updated_entry.data["tasks"]
    assert len(tasks) == 3

    assert tasks[0]["title"] == "Drain water"
    assert tasks[0]["description"] == ""

    assert tasks[1]["title"] == "Turn off pump"
    assert tasks[1]["description"] == ""

    assert tasks[2]["title"] == "Cover the pool"
    assert tasks[2]["description"] == "Use the winter cover"


async def test_options_flow_parses_tasks_with_whitespace_and_colons(hass):
    """Test that task parsing correctly trims whitespace and handles colons."""
    entry = await _create_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "story_name": "Winterizing the pool",
            "story_description": "",
            # Leading/trailing whitespace around title and description
            "tasks_raw": (
                "  Task A  :  description A  \n" "Task B:description B\n" "  Task C  \n"
            ),
        },
    )

    updated_entry = hass.config_entries.async_get_entry(entry.entry_id)
    tasks = updated_entry.data["tasks"]
    assert len(tasks) == 3

    assert tasks[0]["title"] == "Task A"
    assert tasks[0]["description"] == "description A"

    assert tasks[1]["title"] == "Task B"
    assert tasks[1]["description"] == "description B"

    assert tasks[2]["title"] == "Task C"
    assert tasks[2]["description"] == ""


async def test_options_flow_roundtrip_with_colons_in_title_and_description(hass):
    """Test that titles/descriptions containing colons survive a full round-trip."""
    entry = await _create_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "story_name": "Story",
            "story_description": "",
            # Use escaped colons in the title so they survive parsing
            "tasks_raw": "Step 1\\: setup: configure the server\\: port 8080",
        },
    )

    updated_entry = hass.config_entries.async_get_entry(entry.entry_id)
    tasks = updated_entry.data["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Step 1: setup"
    assert tasks[0]["description"] == "configure the server: port 8080"

    # Now open options again — the pre-populated tasks_raw must re-encode the
    # colons so a second save produces the same result
    result2 = await hass.config_entries.options.async_init(updated_entry.entry_id)
    defaults2 = _get_schema_defaults(result2)
    expected_raw = "Step 1\\: setup: configure the server\\: port 8080"
    assert defaults2["tasks_raw"] == expected_raw


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


async def test_options_flow_clears_tasks_when_tasks_raw_empty(hass):
    """Test that submitting an empty tasks_raw clears all tasks on the entry."""
    entry = await _create_entry(hass)
    assert len(entry.data["tasks"]) > 0  # pre-condition: entry has tasks

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "story_name": entry.data["story_name"],
            "story_description": entry.data["story_description"],
            "tasks_raw": "",
        },
    )

    assert result2["type"] == "create_entry"

    updated_entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert updated_entry.data["tasks"] == []
