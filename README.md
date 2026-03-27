# StoryFlow - Home Assistant Custom Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![License](https://img.shields.io/github/license/PavelD/hacs-storyflow-itegration)](LICENSE)

**Track your projects and tasks right in Home Assistant!**

---

## 📍 Development Status

**Current Version:** v0.1.0-dev (In Active Development)

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

#### 🔄 Milestone 3: Automation Support (In Progress - Next Release)
- Services for Home Assistant automations
- Update task states via automations
- Assign tasks to people programmatically
- Full documentation for service usage

#### ⏳ Milestone 4: Task Management (Planned)
- Add new tasks to existing stories
- Delete completed tasks
- Update task details
- Manage tasks dynamically

#### ⏳ Milestone 5: Advanced Features (Planned)
- Clone stories for recurring projects
- Rich service documentation in Home Assistant UI
- Example automations and blueprints

### 🎯 What You Can Do Now

**✅ Available Today:**
- ✨ Create stories for your home projects
- 📋 Add tasks with descriptions and assignments
- 📊 Monitor progress in Lovelace dashboards
- 👥 Track who's responsible for each task
- 🔄 View task states (todo, in progress, done)

**⏳ Coming Soon (Next Release):**
- 🤖 Trigger automations based on task completion
- ✏️ Modify tasks through Home Assistant services
- 🔔 Send notifications when tasks change state
- 📱 Integrate with mobile notifications

**💡 Use Cases This Integration is Perfect For:**
- 🏠 Home improvement project tracking
- 🧹 Family chore management
- 📦 Moving checklist coordination
- 🎉 Event planning and task delegation
- 🎯 Personal goal tracking

### ⚠️ Important Note

**Services are not functional yet!** While you can create stories and view tasks, automation services will be enabled in the next release. This means:
- ❌ You cannot modify tasks after story creation
- ❌ Automations cannot interact with tasks yet
- ❌ No programmatic task updates available

**Why Release Now?** 
We're sharing early to gather feedback and let users see the vision. The foundation is solid, and automation support is coming soon!

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

## 🧪 For Developers

Interested in contributing? This integration is actively developed with high-quality standards:

- **90+ automated tests** ensure reliability
- **~90% code coverage** for confidence in changes
- **Python code quality** enforced with linting and formatting

### Quick Start for Contributors

```bash
# Clone and set up
git clone https://github.com/PavelD/hacs-storyflow-itegration.git
cd hacs-storyflow-itegration
pip install -r requirements_tests.txt

# Run tests
pytest

# Check your changes
pytest --cov=custom_components.storyflow
```

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for detailed development roadmap and technical architecture.

---

## 🗺️ Planned Features

### Coming in Next Releases

**Automation Services** (Next Release - Milestone 3)
- Change task states from automations
- Assign tasks to people automatically
- Trigger actions based on task progress
- Example: "When kitchen task is done, send notification"

**Task Management** (Milestone 4)
- Add new tasks to existing stories
- Remove completed tasks
- Edit task descriptions and assignments
- Update task details on the fly

**Advanced Features** (Milestone 5+)
- Copy stories for recurring projects
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
