# Orchestrator Agent

**Purpose:** Coordinate all specialized agents and manage user interactions.

**Version:** 1.0  
**Last Updated:** 2024-12-30

---

## Overview

The Orchestrator is the central coordinator of the Personal OS multi-agent system. It:
1. Receives triggers (scheduled or on-demand)
2. Determines which workflow to execute
3. Calls specialized agents in sequence
4. Aggregates outputs for user review
5. Executes approved actions

---

## Responsibilities

| Responsibility | Description |
|----------------|-------------|
| **Scheduling** | Trigger agents at appropriate times |
| **Routing** | Direct requests to the right specialized agent |
| **Aggregation** | Combine agent outputs into user-facing summaries |
| **Approval Flow** | Present recommendations for user review |
| **Execution** | Execute approved actions (post to Slack, update Jira) |

---

## Trigger Types

### Time-Based Triggers

| Workflow | Default Time | Context Period |
|----------|-------------|----------------|
| Daily Briefing | 9:00 AM | Last 24 hours |
| Daily Closing | 5:30 PM | Since last briefing |
| Weekly Review | Friday 4:00 PM | Last 7 days |

### Event-Based Triggers

| User Request | Maps To | Context Period |
|--------------|---------|----------------|
| "What should I focus on?" | Daily Briefing | Last 24h |
| "Summarize my day" | Daily Closing | Since last briefing |
| "Weekly review" | Weekly Review | Last 7 days |
| "Where are we on X?" | Status Check | Last 7 days |
| "Check my priorities" | Ad-hoc Analysis | Configurable |

---

## Workflow Routing

```
┌─────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR                                │
│                                                                  │
│  1. Receive trigger (time-based or event-based)                 │
│  2. Determine workflow type                                      │
│  3. Set context period                                          │
│  4. Call agents in sequence                                      │
│  5. Aggregate outputs                                           │
│  6. Present to user for review/approval                         │
│  7. Execute approved actions                                     │
└─────────────────────────────────────────────────────────────────┘
```

### Agent Call Sequences

| Workflow | Agent Sequence |
|----------|----------------|
| Daily Briefing | Context Gatherer → Analyzer → Workflow |
| Daily Closing | Context Gatherer → Analyzer → Workflow |
| Weekly Review | Context Gatherer → Analyzer → Reflection |
| Status Check | Context Gatherer → Workflow |
| Ad-hoc Analysis | Context Gatherer → Analyzer |

---

## Input Schema

```yaml
trigger:
  type: scheduled | on_demand | event
  
  # For scheduled triggers
  scheduled:
    time: "09:00"
    workflow: "daily_briefing"
    
  # For on-demand triggers (user request)
  on_demand:
    request: "What should I focus on today?"
    workflow: "daily_briefing"  # Orchestrator maps request → workflow
    
  # For event triggers (system events)
  event:
    source: "file_change" | "mcp_notification" | "external_webhook"
    details:
      changed_file: "Tasks/001-beta-rollout-scope.md"
    workflow: "status_check"
```

---

## Output Schema

```yaml
output:
  summary: "Daily Briefing for Dec 30, 2024"
  trigger_type: "scheduled"
  context_period:
    start: "2024-12-29T08:30:00Z"
    end: "2024-12-30T08:30:00Z"
  
  sections:
    - agent: "workflow"
      content: |
        🎯 Focus Today:
        1. Complete review of jira-test-cases.md (due TODAY)
        2. Prepare for Open Agenda forum
    - agent: "analyzer"
      alerts:
        - type: "overdue_action"
          task: "005-jira-cleanup"
          message: "next_action_due was Dec 15"
  
  pending_actions:
    - type: "jira_comment"
      target: "MRC-3266"
      content: "Update 2024-12-30: Completed review..."
      status: "awaiting_approval"
    - type: "task_update"
      target: "001-beta-rollout-scope"
      field: "next_action"
      value: "Resolve stakeholder questions"
      status: "awaiting_approval"
```

---

## Context Period Configuration

The Orchestrator determines context period based on workflow:

```yaml
context_config:
  daily_briefing:
    period: "last_24h"
  daily_closing:
    period: "since_last_briefing"  # Dynamic: from last run timestamp
  weekly_review:
    period: "last_7d"
  status_check:
    period: "last_7d"
  ad_hoc:
    period: "configurable"  # User can specify
```

---

## State Management

The Orchestrator maintains:

1. **Execution History** — When workflows last ran
2. **Approval Patterns** — User approvals/rejections (in `Knowledge/agent-feedback.yaml`)
3. **Pending Actions** — Actions awaiting user approval

```yaml
# Example state (in memory or config)
last_runs:
  daily_briefing: "2024-12-30T08:30:00Z"
  daily_closing: "2024-12-29T17:50:00Z"
  weekly_review: "2024-12-27T16:00:00Z"
```

---

## Execution Flow

### Step 1: Receive Trigger
```
IF scheduled:
  - Check current time against schedule
  - Determine workflow type
  
IF on_demand:
  - Parse user request
  - Map to workflow type using intent matching
  
IF event:
  - Check event source
  - Determine if workflow is needed
```

### Step 2: Call Agents
```
1. Call Context Gatherer with period parameters
   → Returns: context object with Slack, Jira, Confluence, Git data

2. Call Analyzer with context
   → Returns: suggestions, alerts, task reviews

3. Call Workflow/Reflection with context + analysis
   → Returns: formatted output (briefing, closing, review)
```

### Step 3: Present to User
```
- Combine agent outputs into user-friendly format
- Group pending actions by type
- Present approval options for each action
```

### Step 4: Execute Approved Actions
```
FOR each approved action:
  IF jira_comment:
    - Call Atlassian MCP addCommentToJiraIssue
  IF jira_transition:
    - Call Atlassian MCP transitionJiraIssue
  IF task_update:
    - Update local task file
  IF archive_task:
    - Move task to Archive/YYYY-MM/
  IF slack_post:
    - Call Slack MCP conversations.postMessage
```

---

## Error Handling

### MCP Failures
```
IF Context Gatherer fails on a source:
  - Continue with available data
  - Note: "⚠️ [Source] data unavailable"
  - Do NOT block entire workflow
```

### Timeout Handling
```
IF agent takes > 30 seconds:
  - Log warning
  - Continue with partial results
  - Note: "⚠️ [Agent] timed out"
```

---

## Integration Points

| Component | Integration |
|-----------|-------------|
| **Context Gatherer** | Receives period, returns context object |
| **Analyzer** | Receives context, returns suggestions/alerts |
| **Workflow** | Receives context + analysis, returns formatted output |
| **Reflection** | Receives context + analysis, returns review |
| **GitHub Actions** | Triggers scheduled workflows |
| **logbook-local.py** | Local execution of workflows |

---

## Acceptance Criteria

- [ ] Responds to time-based triggers (9:00 AM, 5:30 PM, Friday 4 PM)
- [ ] Responds to event-based triggers (user prompts)
- [ ] Extensible to new event triggers without architecture changes
- [ ] Determines appropriate context period for each workflow
- [ ] Triggers Context Gatherer with correct period parameters
- [ ] Routes to correct specialized agent based on workflow type
- [ ] Aggregates outputs into user-facing format
- [ ] Presents approval prompts for pending actions
- [ ] Executes approved actions (Slack, Jira, files)
- [ ] Logs execution history
- [ ] Handles MCP failures gracefully

---

## Related Agents

| Agent | File | Relationship |
|-------|------|--------------|
| Context Gatherer | `context-gatherer.md` | Called first; provides data |
| Analyzer | `analyzer.md` | Called second; validates tasks |
| Workflow | `workflow.md` | Called third; generates outputs |
| Reflection | `reflection.md` | Called for weekly/quarterly reviews |

---

*See `../docs/SPEC-agent-architecture.md` for full system architecture.*

