from homeassistant import config_entries
import voluptuous as vol
from homeassistant.core import callback
from .const import DOMAIN

# ---------------------------------------------------------------------------
# Task serialization helpers
# ---------------------------------------------------------------------------


def _escape(value: str) -> str:
    """Escape backslashes and colons so tasks_raw is round-trip safe."""
    return value.replace("\\", "\\\\").replace(":", "\\:")


def _unescape(value: str) -> str:
    """Reverse _escape: convert \\: → : and \\\\ → \\."""
    result = []
    i = 0
    while i < len(value):
        if value[i] == "\\" and i + 1 < len(value):
            next_char = value[i + 1]
            if next_char in (":", "\\"):
                result.append(next_char)
                i += 2
                continue
        result.append(value[i])
        i += 1
    return "".join(result)


def _split_unescaped_colon(line: str):
    """Split *line* at the first unescaped colon.

    Returns ``(before, after)`` where *after* is the text after the colon
    (may be an empty string), or ``(line, None)`` when no unescaped colon
    exists.
    """
    i = 0
    while i < len(line):
        if line[i] == "\\" and i + 1 < len(line):
            i += 2  # skip the escaped character
        elif line[i] == ":":
            return line[:i], line[i + 1 :]
        else:
            i += 1
    return line, None


def _encode_task_line(task: dict) -> str:
    """Encode a task dict into a single tasks_raw line."""
    title = _escape(task.get("title") or "")
    description = _escape(task.get("description") or "")
    return f"{title}: {description}" if description else title


def _parse_tasks_raw(tasks_raw: str, existing_tasks: list | None = None) -> list:
    """Parse a tasks_raw string into a list of task dicts.

    When *existing_tasks* is provided, the ``state`` and ``assigned_to`` values
    of any task whose title matches an existing task are preserved rather than
    being reset to defaults.  This avoids losing progress when a user edits a
    story via the options flow.
    """
    # Build a lookup so we can restore state/assignee by title in O(1)
    existing_by_title: dict = {}
    if existing_tasks:
        for t in existing_tasks:
            title = t.get("title", "")
            if title and title not in existing_by_title:
                existing_by_title[title] = t

    tasks = []
    for line in tasks_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        before, after = _split_unescaped_colon(line)
        task_title = _unescape(before.strip())
        desc = _unescape(after.strip()) if after is not None else ""

        existing = existing_by_title.get(task_title)
        tasks.append(
            {
                "title": task_title,
                "description": desc,
                "state": existing["state"] if existing else "todo",
                "assigned_to": existing["assigned_to"] if existing else None,
            }
        )
    return tasks


# ---------------------------------------------------------------------------
# Config flow
# ---------------------------------------------------------------------------


class StoryFlowConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for StoryFlow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle user input for creating a new story."""
        errors = {}

        if user_input is not None:
            story_name = user_input.get("story_name", "").strip()
            story_description = user_input.get("story_description", "").strip()
            tasks_raw = user_input.get("tasks_raw", "").strip()

            if not story_name:
                errors["story_name"] = "required"

            tasks = _parse_tasks_raw(tasks_raw)

            if not errors:
                # Generate story_id using the same logic as StoryManager
                story_id = story_name.lower().replace(" ", "_")

                data = {
                    "story_name": story_name,
                    "story_description": story_description,
                    "story_id": story_id,
                    "tasks": tasks,
                }
                return self.async_create_entry(title=story_name, data=data)

        schema = vol.Schema(
            {
                vol.Required("story_name"): str,
                vol.Optional("story_description", default=""): str,
                vol.Optional("tasks_raw", default=""): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "example": "Enter name, description (Markdown) and list of tasks line by line.\n"
                "Example:\nDrain water: Pump out approx. 10 cm\nSwitch off the pump"
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return OptionsFlowHandler(config_entry)


# ---------------------------------------------------------------------------
# Options flow
# ---------------------------------------------------------------------------


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for StoryFlow (edit story details and tasks)."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Handle the options form."""
        errors = {}

        if user_input is not None:
            story_name = user_input.get("story_name", "").strip()
            story_description = user_input.get("story_description", "").strip()
            tasks_raw = user_input.get("tasks_raw", "").strip()

            if not story_name:
                errors["story_name"] = "required"

            # Preserve existing task state/assigned_to for tasks whose title
            # matches one already stored in the entry.
            tasks = _parse_tasks_raw(
                tasks_raw,
                existing_tasks=self._config_entry.data.get("tasks", []),
            )

            if not errors:
                # Preserve the original story_id — it is used as a stable key
                story_id = self._config_entry.data.get(
                    "story_id",
                    story_name.lower().replace(" ", "_"),
                )

                new_data = {
                    **self._config_entry.data,
                    "story_name": story_name,
                    "story_description": story_description,
                    "story_id": story_id,
                    "tasks": tasks,
                }

                self.hass.config_entries.async_update_entry(
                    self._config_entry, data=new_data
                )
                # Explicitly reload the entry so the new data takes effect.
                # HA only auto-reloads when entry.options changes; since we write
                # to entry.data we must trigger the reload ourselves.
                await self.hass.config_entries.async_reload(self._config_entry.entry_id)
                return self.async_create_entry(title="", data={})

        # Pre-populate form with current values
        current_data = self._config_entry.data
        current_tasks = current_data.get("tasks", [])
        tasks_raw_default = "\n".join(_encode_task_line(t) for t in current_tasks)

        schema = vol.Schema(
            {
                vol.Required(
                    "story_name", default=current_data.get("story_name", "")
                ): str,
                vol.Optional(
                    "story_description",
                    default=current_data.get("story_description", ""),
                ): str,
                vol.Optional("tasks_raw", default=tasks_raw_default): str,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
