# StoryFlow - Home Assistant Custom Integration

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
![GitHub release](https://img.shields.io/github/v/release/PavelD/ha-storyflow)
![GitHub license](https://img.shields.io/github/license/PavelD/ha-storyflow)

**Track your projects and tasks right in Home Assistant!**

---

## 📍 Development Status

**Current Version:** v0.0.1 (In Active Development)

### Development Milestones

#### ✅ Milestone 1: Story & Task Display (Complete)
- Create and view stories through Home Assistant UI
- Display tasks as sensor entities  
- Track overall progress with completion percentage
- Support multiple stories simultaneously
- All data persists across Home Assistant restarts

#### ✅ Milestone 2: Data Foundation (Complete)
- Robust storage system for stories and tasks
- Data validation and error handling
- Support for task states (todo, in progress, done, etc.)
- Person assignment tracking
- Comprehensive test coverage (90+ tests)

#### ✅ Milestone 3: Automation Support (Complete)
- ✅ Services for Home Assistant automations
- ✅ Update task states via automations (`set_task_state`)
- ✅ Assign tasks to people programmatically (`assign_task`)
- ✅ Comprehensive error handling with custom exceptions

#### ✅ Milestone 4: Task Management (Complete)
- ✅ Add new tasks to existing stories (`add_task` service)
- ✅ Auto-generates unique task IDs within a story
- ✅ Full state validation (todo, progress, review, done, rejected)
- ✅ Optional person assignment at task creation
- ✅ Progress entity auto-refreshes on task addition and deletion
- ✅ Delete tasks from stories (`delete_task` service)
- ✅ Update task title and/or description (`update_task` service)
- ✅ Clone stories for recurring projects with tasks reset (`clone_story` service)

#### ⏳ Milestone 5: Documentation & Examples (Planned)
- Rich service documentation in Home Assistant UI
- Example automations and blueprints
- Interactive Lovelace card examples

### 🎯 What You Can Do Now

**✅ Available Today:**
- ✨ Create stories for your home projects
- 📋 Add tasks with descriptions and assignments
- 📊 Monitor progress in Lovelace dashboards
- 👥 Track who's responsible for each task
- 🔄 View task states (todo, progress, review, done, rejected)
- 🤖 Update task states via automations (`set_task_state`)
- 👤 Assign/unassign tasks programmatically (`assign_task`)
- ⚡ Trigger actions based on task changes
- ➕ Add new tasks to stories dynamically (`add_task`)
- 🗑️ Delete tasks from stories (`delete_task`)
- ✏️ Update task title and/or description (`update_task`)
- 🔁 Clone stories for recurring projects with tasks reset (`clone_story`)
- 🔄 Progress entity auto-updates when tasks are added, removed, or when a story is cloned

**⏳ Coming Soon (Milestone 5):**
- 📖 Rich service documentation in Home Assistant UI
- 📝 Example automations and blueprints
- 🔔 Send notifications when tasks change state

**💡 Use Cases This Integration is Perfect For:**
- 🏠 Home improvement project tracking
- 🧹 Family chore management
- 📦 Moving checklist coordination
- 🎉 Event planning and task delegation
- 🎯 Personal goal tracking

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
4. Add repository URL: `https://github.com/PavelD/ha-storyflow`
5. Select category: **Integration**
6. Click **Add**
7. Search for "**StoryFlow**" and click **Download**
8. Restart Home Assistant

### Manual Installation

1. Download the latest release from [GitHub Releases](https://github.com/PavelD/ha-storyflow/releases)
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

## 🤖 Services

### ✅ Available Services

#### `storyflow.add_task`
**Add a new task to an existing story**

```yaml
service: storyflow.add_task
data:
  story_id: "kitchen"
  title: "Paint walls"
  description: "Choose color and paint the living room walls"
  assigned_to: "person.john"
  state: "todo"
```

**Parameters:**
- `story_id` (required): ID of the story to add the task to (e.g., `kitchen`, `morning_routine`)
- `title` (required): Title of the new task
- `description` (optional): Detailed task description
- `assigned_to` (optional): Person entity ID to assign the task to
- `state` (optional): Initial state — `todo` (default), `progress`, `review`, `done`, or `rejected`

**What happens when you add a task:**
1. A unique task ID is generated (e.g., `kitchen_task_3`)
2. A new sensor entity appears in Home Assistant
3. The progress entity recalculates and updates instantly

**Example Automation:**
```yaml
automation:
  - alias: "Add weekend task via button press"
    trigger:
      - platform: state
        entity_id: input_button.add_weekend_task
    action:
      - service: storyflow.add_task
        data:
          story_id: "weekend_chores"
          title: "Mow the lawn"
          assigned_to: "person.john"
```

#### `storyflow.set_task_state`
**Change the state of a task**

```yaml
service: storyflow.set_task_state
data:
  task_id: "kitchen_task_0"
  new_state: "done"
```

**Parameters:**
- `task_id` (required): ID of the task to update
- `new_state` (required): New state - `todo`, `progress`, `review`, `done`, or `rejected`

**Example Automation:**
```yaml
automation:
  - alias: "Mark task done at 9 AM"
    trigger:
      - platform: time
        at: "09:00:00"
    action:
      - service: storyflow.set_task_state
        data:
          task_id: "morning_routine_task_0"
          new_state: "done"
```

#### `storyflow.assign_task`
**Assign or unassign a task to a person**

```yaml
# Assign task
service: storyflow.assign_task
data:
  task_id: "kitchen_task_1"
  person_id: "person.john"

# Unassign task (omit person_id)
service: storyflow.assign_task
data:
  task_id: "kitchen_task_1"
```

**Parameters:**
- `task_id` (required): ID of the task to assign
- `person_id` (optional): Person entity ID. Omit to unassign the task.

**Example Automation:**
```yaml
automation:
  - alias: "Auto-assign task to available person"
    trigger:
      - platform: state
        entity_id: person.john
        to: "home"
    action:
      - service: storyflow.assign_task
        data:
          task_id: "evening_chores_task_0"
          person_id: "person.john"
```

#### `storyflow.delete_task`
**Remove a task from a story**

```yaml
service: storyflow.delete_task
data:
  task_id: "kitchen_task_2"
```

**Parameters:**
- `task_id` (required): ID of the task to delete

**What happens when you delete a task:**
1. The task is removed from storage
2. Its sensor entity is removed from Home Assistant
3. The progress entity recalculates and updates instantly

#### `storyflow.update_task`
**Update a task's title and/or description**

```yaml
service: storyflow.update_task
data:
  task_id: "kitchen_task_1"
  title: "Install new cabinets"
  description: "Choose and install modern kitchen cabinets"
```

**Parameters:**
- `task_id` (required): ID of the task to update
- `title` (optional): New title for the task
- `description` (optional): New description for the task
- At least one of `title` or `description` must be provided

#### `storyflow.clone_story`
**Clone a story with all tasks reset**

```yaml
service: storyflow.clone_story
data:
  story_id: "kitchen"
  new_story_name: "Kitchen Renovation (Round 2)"
```

**Parameters:**
- `story_id` (required): ID of the story to clone
- `new_story_name` (optional): Name for the cloned story. Defaults to original name + " (Copy)"

**What happens when you clone a story:**
1. A new story is created with a unique ID derived from the new name
2. All tasks are copied with state reset to `todo` and assignments cleared
3. New sensor entities (tasks + progress) appear in Home Assistant instantly

**Example Automation:**
```yaml
automation:
  - alias: "Clone chore list every Monday"
    trigger:
      - platform: time
        at: "06:00:00"
    condition:
      - condition: time
        weekday:
          - mon
    action:
      - service: storyflow.clone_story
        data:
          story_id: "weekly_chores"
          new_story_name: "Weekly Chores"
```

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

## 🧪 For Developers

Interested in contributing? This integration is actively developed with high-quality standards:

- **142+ automated tests** ensure reliability
- **~90% code coverage** for confidence in changes
- **Python code quality** enforced with linting and formatting

### Quick Start for Contributors

```bash
# Clone and set up
git clone https://github.com/PavelD/ha-storyflow.git
cd ha-storyflow
pip install -r requirements_tests.txt

# Run tests
pytest

# Check your changes
pytest --cov=custom_components.storyflow
```

## 🗺️ Planned Features

### Coming in Next Releases

**Documentation & Examples** (Milestone 5)
- Rich service documentation in Home Assistant UI
- Example automations and blueprints
- Interactive Lovelace card examples

**Future Vision** (Milestone 6+)
- Interactive Lovelace card with quick actions
- Task dependencies ("Task B needs Task A first")
- Due dates and reminders
- Task comments and history
- Statistics and dashboards

### Long-term Vision

Beyond the core features, we envision:
- 📅 Calendar integration for due dates
- 🔔 Smart notifications based on task priority
- 📱 Mobile app integration
- 🎯 Sprint planning and velocity tracking
- 👥 Multi-user collaboration features
- 📊 Advanced analytics and reporting

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

- **Issues**: [GitHub Issues](https://github.com/PavelD/ha-storyflow/issues)
- **Discussions**: [GitHub Discussions](https://github.com/PavelD/ha-storyflow/discussions)

---

**🚧 Under Active Development**
