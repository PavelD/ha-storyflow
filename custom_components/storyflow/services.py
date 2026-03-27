"""Services for StoryFlow."""

import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, TASK_STATES

_LOGGER = logging.getLogger(__name__)

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
    """Register services with reference counting."""
    # Only register services if this is the first config entry
    if hass.data[DOMAIN].get("service_ref_count", 0) == 0:
        _LOGGER.debug("Registering StoryFlow services")

        async def set_state_service(call: ServiceCall) -> None:
            """Set task state."""
            task_id = call.data["task_id"]
            new_state = call.data["new_state"]

            _LOGGER.debug(
                "Service call: set_task_state for %s to %s", task_id, new_state
            )

            # Find task entity from the registry
            task_entity = hass.data[DOMAIN]["task_entities"].get(task_id)
            if task_entity is None:
                error_msg = f"Task '{task_id}' not found"
                _LOGGER.error(error_msg)
                raise ValueError(error_msg)

            try:
                # Update task state (persists to storage)
                await task_entity.async_update_state(new_state)
                _LOGGER.info(
                    "Successfully updated task %s to state %s", task_id, new_state
                )
            except ValueError as err:
                _LOGGER.error("Failed to update task %s: %s", task_id, err)
                raise

        async def assign_service(call: ServiceCall) -> None:
            """Assign task to person."""
            task_id = call.data["task_id"]
            person_id = call.data.get("person_id")

            # TODO: Implement - find task entity and update assigned_to
            _LOGGER.info(f"Assigning task {task_id} to {person_id}")

        async def clone_story_service(call: ServiceCall) -> None:
            """Clone a story."""
            story_id = call.data["story_id"]
            new_title = call.data.get("new_story_name")

            # TODO: Implement - duplicate story with reset tasks
            _LOGGER.info(f"Cloning story {story_id} to {new_title}")

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

    # Increment reference count
    hass.data[DOMAIN]["service_ref_count"] += 1
    _LOGGER.debug("Service reference count: %d", hass.data[DOMAIN]["service_ref_count"])


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services with reference counting."""
    # Decrement reference count
    hass.data[DOMAIN]["service_ref_count"] -= 1
    _LOGGER.debug("Service reference count: %d", hass.data[DOMAIN]["service_ref_count"])

    # Only remove services when the last config entry is unloaded
    if hass.data[DOMAIN]["service_ref_count"] <= 0:
        _LOGGER.debug("Unregistering StoryFlow services")
        hass.services.async_remove(DOMAIN, SERVICE_SET_STATE)
        hass.services.async_remove(DOMAIN, SERVICE_ASSIGN)
        hass.services.async_remove(DOMAIN, SERVICE_CLONE_STORY)
