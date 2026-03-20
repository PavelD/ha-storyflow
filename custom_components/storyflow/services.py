"""Services for StoryFlow."""

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, TASK_STATES

SERVICE_SET_STATE = "set_task_state"
SERVICE_ASSIGN = "assign_task"
SERVICE_CLONE_STORY = "clone_story"

SET_STATE_SCHEMA = vol.Schema(
    {
        vol.Required("task_id"): cv.string,
        vol.Required("new_state"): vol.In(TASK_STATES),
    }
)

ASSIGN_SCHEMA = vol.Schema(
    {
        vol.Required("task_id"): cv.string,
        vol.Optional("person_id"): cv.string,
    }
)

CLONE_STORY_SCHEMA = vol.Schema(
    {
        vol.Required("story_id"): cv.string,
        vol.Optional("new_story_name"): cv.string,
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register services."""

    async def set_state_service(call: ServiceCall) -> None:
        """Set task state."""
        task_id = call.data["task_id"]
        new_state = call.data["new_state"]

        # TODO: Implement - find task entity and update state
        # For now, log the call
        hass.logger.info(f"Setting task {task_id} to state {new_state}")

    async def assign_service(call: ServiceCall) -> None:
        """Assign task to person."""
        task_id = call.data["task_id"]
        person_id = call.data.get("person_id")

        # TODO: Implement - find task entity and update assigned_to
        hass.logger.info(f"Assigning task {task_id} to {person_id}")

    async def clone_story_service(call: ServiceCall) -> None:
        """Clone a story."""
        story_id = call.data["story_id"]
        new_title = call.data.get("new_story_name")

        # TODO: Implement - duplicate story with reset tasks
        hass.logger.info(f"Cloning story {story_id} to {new_title}")

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_STATE,
        set_state_service,
        schema=SET_STATE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_ASSIGN,
        assign_service,
        schema=ASSIGN_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CLONE_STORY,
        clone_story_service,
        schema=CLONE_STORY_SCHEMA,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services."""
    hass.services.async_remove(DOMAIN, SERVICE_SET_STATE)
    hass.services.async_remove(DOMAIN, SERVICE_ASSIGN)
    hass.services.async_remove(DOMAIN, SERVICE_CLONE_STORY)
