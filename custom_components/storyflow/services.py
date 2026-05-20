"""Services for StoryFlow."""

import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, TASK_STATES
from .exceptions import TaskNotFoundError
from .task_entity import get_task_unique_id

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_STATE = "set_task_state"
SERVICE_ASSIGN = "assign_task"
SERVICE_ADD_TASK = "add_task"
SERVICE_DELETE_TASK = "delete_task"
SERVICE_UPDATE_TASK = "update_task"
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

ADD_TASK_SCHEMA = vol.Schema(
    {
        vol.Required("story_id"): cv.string,
        vol.Required("title"): cv.string,
        vol.Optional("description"): cv.string,
        vol.Optional("assigned_to"): cv.string,
        vol.Optional("state", default="todo"): vol.In(TASK_STATES),
    }
)

DELETE_TASK_SCHEMA = vol.Schema(
    {
        vol.Required("task_id"): cv.string,
    }
)

UPDATE_TASK_SCHEMA = vol.Schema(
    {
        vol.Required("task_id"): cv.string,
        vol.Optional("title"): cv.string,
        vol.Optional("description"): cv.string,
    }
)

CLONE_STORY_SCHEMA = vol.Schema(
    {
        vol.Required("story_id"): cv.string,
        vol.Optional("new_story_name"): cv.string,
    }
)


async def _get_manager_and_storage_for_story(
    hass: HomeAssistant, story_id: str
) -> tuple:
    """Find the (manager, storage) pair that owns *story_id*.

    Iterates over every entry registered under ``hass.data[DOMAIN]`` and
    returns the first pair whose storage reports the story as existing.

    Args:
        hass: The Home Assistant instance.
        story_id: The story to look up.

    Returns:
        A ``(manager, storage_handler)`` tuple.

    Raises:
        ValueError: If no entry_data can satisfy the story_id.
    """
    for entry_data in hass.data[DOMAIN].values():
        if (
            isinstance(entry_data, dict)
            and "manager" in entry_data
            and "storage" in entry_data
        ):
            if await entry_data["storage"].async_story_exists(story_id):
                return entry_data["manager"], entry_data["storage"]

    _LOGGER.error("No manager found for story '%s'", story_id)
    raise ValueError(f"Story '{story_id}' not found")


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
            task_entity = hass.data[DOMAIN].get("task_entities", {}).get(task_id)
            if task_entity is None:
                _LOGGER.error("Task '%s' not found", task_id)
                raise TaskNotFoundError(task_id)

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
            person_id = call.data.get("person_id")  # None = unassign

            _LOGGER.debug("Service call: assign_task for %s to %s", task_id, person_id)

            # Find task entity from the registry
            task_entity = hass.data[DOMAIN].get("task_entities", {}).get(task_id)
            if task_entity is None:
                _LOGGER.error("Task '%s' not found", task_id)
                raise TaskNotFoundError(task_id)

            try:
                # Update assignment (persists to storage)
                await task_entity.async_update_assignment(person_id)
                action = (
                    "unassigned" if person_id is None else f"assigned to {person_id}"
                )
                _LOGGER.info("Successfully %s task %s", action, task_id)
            except ValueError as err:
                _LOGGER.error("Failed to assign task %s: %s", task_id, err)
                raise

        async def add_task_service(call: ServiceCall) -> None:
            """Add a new task to a story."""
            story_id = call.data["story_id"]
            title = call.data["title"]
            description = call.data.get("description", "")
            assigned_to = call.data.get("assigned_to")
            state = call.data.get("state", "todo")

            _LOGGER.debug(
                "Service call: add_task to story %s with title '%s'", story_id, title
            )

            # Check if story exists by trying to get its callback
            if story_id not in hass.data[DOMAIN].get("entity_callbacks", {}):
                _LOGGER.error("Story '%s' not found or not set up", story_id)
                raise ValueError(f"Story '{story_id}' not found")

            try:
                # Find the manager and storage for this story
                manager, storage_handler = await _get_manager_and_storage_for_story(
                    hass, story_id
                )

                # Add task via manager (validates and persists to storage)
                task_data = await manager.async_add_task(
                    story_id=story_id,
                    title=title,
                    description=description,
                    assigned_to=assigned_to,
                    state=state,
                )

                task_id = task_data["id"]
                _LOGGER.debug("Created task data with ID: %s", task_id)

                # Import TaskEntity here to avoid circular imports
                from .task_entity import TaskEntity

                # Create new TaskEntity
                task_entity = TaskEntity(
                    story_id=story_id,
                    task_id=task_id,
                    title=title,
                    description=description,
                    storage_handler=storage_handler,
                    assigned_to=assigned_to,
                    state=state,
                    order=task_data.get("order", 0),
                )

                # Register entity with Home Assistant using stored callback
                async_add_entities = hass.data[DOMAIN]["entity_callbacks"][story_id]
                async_add_entities([task_entity])

                # Add entity to entity lookup registry
                hass.data[DOMAIN]["task_entities"][task_id] = task_entity

                # Update progress entity
                progress_entity = hass.data[DOMAIN]["progress_entities"].get(story_id)
                if progress_entity:
                    # Reload tasks to update progress calculation
                    story_data = await storage_handler.load_story(story_id)
                    progress_entity.tasks = story_data.get("tasks", [])
                    progress_entity.async_write_ha_state()

                _LOGGER.info(
                    "Successfully added task '%s' (ID: %s) to story '%s'",
                    title,
                    task_id,
                    story_id,
                )

            except ValueError as err:
                _LOGGER.error("Failed to add task to story %s: %s", story_id, err)
                raise

        async def delete_task_service(call: ServiceCall) -> None:
            """Delete a task from a story."""
            task_id = call.data["task_id"]

            _LOGGER.debug("Service call: delete_task for %s", task_id)

            # Find task entity from the registry
            task_entity = hass.data[DOMAIN].get("task_entities", {}).get(task_id)
            if task_entity is None:
                _LOGGER.error("Task '%s' not found", task_id)
                raise TaskNotFoundError(task_id)

            story_id = task_entity.story_id

            try:
                # Find the manager and storage for this story
                manager, storage_handler = await _get_manager_and_storage_for_story(
                    hass, story_id
                )

                # Delete task from storage via manager (validates existence)
                await manager.async_delete_task(story_id, task_id)

                # Remove entity from Home Assistant entity registry
                from homeassistant.helpers import entity_registry as er

                entity_reg = er.async_get(hass)
                unique_id = get_task_unique_id(task_id)
                ha_entity_id = entity_reg.async_get_entity_id(
                    "sensor", DOMAIN, unique_id
                )
                if ha_entity_id:
                    entity_reg.async_remove(ha_entity_id)
                    _LOGGER.debug(
                        "Removed entity %s from entity registry", ha_entity_id
                    )

                # Remove from task_entities lookup registry
                hass.data[DOMAIN]["task_entities"].pop(task_id, None)

                # Update progress entity to recalculate stats
                progress_entity = hass.data[DOMAIN]["progress_entities"].get(story_id)
                if progress_entity:
                    story_data = await storage_handler.load_story(story_id)
                    progress_entity.tasks = story_data.get("tasks", [])
                    progress_entity.async_write_ha_state()

                _LOGGER.info(
                    "Successfully deleted task '%s' from story '%s'",
                    task_id,
                    story_id,
                )

            except ValueError as err:
                _LOGGER.error("Failed to delete task %s: %s", task_id, err)
                raise

        async def update_task_service(call: ServiceCall) -> None:
            """Update a task's title and/or description."""
            task_id = call.data["task_id"]
            title = call.data.get("title")
            description = call.data.get("description")

            _LOGGER.debug("Service call: update_task for %s", task_id)

            # Validate at least one field is provided
            if title is None and description is None:
                raise ValueError(
                    "At least one of 'title' or 'description' must be provided"
                )

            # Find task entity from the registry
            task_entity = hass.data[DOMAIN].get("task_entities", {}).get(task_id)
            if task_entity is None:
                _LOGGER.error("Task '%s' not found", task_id)
                raise TaskNotFoundError(task_id)

            try:
                # Build the updates dict (only include provided fields)
                updates = {}
                if title is not None:
                    updates["title"] = title
                if description is not None:
                    updates["description"] = description

                # Update entity attributes (persists to storage + updates HA state)
                await task_entity.async_update_attributes(**updates)

                _LOGGER.info(
                    "Successfully updated task '%s' with fields: %s",
                    task_id,
                    list(updates.keys()),
                )

            except ValueError as err:
                _LOGGER.error("Failed to update task %s: %s", task_id, err)
                raise

        async def clone_story_service(call: ServiceCall) -> None:
            """Clone a story with all tasks reset to todo."""
            story_id = call.data["story_id"]
            new_story_name = call.data.get("new_story_name")

            _LOGGER.debug("Service call: clone_story for %s", story_id)

            # Find the manager and storage for this story
            manager, storage_handler = await _get_manager_and_storage_for_story(
                hass, story_id
            )

            # Clone the story (validates source, persists new story to storage)
            result = await manager.async_clone_story(story_id, new_story_name)
            new_story_id = result["story_id"]
            new_story_data = result["story_data"]

            # Find an existing async_add_entities callback.
            # All story entities share the same sensor platform so any callback works.
            entity_callbacks = hass.data[DOMAIN].get("entity_callbacks", {})
            async_add_entities = (
                next(iter(entity_callbacks.values())) if entity_callbacks else None
            )

            if async_add_entities is None:
                _LOGGER.warning(
                    "No entity callback available — cloned story '%s' entities will "
                    "appear after the next Home Assistant restart",
                    new_story_id,
                )
            else:
                from .story_progress_entity import StoryProgressEntity
                from .task_entity import TaskEntity

                new_entities = []

                # Progress entity for the cloned story
                progress_entity = StoryProgressEntity(
                    story_id=new_story_id,
                    tasks=new_story_data.get("tasks", []),
                )
                hass.data[DOMAIN]["progress_entities"][new_story_id] = progress_entity
                new_entities.append(progress_entity)

                # Task entities for the cloned story
                for task_data in new_story_data.get("tasks", []):
                    task_entity = TaskEntity(
                        story_id=new_story_id,
                        task_id=task_data["id"],
                        title=task_data["title"],
                        description=task_data.get("description", ""),
                        storage_handler=storage_handler,
                        assigned_to=task_data.get("assigned_to"),
                        state=task_data.get("state", "todo"),
                        order=task_data.get("order", 0),
                    )
                    new_entities.append(task_entity)
                    hass.data[DOMAIN]["task_entities"][task_data["id"]] = task_entity

                # Register the callback for the new story so add_task works on it too
                hass.data[DOMAIN]["entity_callbacks"][new_story_id] = async_add_entities

                # Add all new entities to Home Assistant
                async_add_entities(new_entities)

            _LOGGER.info(
                "Successfully cloned story '%s' → '%s'",
                story_id,
                new_story_id,
            )

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
            SERVICE_ADD_TASK,
            add_task_service,
            schema=ADD_TASK_SCHEMA,
        )

        hass.services.async_register(
            DOMAIN,
            SERVICE_DELETE_TASK,
            delete_task_service,
            schema=DELETE_TASK_SCHEMA,
        )

        hass.services.async_register(
            DOMAIN,
            SERVICE_UPDATE_TASK,
            update_task_service,
            schema=UPDATE_TASK_SCHEMA,
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
        hass.services.async_remove(DOMAIN, SERVICE_ADD_TASK)
        hass.services.async_remove(DOMAIN, SERVICE_DELETE_TASK)
        hass.services.async_remove(DOMAIN, SERVICE_UPDATE_TASK)
        hass.services.async_remove(DOMAIN, SERVICE_CLONE_STORY)
