# Personal OS - Core System

The portable engine of Personal OS. This folder contains system components that can be shared across repos.

## Folder Structure

```
core/
├── agents/           # Specialized agent instructions (Phase 3)
│   ├── README.md     # Agent overview and architecture
│   ├── orchestrator.md      # Planned
│   ├── context-gatherer.md  # Planned
│   ├── analyzer.md          # Planned
│   ├── workflow.md          # Planned
│   └── reflection.md        # Planned
│
├── docs/             # System documentation
│   ├── PRD.md                    # Product requirements
│   ├── SPEC-agent-architecture.md # Multi-agent design
│   ├── schema-v2-update-plan.md  # Schema migration plan
│   └── implementation-plan-v2.md # Implementation roadmap
│
├── templates/        # User-facing templates
│   ├── AGENTS.md     # Main AI instructions (Schema v2.0)
│   ├── CLAUDE.md     # Claude Code instructions
│   ├── config.yaml   # Configuration template
│   └── gitignore     # Recommended .gitignore
│
├── mcp/              # MCP server for task management
│   └── server.py     # Tool implementations
│
├── evals/            # Session evaluation framework
│   └── README.md     # Eval workflow guide
│
└── README.md         # This file
```

## Quick Start

### For New Users

1. Copy `templates/AGENTS.md` to your project root
2. Copy `templates/config.yaml` and customize
3. Create `Tasks/`, `Knowledge/`, `Archive/` folders
4. Start using with your AI assistant (Cursor, Claude, etc.)

### For Developers

See `docs/` for architecture and implementation details:
- **PRD.md** — Product requirements and user stories
- **SPEC-agent-architecture.md** — Multi-agent system design
- **schema-v2-update-plan.md** — Task schema documentation

## Components

### Templates (`templates/`)

User-facing configuration files. Copy these to your project root.

| File | Purpose |
|------|---------|
| `AGENTS.md` | AI assistant instructions (Schema v2.0) |
| `CLAUDE.md` | Claude Code specific instructions |
| `config.yaml` | Customizable configuration |

**Important:** Keep `templates/AGENTS.md` in sync with root `AGENTS.md`.

### Agents (`agents/`)

Specialized AI agents for the multi-agent architecture (Phase 3 ✅):

| Agent | File | Purpose |
|-------|------|---------|
| Orchestrator | `orchestrator.md` | Coordinates scheduling and routing |
| Context Gatherer | `context-gatherer.md` | Fetches Slack, Jira, Confluence, Git data |
| Analyzer | `analyzer.md` | Validates priorities, statuses, due dates |
| Workflow | `workflow.md` | Daily Briefing, Closing, Status checks |
| Reflection | `reflection.md` | Weekly/quarterly retrospectives |

See `agents/README.md` for architecture details and data flow diagrams.

### Documentation (`docs/`)

System documentation (not user knowledge):

| Doc | Purpose |
|-----|---------|
| PRD.md | Product requirements, user stories, success metrics |
| SPEC-agent-architecture.md | Multi-agent system design |
| schema-v2-update-plan.md | Schema v2.0 migration details |
| implementation-plan-v2.md | Phased implementation roadmap |

### MCP Server (`mcp/`)

Model Context Protocol server providing tools for AI assistants:

- `list_tasks` — Filter and view tasks
- `create_task` — Create with auto-categorization
- `update_task_status` — Change task status
- `process_backlog_with_dedup` — Smart backlog processing

### Evaluations (`evals/`)

Session evaluation framework for improving AI workflows:

1. Capture Claude Code sessions
2. Generate evaluation files
3. Review and annotate
4. Apply improvements to AGENTS.md

See `evals/README.md` for workflow details.

## Schema v2.0

Current task schema includes:

```yaml
---
title: [Task name]
category: [technical|outreach|research|writing|admin|personal|other]
priority: [P0|P1|P2|P3]
status: [n|s|b|d]  # not_started | started | blocked | done

# Blocking (when status: b)
blocked_type: [external|dependency|decision]
blocked_by: [Who/what is blocking]
blocked_expected: [YYYY-MM-DD]

# Dates
created_date: [YYYY-MM-DD]
due_date: [YYYY-MM-DD]

# Focus (when status: s with subtasks)
next_action: [Single action with earliest due date]
next_action_due: [YYYY-MM-DD]
---
```

See `docs/schema-v2-update-plan.md` for full documentation.

## Implementation Phases

| Phase | Status | Focus |
|-------|--------|-------|
| 1. Foundation | ✅ Complete | Task files, workflows, Slack integration |
| 2. Schema v2.0 | ✅ Complete | next_action, blocked fields, validation |
| 3. Multi-Agent | ✅ Complete | Specialized agents in `core/agents/` |
| 4. Integration | 🔲 Planned | Connect agents to scripts & workflows |

## License

MIT - Use freely for personal or commercial projects.
