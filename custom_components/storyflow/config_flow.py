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
        """Return the options flow handler (not implemented yet)."""
