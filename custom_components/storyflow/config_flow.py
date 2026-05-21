from homeassistant import config_entries
import voluptuous as vol
from homeassistant.core import callback
from .const import DOMAIN


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

            # Parse tasks (one per line, format "title: desc" or just "title")
            tasks = []
            if tasks_raw:
                for line in tasks_raw.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    if ":" in line:
                        task_name, desc = map(str.strip, line.split(":", 1))
                    else:
                        task_name, desc = line, ""
                    tasks.append(
                        {
                            "title": task_name,
                            "description": desc,
                            "state": "todo",
                            "assigned_to": None,
                        }
                    )

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

            # Parse tasks (one per line, format "title: desc" or just "title")
            tasks = []
            if tasks_raw:
                for line in tasks_raw.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    if ":" in line:
                        task_title, desc = map(str.strip, line.split(":", 1))
                    else:
                        task_title, desc = line, ""
                    tasks.append(
                        {
                            "title": task_title,
                            "description": desc,
                            "state": "todo",
                            "assigned_to": None,
                        }
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
                await self.hass.config_entries.async_reload(self._config_entry.entry_id)
                return self.async_create_entry(title="", data={})

        # Pre-populate form with current values
        current_data = self._config_entry.data
        current_tasks = current_data.get("tasks", [])
        tasks_raw_default = "\n".join(
            f"{t['title']}: {t['description']}" if t.get("description") else t["title"]
            for t in current_tasks
        )

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
