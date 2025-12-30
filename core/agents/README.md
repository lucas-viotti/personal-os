# Specialized Agents

This folder contains instruction files for the multi-agent architecture.

## Agent Files

| Agent | File | Status | Purpose |
|-------|------|--------|---------|
| Orchestrator | `orchestrator.md` | ✅ Created | Coordinates all agents, manages scheduling |
| Context Gatherer | `context-gatherer.md` | ✅ Created | Fetches data from Slack, Jira, Confluence, Git |
| Analyzer | `analyzer.md` | ✅ Created | Validates priorities, statuses, due dates |
| Workflow | `workflow.md` | ✅ Created | Generates Daily Briefing, Closing, Status checks |
| Reflection | `reflection.md` | ✅ Created | Weekly/monthly/quarterly retrospectives |

## Architecture

See [SPEC-agent-architecture.md](../docs/SPEC-agent-architecture.md) for full design.

```
┌─────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR AGENT                          │
│                                                                  │
│  • Time-based triggers (9:00 AM, 5:30 PM, Friday 4 PM)         │
│  • Event-based triggers (user prompts)                          │
│  • Routes to specialized agents                                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
   │   CONTEXT   │──▶│  ANALYZER   │──▶│  WORKFLOW   │
   │   GATHERER  │   │             │   │             │
   └─────────────┘   └─────────────┘   └─────────────┘
                                              │
                                              ▼
                                       ┌─────────────┐
                                       │ REFLECTION  │
                                       └─────────────┘
```

## Data Flow

### Daily Briefing (9:00 AM)
```
Orchestrator (trigger) → Context Gatherer (last 24h) → Analyzer → Workflow → User
```

### Daily Closing (5:30 PM)
```
Orchestrator (trigger) → Context Gatherer (since briefing) → Analyzer → Workflow → User
```

### Weekly Review (Friday 4 PM)
```
Orchestrator (trigger) → Context Gatherer (last 7d) → Analyzer → Reflection → User
```

## Implementation Status

| Phase | Status | Focus |
|-------|--------|-------|
| **Phase 1** | ✅ Complete | Foundation (task files, workflows, Slack integration) |
| **Phase 2** | ✅ Complete | Schema v2.0 (next_action, blocked fields, validation) |
| **Phase 3** | ✅ Complete | Multi-agent architecture (this folder) |
| **Phase 4** | 🔲 Planned | Integration with existing scripts & workflows |

## How Agents Work

Each agent file contains:

1. **Overview** — What the agent does
2. **Responsibilities** — Specific tasks it handles
3. **Input Schema** — What data it receives (YAML format)
4. **Output Schema** — What it produces (YAML format)
5. **Logic/Prompt Template** — How it processes data
6. **Acceptance Criteria** — How to validate it works
7. **Configuration** — Customizable settings

## Agent Types

| Agent | Type | Why |
|-------|------|-----|
| Context Gatherer | **Code-based** | Deterministic data fetching (MCPs + file I/O) |
| Analyzer | **LLM-based** | Requires reasoning about priorities/context |
| Workflow | **LLM-based** | Requires natural language generation |
| Reflection | **LLM-based** | Requires synthesis and summarization |
| Orchestrator | **Hybrid** | Logic routing + LLM for intent matching |

## Configuration

Key settings in `config.yaml`:

```yaml
# Analyzer cache TTL (configurable, default 25 min)
analyzer:
  cache_ttl: 25  # minutes

# Context gathering sources
context_gatherer:
  slack:
    enabled: true
  jira:
    enabled: true
    project_key: "${JIRA_PROJECT}"
  confluence:
    enabled: true
    spaces: "${CONFLUENCE_SPACES}"

# Workflow settings
workflow:
  daily_briefing:
    max_focus_items: 3
```

> **Note:** The 25-minute cache TTL was chosen based on personal workflow patterns. Users who receive frequent updates via Slack/Jira may want to reduce this; users who prefer fewer API calls can increase it.

## Using with Claude Code / Cursor

Agent files are designed to be self-contained for AI coding assistants:

1. **Each agent declares interfaces** — Clear inputs/outputs
2. **No circular dependencies** — Context → Analyzer → Workflow (one direction)
3. **Clear boundaries** — Each agent has explicit responsibilities
4. **Testable in isolation** — Can validate against specific test cases

When working on a specific agent, the AI only needs to load that agent's file plus the SPEC.

## Quick Reference

| Need | Agent | Command Example |
|------|-------|-----------------|
| Morning focus | Workflow | "What should I focus on today?" |
| End-of-day summary | Workflow | "Summarize my day" |
| Status on initiative | Workflow | "Where are we on Troy Beta?" |
| Weekly review | Reflection | "Generate weekly review" |
| Check priorities | Analyzer | "Are my task priorities correct?" |
