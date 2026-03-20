# StoryFlow Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![License](https://img.shields.io/github/license/PavelD/hacs-storyflow-itegration)](LICENSE)

**Version:** v0.0.1 - Early Development  
**Status:** 🚧 MVP Infrastructure Only - Services Not Implemented

---

## ⚠️ Current Status

This integration is in **early development phase**. The basic infrastructure for managing stories and tasks is in place, but **automation features are not yet functional**.

### ✅ What Works (v0.0.1)

- **Story Creation**: Create stories via Home Assistant config flow UI
- **Task Display**: Tasks appear as sensor entities in Home Assistant
- **Progress Tracking**: Aggregate progress entity shows completion percentage
- **Multiple Stories**: Support for multiple concurrent story entries
- **Persistence**: Stories and tasks are saved to Home Assistant storage
- **HACS Compatible**: Can be installed as a custom repository

### ⚠️ What Doesn't Work Yet

- **Service Operations**: Services are registered but contain only stub implementations (log messages, no actual operations)
- **Task Modifications**: Cannot modify tasks programmatically or via automations
- **Automation Support**: Services don't perform actions, making automation impossible
- **CRUD Operations**: No add/update/delete task functionality via services

**Bottom Line**: This is a **display-only** integration at the moment. You can view stories and tasks, but cannot interact with them programmatically.

---

## 🎯 Overview

StoryFlow aims to bring agile project management capabilities to Home Assistant. When complete, it will allow you to manage stories (user stories) and tasks with full automation support, person assignment, and real-time progress tracking.

**Intended Use Cases:**
- 🏠 Home improvement projects
- 📋 Family task management
- 🎯 Personal goal tracking
- 🤝 Team collaboration in home environments

---

## 📦 Installation

### Via HACS (Recommended)

1. Open **HACS** in Home Assistant
2. Click on **Integrations**
3. Click the **⋮** menu (top-right) → **Custom repositories**
4. Add repository URL: `https://github.com/PavelD/hacs-storyflow-itegration`
5. Select category: **Integration**
6. Click **Add**
7. Search for "**StoryFlow**" and click **Download**
8. Restart Home Assistant

### Manual Installation

1. Download the latest release from [GitHub Releases](https://github.com/PavelD/hacs-storyflow-itegration/releases)
2. Extract and copy `custom_components/storyflow` to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

---

## ⚙️ Configuration

### Adding a Story

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "**StoryFlow**"
4. Enter your story details:
   - **Story Name**: e.g., "Kitchen Renovation"
   - **Description**: Markdown-formatted description (optional)
   - **Tasks**: Initial tasks (currently set at integration setup only)
5. Click **Submit**

The integration will create:
- Task sensor entities (one per task)
- A progress sensor entity showing completion percentage

---

## 📊 Entities

### Task Entities

**Entity ID Format**: `sensor.storyflow_<story_id>_task_<task_id>`

**State**: Current task state (`todo`, `progress`, `review`, `done`, `rejected`)

**Attributes**:
```yaml
task_id: "1"
description: "Install new cabinets"
state: "progress"
assigned_to: "person.john"
story_id: "kitchen"
```

**Example**:
```yaml
sensor.storyflow_kitchen_task_1:
  state: "progress"
  attributes:
    task_id: "1"
    description: "Install new cabinets"
    assigned_to: "person.john"
```

### Progress Entity

**Entity ID Format**: `sensor.storyflow_<story_id>_progress`

**State**: Percentage complete (0-100)

**Unit**: `%`

**Attributes**:
```yaml
total_tasks: 5
done_tasks: 2
in_progress_tasks: 1
todo_tasks: 2
```

**Example**:
```yaml
sensor.storyflow_kitchen_progress:
  state: 40
  attributes:
    total_tasks: 5
    done_tasks: 2
    in_progress_tasks: 1
    todo_tasks: 2
```

---

## 🚧 Services (Planned, Not Implemented)

The following services are registered but **do not perform any actions** in v0.0.1. They currently only log messages.

### Registered but Non-Functional:
- `storyflow.set_task_state` - Intended to change task states
- `storyflow.assign_task` - Intended to assign tasks to persons
- `storyflow.clone_story` - Intended to duplicate stories

### Planned for Future Versions:
- `storyflow.add_task` - Add new tasks to stories
- `storyflow.update_task` - Update task details
- `storyflow.delete_task` - Remove tasks from stories

**Note**: Until services are implemented, you cannot modify tasks after initial story creation.

---

## 🎨 Lovelace Display

You can display task and progress entities in Lovelace cards:

### Simple Entities Card

```yaml
type: entities
title: Kitchen Renovation
entities:
  - entity: sensor.storyflow_kitchen_progress
  - entity: sensor.storyflow_kitchen_task_1
  - entity: sensor.storyflow_kitchen_task_2
  - entity: sensor.storyflow_kitchen_task_3
```

### Progress Card

```yaml
type: gauge
entity: sensor.storyflow_kitchen_progress
min: 0
max: 100
name: Project Progress
```

---

## 🧪 Development

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/PavelD/hacs-storyflow-itegration.git
cd hacs-storyflow-itegration

# Install development dependencies
pip install -r requirements_tests.txt
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=custom_components.storyflow --cov-report=html

# Run specific test file
pytest tests/test_services.py
```

### Test Suite

The project includes 48 tests covering:
- Service registration infrastructure
- Task entity initialization
- Progress calculation logic
- Integration lifecycle management

**Note**: Tests verify infrastructure, not functional implementations. Services are mocked/stubbed.

### Code Quality

```bash
# Format code
black custom_components/ tests/

# Linting
pylint custom_components/
```

---

## 🗺️ Roadmap

### Current Version (v0.0.1) ✅
- [x] Config flow for story creation
- [x] Task entities with state display
- [x] Progress calculation entity
- [x] Persistent storage
- [x] Multiple story support
- [x] Service registration infrastructure
- [x] Test infrastructure (48 tests)

### Planned for Future Versions
**Note**: Timeline and feature set determined by project maintainer.

**Core Functionality** (Required for v1.0):
- [ ] Implement functional `set_task_state` service
- [ ] Implement functional `assign_task` service
- [ ] Add `add_task` service (create tasks programmatically)
- [ ] Add `update_task` service (modify existing tasks)
- [ ] Add `delete_task` service (remove tasks)
- [ ] Add `services.yaml` for UI documentation
- [ ] Enable automation support

**Enhanced Features** (Post-v1.0):
- [ ] Create new stories via service (currently config flow only)
- [ ] Clone story functionality
- [ ] Interactive Lovelace card with task management
- [ ] State flow enforcement (optional validation)
- [ ] Task dependencies
- [ ] Task due dates and reminders
- [ ] Task comments and history
- [ ] Bulk operations
- [ ] Import/export capabilities
- [ ] Statistics dashboard

---

## ⚙️ Architecture Notes

### Service Infrastructure

Services are registered using reference counting to support multiple story entries. However, the actual service implementations are placeholders:

```python
# Current implementation (v0.0.1)
async def set_state_service(call: ServiceCall) -> None:
    """Set task state."""
    # TODO: Implement - find task entity and update state
    _LOGGER.info(f"Setting task {task_id} to state {new_state}")
```

### Entity Management

- Task entities are created from stored task data
- Progress entity calculates completion from task states
- Entities are read-only in current version

---

## 🤝 Contributing

Contributions are welcome! 

**Before Contributing:**
1. Check current roadmap and open issues
2. Discuss major changes via GitHub issues first
3. Add tests for new functionality
4. Ensure all tests pass
5. Follow existing code style

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built for the [Home Assistant](https://www.home-assistant.io/) community
- Compatible with [HACS](https://hacs.xyz/)
- Inspired by agile project management methodologies

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/PavelD/hacs-storyflow-itegration/issues)
- **Discussions**: [GitHub Discussions](https://github.com/PavelD/hacs-storyflow-itegration/discussions)

---

## 📝 Version History

### v0.0.1 (Current)
- Initial release
- MVP infrastructure
- Display-only functionality
- Service stubs (non-functional)

---

**🚧 Under Active Development**
