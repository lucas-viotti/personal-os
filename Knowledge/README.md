# Knowledge

Store **user-specific** reference documents, research, meeting notes, and any persistent information that your tasks might need.

> This directory is for YOUR knowledge—project context, meeting notes, research. System documentation lives in `core/docs/`.

---

## What Goes Here

| Type | Examples |
|------|----------|
| **Project context** | Initiative briefs, stakeholder notes |
| **Meeting notes** | Decisions, action items, attendees |
| **Research** | Market analysis, technical findings |
| **Process docs** | Your personal how-tos, checklists |
| **Prioritization rules** | `prioritization-rules.md` (AI uses this) |
| **Agent feedback** | `agent-feedback.yaml` (tracks approval patterns) |

---

## What Does NOT Go Here

| Type | Where It Lives |
|------|----------------|
| System documentation | `core/docs/` (PRD, SPEC, implementation plans) |
| Agent instructions | `core/agents/` (orchestrator, analyzer, etc.) |
| Templates | `core/templates/` (AGENTS.md, config.yaml) |

---

## Key Files

| File | Purpose |
|------|---------|
| `prioritization-rules.md` | AI prioritization criteria (user-editable) |
| `agent-feedback.yaml` | Tracks your approval/rejection patterns (future) |
| `meetings/` | Meeting transcripts (future) |

---

## Linking from Tasks

Reference knowledge docs in your task files:

```yaml
resource_refs:
  - Knowledge/project-spec.md
  - Knowledge/meeting-notes-2024-01-15.md
```

---

## System Documentation

For system docs (PRD, architecture specs, etc.), see:

```
core/docs/
├── PRD.md                      # Product requirements
├── SPEC-agent-architecture.md  # Multi-agent design
├── schema-v2-update-plan.md    # Schema v2.0 documentation
└── implementation-plan-v2.md   # Implementation roadmap
```
