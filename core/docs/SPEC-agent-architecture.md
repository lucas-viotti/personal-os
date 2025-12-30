# Personal OS - Solution Architecture Specification

**Version:** 1.0  
**Created:** 2024-12-30  
**Author:** Lucas Viotti  
**Status:** Draft

---

## 0. Configuration

### Configurable Parameters

These values can be adjusted by users based on their workflow patterns:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `CONTEXT_CACHE_TTL` | 25 min | How long to cache context before re-fetching. Higher = faster but potentially stale. |
| `DAILY_BRIEFING_TIME` | 09:00 | Morning workflow trigger time |
| `DAILY_CLOSING_TIME` | 17:50 | Evening workflow trigger time |
| `WEEKLY_REVIEW_DAY` | Friday | Day of week for weekly review |
| `WEEKLY_REVIEW_TIME` | 16:00 | Weekly review trigger time |

> **Note:** The 25-minute cache TTL was chosen based on personal workflow patterns. Users who receive frequent updates via Slack/Jira may want to reduce this; users who prefer less API calls can increase it.

### File Structure

```
project/
├── core/                        # Portable system engine
│   ├── agents/                  # Specialized agent instructions
│   │   ├── orchestrator.md      # Main coordinator
│   │   ├── context-gatherer.md  # MCP integration
│   │   ├── analyzer.md          # Priority/status analysis
│   │   ├── workflow.md          # Daily/weekly workflows
│   │   └── reflection.md        # Retrospectives
│   ├── docs/                    # System documentation
│   │   ├── PRD.md               # Product requirements
│   │   ├── SPEC-agent-architecture.md  # This document
│   │   ├── schema-v2-update-plan.md    # Schema migration
│   │   └── implementation-plan-v2.md   # Implementation roadmap
│   ├── templates/               # User-facing templates
│   │   ├── AGENTS.md            # AI instructions (synced with root)
│   │   └── config.yaml          # Configuration template
│   ├── mcp/                     # MCP server
│   │   └── server.py            # Tool implementations
│   └── evals/                   # Session evaluations
│
├── Tasks/                       # Active task files
├── Archive/                     # Completed tasks
├── Knowledge/                   # User knowledge only
│   ├── prioritization-rules.md  # AI prioritization criteria (user-editable)
│   ├── agent-feedback.yaml      # User approval patterns (NEW)
│   └── meetings/                # Meeting transcripts (future)
├── scripts/
│   └── logbook-local.py         # Local execution
├── .github/workflows/           # Scheduled GitHub Actions
├── AGENTS.md                    # Main agent entry point
├── GOALS.md                     # User goals
└── config.yaml                  # User configuration (NEW)
```

### Claude Code / Cursor Optimization

Agent files are designed to be self-contained so AI coding assistants can work on individual agents without loading the entire system:

1. **Each agent file declares its interfaces** — inputs, outputs, dependencies
2. **No circular dependencies** — Context → Analyzer → Workflow (one direction)
3. **Clear boundaries** — Each agent has explicit responsibilities
4. **Testable in isolation** — Agents can be validated against specific test cases

---

## 1. Architecture Overview

### Design Philosophy

Personal OS follows a **multi-agent architecture** where specialized agents handle distinct responsibilities, coordinated by an orchestrator. This approach provides:

1. **Separation of concerns** — Each agent has a focused scope
2. **Composability** — Agents can be improved or replaced independently
3. **Clarity** — Clear ownership of what each agent does
4. **Testability** — Each agent can be validated against specific acceptance criteria

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PERSONAL OS AGENT SYSTEM                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                      ORCHESTRATOR AGENT                             │ │
│  │                                                                      │ │
│  │  • Schedules agent execution (time-based triggers)                  │ │
│  │  • Routes requests to appropriate specialized agents                │ │
│  │  • Aggregates outputs for user review                               │ │
│  │  • Handles user approvals/rejections                                │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                    │                                     │
│           ┌────────────────────────┼────────────────────────┐           │
│           │                        │                        │           │
│           ▼                        ▼                        ▼           │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐     │
│  │    CONTEXT      │    │    ANALYZER     │    │    WORKFLOW     │     │
│  │    GATHERER     │    │     AGENT       │    │     AGENT       │     │
│  │     AGENT       │    │                 │    │                 │     │
│  │                 │    │ • Priority      │    │ • Daily         │     │
│  │ • Slack MCP     │───▶│   validation    │───▶│   Briefing      │     │
│  │ • Atlassian MCP │    │ • Status review │    │ • Daily Closing │     │
│  │ • Git commits   │    │ • Due date      │    │ • Weekly Review │     │
│  │ • Meeting notes │    │   verification  │    │                 │     │
│  │ • Local files   │    │ • Blocker check │    │                 │     │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘     │
│                                                                          │
│                                    │                                     │
│                                    ▼                                     │
│                         ┌─────────────────┐                             │
│                         │   REFLECTION    │                             │
│                         │     AGENT       │                             │
│                         │                 │                             │
│                         │ • Weekly goals  │                             │
│                         │ • Quarterly     │                             │
│                         │   progress      │                             │
│                         │ • Annual review │                             │
│                         │ • Initiative    │                             │
│                         │   tracking      │                             │
│                         └─────────────────┘                             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Agent Specifications

### 2.1 Orchestrator Agent

**Purpose:** Coordinate all specialized agents and manage user interactions.

**Responsibilities:**
1. **Scheduling** — Trigger agents at appropriate times
2. **Routing** — Direct requests to the right specialized agent
3. **Aggregation** — Combine agent outputs into user-facing summaries
4. **Approval Flow** — Present recommendations for user review
5. **Execution** — Execute approved actions (post to Slack, update Jira)

**Trigger Types:**

The Orchestrator responds to two types of triggers:

| Type | Description | Examples |
|------|-------------|----------|
| **Time-based** | Scheduled execution at specific times | 9:00 AM, 5:30 PM, Friday 4 PM |
| **Event-based** | Triggered by user request or system event | "Run daily briefing", file change, etc. |

**Defined Workflows:**

| Workflow | Default Trigger | Event Trigger | Context Period | Agents Called |
|----------|-----------------|---------------|----------------|---------------|
| Daily Briefing | 9:00 AM | "What should I focus on?" | Last 24h | Context → Analyzer → Workflow |
| Daily Closing | 5:30 PM | "Summarize my day" | Since last briefing | Context → Analyzer → Workflow |
| Weekly Review | Friday 4:00 PM | "Weekly review" | Last 7 days | Context → Analyzer → Reflection |
| Status Check | — | "Where are we on X?" | Last 7 days | Context → Workflow |
| Ad-hoc Analysis | — | "Check my priorities" | Configurable | Context → Analyzer |

**Extensibility:**
New event triggers can be added without modifying core architecture. The Orchestrator maintains a trigger registry that maps events to workflows.

**State Management:**
- Maintains execution history
- Tracks user approvals/rejections for learning
- Stores pending actions awaiting approval

**Interface:**

```yaml
# Orchestrator receives triggers
trigger:
  type: scheduled | on_demand | event
  
  # For scheduled triggers
  scheduled:
    time: "09:00"
    workflow: "daily_briefing"
    
  # For on-demand triggers (user request)
  on_demand:
    request: "What should I focus on today?"
    workflow: "daily_briefing"  # Orchestrator maps request to workflow
    
  # For event triggers (system events)
  event:
    source: "file_change" | "mcp_notification" | "external_webhook"
    details:
      changed_file: "Tasks/001-beta-rollout-scope.md"
    workflow: "status_check"  # Optional: auto-trigger workflow

# Orchestrator determines context period based on workflow
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

# Orchestrator returns aggregated output
output:
  summary: "Daily Briefing for Dec 30, 2024"
  trigger_type: "scheduled"
  context_period:
    start: "2024-12-29T08:30:00Z"
    end: "2024-12-30T08:30:00Z"
  sections:
    - agent: workflow
      content: "..."
    - agent: analyzer
      alerts: [...]
  pending_actions:
    - type: jira_update
      target: MRC-3266
      content: "..."
      status: awaiting_approval
```

---

### 2.2 Context Gatherer Agent

**Purpose:** Fetch and synthesize data from all sources into a unified context.

**Responsibilities:**
1. **Source Integration** — Connect to Slack, Jira, Confluence, Git, local files
2. **Data Extraction** — Pull relevant updates since last sync
3. **Synthesis** — Combine raw data into structured context
4. **Relevance Filtering** — Surface only task-relevant information

**Data Sources:**

| Source | MCP/API | Data Extracted |
|--------|---------|----------------|
| Slack | Slack MCP | Messages, threads, mentions, decisions |
| Jira | Atlassian MCP | Status changes, comments, assignee updates |
| Confluence | Atlassian MCP | Page edits, comments |
| Git | Local CLI | Commits to task files, Knowledge/ |
| Local Files | File system | Task files, Progress Logs |
| Meetings | Google Drive | Gemini transcripts (manual import) |

**Output Schema:**

```yaml
context:
  timestamp: "2024-12-30T17:50:00Z"
  period:
    type: "last_24h" | "last_7d" | "since_timestamp" | "custom"
    start: "2024-12-29T08:30:00Z"  # Set by Orchestrator
    end: "2024-12-30T17:50:00Z"
  
  sources:
    slack:
      messages_analyzed: 47
      relevant_threads:
        - thread_id: "C081E1LDD60/p1765284956532589"
          topic: "Lead Bank overlimit clause"
          key_points:
            - "Lead confirmed no 3-cycle delay"
            - "Must include in minimum payment immediately"
          related_tasks: ["004-cardholder-agreement"]
        - thread_id: "C08TR3PKC1W/p1765551881487039"
          topic: "Late Fee decision forum scheduling"
          key_points:
            - "Thiago requested postponement due to holidays"
            - "New date likely mid-January"
          related_tasks: ["009-late-fee-penalty-apr-decision"]
        - thread_id: "C07EPTTAJJH/p1748463085869849"
          topic: "Collections policy handover"
          key_points:
            - "Jennifer completed FDCPA draft"
            - "Ownership transferred to Compliance"
          related_tasks: ["002-collections-loan-servicing-split"]
          
    jira:
      issues_updated:
        - key: MRC-3266
          summary: "Beta Rollout Scope Document"
          changes:
            - field: status
              from: "In Progress"
              to: "In Review"
            - field: comment
              content: "Draft sent to Legal"
          related_tasks: ["001-beta-rollout-scope"]
        - key: MRC-1911
          summary: "Loan Servicing Policy"
          changes:
            - field: status
              from: "In Progress"
              to: "Done"
          related_tasks: ["002-collections-loan-servicing-split"]
        - key: MRC-1912
          summary: "Cardholder Agreement"
          changes:
            - field: comment
              content: "Awaiting Lead Bank response on overlimit clause"
          related_tasks: ["004-cardholder-agreement"]
          
    confluence:
      pages_edited:
        - page_id: "264465777127"
          title: "Milestones & Rollout Stages"
          edit_summary: "Updated beta timeline"
          related_tasks: ["001-beta-rollout-scope"]
        - page_id: "264284242783"
          title: "CC Policies Database"
          edit_summary: "Added Loan Servicing Policy link"
          related_tasks: ["002-collections-loan-servicing-split"]
          
    git:
      commits:
        - hash: "abc123"
          timestamp: "2024-12-30T14:30:00Z"
          message: "Update progress on cardholder agreement"
          files: ["Tasks/004-cardholder-agreement-followup.md"]
        - hash: "def456"
          timestamp: "2024-12-30T16:00:00Z"
          message: "Complete collections policy split task"
          files: ["Tasks/002-collections-loan-servicing-split.md"]
          
    local_tasks:
      - file: "Tasks/001-beta-rollout-scope-document.md"
        title: "Finish Troy's CC Beta rollout scope document"
        next_action: "Complete review of jira-test-cases.md"
        next_action_due: "2025-12-30"
        status: "s"
        priority: "P0"
      - file: "Tasks/004-cardholder-agreement-followup.md"
        title: "Review and Finalize Cardholder Agreement V2"
        status: "b"
        blocked_by: "Lead Bank - overlimit clause response"
        blocked_expected: "2026-01-10"
        priority: "P1"
      - file: "Tasks/009-late-fee-penalty-apr-decision.md"
        title: "Late Fee & Penalty APR Decisions"
        next_action: "Attend decision forum when scheduled"
        status: "s"
        priority: "P0"
        
    # Future: Meeting transcripts (manual import for now)
    meetings:  # Optional - populated when transcripts imported to Knowledge/
      - file: "Knowledge/meetings/2024-12-30-beta-alignment.md"
        date: "2024-12-30"
        title: "Beta Rollout Alignment"
        participants: ["Lucas", "Thiago", "Jennifer"]
        key_decisions:
          - "Jan 9 deadline confirmed for leadership draft"
          - "Defer late fee forum to mid-January"
        action_items:
          - assignee: "Lucas"
            action: "Complete stakeholder matrix"
            due: "2025-01-06"
        related_tasks: ["001-beta-rollout-scope", "009-late-fee-penalty"]
```

**Pre-processing Rules:**
1. Filter noise (bot messages, automated notifications)
2. Group by task/initiative when possible
3. Extract key decisions and action items
4. Identify blockers mentioned
5. Flag deadline changes

---

### 2.3 Analyzer Agent

**Purpose:** Validate task metadata against latest context and suggest corrections.

**Responsibilities:**
1. **Priority Validation** — Check if P0-P3 still makes sense
2. **Status Review** — Verify blocked/started/not-started is accurate
3. **Due Date Verification** — Check for implicit deadline changes
4. **Blocker Detection** — Identify resolved or new blockers
5. **Consistency Check** — Ensure `next_action` matches reality

**Analysis Checks:**

| Check | Input | Logic | Output |
|-------|-------|-------|--------|
| Priority drift | Context + Task | If high activity on P2 task, suggest promoting | `suggest_priority_change: P2 → P1` |
| Stale blocker | Context + blocked_expected | If blocker discussed as resolved in Slack | `suggest_status_change: b → s` |
| Missed deadline | Context + next_action_due | If date passed without completion | `alert: overdue_action` |
| Implicit date change | Context (Slack/Jira) | If discussion mentions new date | `suggest_due_date_change` |
| Completed action | Context + next_action | If action discussed as done | `suggest_next_action_update` |

**Output Schema:**

```yaml
analysis:
  timestamp: "2024-12-30T17:52:00Z"
  
  task_reviews:
    - task: "004-cardholder-agreement-followup"
      current:
        status: b
        blocked_by: "Lead Bank - overlimit clause"
        blocked_expected: "2026-01-10"
      findings:
        - type: blocker_resolved
          evidence: "Slack thread C081E1LDD60 - Lead confirmed resolution Dec 16"
          confidence: high
      suggestions:
        - action: update_status
          from: b
          to: s
          reason: "Blocker resolved per Slack discussion"
        - action: set_next_action
          value: "Update agreement with Lead Bank decision"
          due: "2025-12-31"
          
    - task: "001-beta-rollout-scope-document"
      current:
        status: s
        next_action: "Complete review of jira-test-cases.md"
        next_action_due: "2025-12-30"
      findings:
        - type: action_due_today
          severity: high
      suggestions: []  # No changes needed, just surface as focus
      
  alerts:
    - type: overdue_action
      task: "005-jira-cleanup"
      message: "next_action_due was Dec 15, no update since"
      severity: medium
      
  no_issues:
    - task: "012-ccf-product-team-prioritization"
      reason: "No relevant context found; metadata appears current"
```

**Confidence Levels:**
- **High** — Direct evidence (explicit Slack message, Jira status change)
- **Medium** — Inferred (discussion suggests completion, but not explicit)
- **Low** — Speculative (related topic discussed, unclear if applies)

Only suggestions with **high confidence** are auto-recommended; medium/low require user validation.

---

### 2.4 Workflow Agent

**Purpose:** Generate daily operational outputs for user review.

**Responsibilities:**
1. **Daily Briefing** — Morning focus recommendations
2. **Daily Closing** — End-of-day summary and Jira sync suggestions
3. **On-demand Status** — Answer "where are we on X?"

**Daily Briefing Logic:**

```
INPUT: Analyzer output + Local tasks

1. Filter tasks where status != 'b' (exclude blocked)
2. Sort by next_action_due ASC (earliest first)
3. Take top 3 as "Focus Today"
4. Group remaining by priority (P0, P1, P2, P3)
5. Summarize blocked tasks with follow-up dates
6. Include any Analyzer alerts (overdue, etc.)

OUTPUT: Structured briefing for Slack
```

**Daily Closing Logic:**

```
INPUT: Context (full day) + Analyzer output + Local tasks

1. Compare morning state to current state
2. Identify: what changed in tasks? what was delivered?
3. For each task with local progress:
   - Check if linked Jira is stale
   - If yes, generate Jira update suggestion
4. Summarize day's accomplishments
5. Flag incomplete focus items
6. Suggest next_action updates

OUTPUT: Closing summary + pending Jira updates for approval
```

**Status Check Logic ("Where are we on X?"):**

```
INPUT: User query (e.g., "Where are we on Troy Beta?") + Context (last 7 days)

1. Identify target task(s) by name/keyword match
2. Read task file's ## Progress Log (last 3-5 entries)
3. Fetch linked Jira card status + recent comments
4. Fetch recent Slack threads mentioning the initiative
5. Synthesize into concise status summary

OUTPUT: 
- Current status (started/blocked/etc.)
- Next action and due date
- Last 3 progress updates with dates
- Any blockers and follow-up dates
- Links to evidence (Jira, Slack threads)

VALIDATION: User can respond accurately within 30 seconds of reading
```

**Output Schema:**

```yaml
# Daily Briefing
briefing:
  date: "2024-12-30"
  focus_today:
    - task: "001-beta-rollout-scope-document"
      next_action: "Complete review of jira-test-cases.md"
      due: "2024-12-30"
      reason: "Due today; critical for Jan 9 milestone"
    - task: "009-late-fee-penalty-apr-decision"
      next_action: "Prepare for Open Agenda forum"
      due: "2025-01-08"
      reason: "P0; requires prep before forum"
      
  tracking_blocked:
    - task: "004-cardholder-agreement-followup"
      blocked_by: "Lead Bank review"
      follow_up: "2026-01-10"
      
  alerts:
    - "005-jira-cleanup: overdue since Dec 15"

# Daily Closing
closing:
  date: "2024-12-30"
  accomplished:
    - task: "001-beta-rollout-scope"
      action: "Completed jira-test-cases review"
      evidence: "Local file updated + Jira MRC-3266 comment"
      
  pending_jira_updates:
    - jira_key: MRC-3266
      jira_title: "Beta Rollout Scope Document"
      jira_url: "https://nubank.atlassian.net/browse/MRC-3266"
      updates:
        - type: comment
          content: |
            Update 2024-12-30: Completed review of jira-test-cases.md. 
            10 BA Initiatives, 148 stories validated.
            Next: Resolve open questions with stakeholders by Jan 6.
          status: awaiting_approval
        - type: due_date
          from: "2025-01-09"
          to: "2025-01-16"
          reason: "Slack discussion on Dec 28 moved timeline"
          status: awaiting_approval
        - type: transition
          from: "In Progress"
          to: "In Review"
          status: awaiting_approval
      
  incomplete_focus:
    - task: "009-late-fee-penalty-apr-decision"
      planned: "Prepare for Open Agenda forum"
      note: "No activity detected today"
      
  suggested_updates:
    - task: "001-beta-rollout-scope"
      field: next_action
      from: "Complete review of jira-test-cases.md"
      to: "Resolve open questions with stakeholders"
      new_due: "2026-01-06"
      
  # NEW: Archive prompts for completed tasks
  completed_tasks:
    - task: "004-cardholder-agreement-followup"
      title: "Review and Finalize Cardholder Agreement V2"
      completed_evidence:
        - "Jira MRC-1912 transitioned to Done"
        - "Slack thread: 'Cardholder Agreement signed off'"
      archive_prompt:
        status: awaiting_approval
        destination: "Archive/2024-12/"
```

---

### 2.5 Reflection Agent

**Purpose:** Provide periodic reflection on progress toward goals.

**Responsibilities:**
1. **Weekly Review** — What delivered vs. planned
2. **Goal Progress** — Track quarterly/annual objectives
3. **Initiative Health** — Status of each major initiative
4. **Performance Evidence** — Compile achievements for reviews

**Time Horizons:**

| Horizon | Trigger | Focus |
|---------|---------|-------|
| Weekly | Friday 4 PM | Delivered this week, plan next week |
| Monthly | 1st of month | Initiative progress, blockers |
| Quarterly | End of Q | OKR progress, adjustments |
| Annual | Dec | Performance review evidence |

**Weekly Review Logic:**

```
INPUT: 
- Context (last 7 days)
- Archived tasks (completed this week)
- Active tasks (status changes, progress)
- GOALS.md (objectives to track)

1. List completed tasks with evidence
2. Calculate: planned vs. actual delivery
3. Identify recurring blockers
4. Check progress against quarterly goals
5. Suggest focus areas for next week

OUTPUT: Weekly summary for user + manager sharing
```

**Output Schema:**

```yaml
weekly_review:
  week: "Dec 23-30, 2024"
  
  delivered:
    - task: "002-collections-loan-servicing-split"
      completed: "2024-12-29"
      evidence:
        - "Confluence pages updated"
        - "MRC-1911 marked done"
      goal_alignment: "Policies and procedures for Troy"
      
  in_progress:
    - task: "001-beta-rollout-scope-document"
      planned_completion: "2026-01-16"
      this_week: "Completed jira-test-cases review"
      next_week: "Stakeholder alignment"
      
  blocked:
    - task: "004-cardholder-agreement-followup"
      blocked_since: "2024-12-11"
      blocked_by: "Lead Bank"
      follow_up: "2026-01-10"
      
  goal_progress:
    - goal: "Prepare beta rollout launch for the US"
      status: "On track"
      key_milestones:
        - "Jan 9: Draft ready for leadership"
        - "Jan 16: Final version"
      this_week_contribution: "Completed jira scope review"
      
  metrics:
    tasks_completed: 3
    tasks_started: 2
    tasks_blocked: 2
    avg_time_in_progress: "8 days"
    
  next_week_focus:
    - "Resolve stakeholder questions for beta scope"
    - "Follow up on Lead Bank (Jan 10)"
    - "Prepare for Late Fee decision forum"
```

---

## 3. Data Flow

### 3.1 Daily Briefing Flow (9:00 AM)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Orchestrator │────▶│   Context    │────▶│   Analyzer   │────▶│   Workflow   │
│              │     │   Gatherer   │     │              │     │              │
│ Trigger:     │     │              │     │              │     │              │
│ 9:00 AM      │     │ Fetch:       │     │ Check:       │     │ Generate:    │
│              │     │ - Slack 24h  │     │ - Priorities │     │ - Focus list │
│              │     │ - Jira 24h   │     │ - Blockers   │     │ - Alerts     │
│              │     │ - Tasks      │     │ - Due dates  │     │ - Tracking   │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                      │
                                                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              USER REVIEW                                      │
│                                                                               │
│  📋 Daily Briefing - Dec 30, 2024                                            │
│                                                                               │
│  🎯 Focus Today:                                                             │
│  1. Complete review of jira-test-cases.md (due TODAY)                        │
│  2. Prepare for Open Agenda forum                                            │
│                                                                               │
│  ⏳ Tracking (Blocked):                                                       │
│  • Cardholder Agreement - waiting on Lead Bank (follow up Jan 10)            │
│                                                                               │
│  ⚠️ Alerts:                                                                   │
│  • Jira cleanup overdue since Dec 15                                         │
│                                                                               │
│  [✓ Looks good] [Edit suggestions] [Snooze alerts]                          │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Daily Closing Flow (5:30 PM)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Orchestrator │────▶│   Context    │────▶│   Analyzer   │────▶│   Workflow   │
│              │     │   Gatherer   │     │              │     │              │
│ Trigger:     │     │              │     │              │     │              │
│ 5:30 PM      │     │ Fetch:       │     │ Compare:     │     │ Generate:    │
│              │     │ - Full day   │     │ - Morning    │     │ - Summary    │
│              │     │   context    │     │   vs. now    │     │ - Jira sync  │
│              │     │ - Git diffs  │     │ - Stale Jira │     │ - Next steps │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                      │
                                                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              USER REVIEW                                      │
│                                                                               │
│  🌆 Daily Closing - Dec 30, 2024                                             │
│                                                                               │
│  ✅ Accomplished:                                                             │
│  • Completed jira-test-cases review (Task 001)                               │
│                                                                               │
│  📝 Suggested Jira Updates:                                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ MRC-3266: "Completed review of jira-test-cases.md. 10 BA Initiatives,  │  │
│  │ 148 stories validated. Next: Resolve open questions by Jan 6."         │  │
│  │                                                                         │  │
│  │ [✓ Approve & Post] [Edit] [Skip]                                       │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
│  📌 Suggested Task Updates:                                                  │
│  • Task 001: Update next_action to "Resolve open questions" (due Jan 6)     │
│    [✓ Apply] [Edit] [Skip]                                                  │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Weekly Review Flow (Friday 4:00 PM)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Orchestrator │────▶│   Context    │────▶│   Analyzer   │────▶│  Reflection  │
│              │     │   Gatherer   │     │              │     │              │
│ Trigger:     │     │              │     │              │     │              │
│ Fri 4 PM     │     │ Fetch:       │     │ Analyze:     │     │ Generate:    │
│              │     │ - Week data  │     │ - Goal prog  │     │ - Delivered  │
│              │     │ - Archives   │     │ - Patterns   │     │ - Progress   │
│              │     │ - GOALS.md   │     │ - Health     │     │ - Next week  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                      │
                                                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              USER REVIEW                                      │
│                                                                               │
│  📊 Weekly Review - Dec 23-30, 2024                                          │
│                                                                               │
│  ✅ Delivered This Week:                                                      │
│  • Collections/Loan Servicing policy split (completed Dec 29)                │
│  • Jira-test-cases review for Beta scope                                     │
│                                                                               │
│  📈 Goal Progress: "Prepare beta rollout launch"                             │
│  Status: On track | Next milestone: Jan 9 (draft for leadership)             │
│                                                                               │
│  ⏳ Blocked > 7 Days:                                                         │
│  • Cardholder Agreement (19 days) - Lead Bank review                         │
│                                                                               │
│  🎯 Suggested Focus Next Week:                                                │
│  1. Resolve stakeholder questions (Beta scope)                               │
│  2. Follow up Lead Bank (Jan 10)                                             │
│  3. Prepare Late Fee decision forum                                          │
│                                                                               │
│  [✓ Share with Manager] [Edit] [Save Draft]                                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

### 3.4 Output Action Types

When user approves recommendations, the Orchestrator executes these action types:

| Action Type | Description | Execution Method |
|-------------|-------------|------------------|
| `slack_post` | Post message to Slack channel | Slack MCP `conversations.postMessage` |
| `jira_comment` | Add comment to Jira issue | Atlassian MCP `addCommentToJiraIssue` |
| `jira_description` | Update Jira issue description | Atlassian MCP `editJiraIssue` (fields.description) |
| `jira_due_date` | Change Jira issue due date | Atlassian MCP `editJiraIssue` (fields.duedate) |
| `jira_transition` | Change Jira issue status | Atlassian MCP `transitionJiraIssue` |
| `jira_fields` | Update other Jira fields (priority, labels, etc.) | Atlassian MCP `editJiraIssue` |
| `task_update` | Update local task file frontmatter | Direct file edit |
| `archive_task` | Move completed task to Archive/ | File move + add `completed_date` |

**Jira Sync Flow (Detail):**

**Comment Format Standard:**
```
Update YYYY-MM-DD: [summary of progress or change]
```

Example:
```
Update 2024-12-30: Completed review of jira-test-cases.md. 10 BA Initiatives, 
148 stories validated. Next: Resolve open questions with stakeholders by Jan 6.
```

**Supported Jira Update Types:**

| Update Type | When to Suggest | Example |
|-------------|-----------------|---------|
| **Comment** | Progress made, decision logged | "Update 2024-12-30: Completed stakeholder review" |
| **Description** | Scope clarified, requirements changed | Append section to description |
| **Due Date** | Deadline moved based on discussion | Change from Jan 9 → Jan 16 |
| **Status Transition** | Work completed or blocked | Move to "In Review" or "Done" |
| **Priority/Labels** | Context suggests urgency change | Add "blocked" label |

**User Preview (Multiple Updates Possible):**
```
┌─────────────────────────────────────────────────────────────────┐
│ 📝 Suggested Jira Updates                                       │
│                                                                  │
│ Card: [MRC-3266: Beta Rollout Scope Document](hyperlink)        │
│                                                                  │
│ 1. Add Comment:                                                  │
│    "Update 2024-12-30: Completed review of jira-test-cases.md.  │
│    10 BA Initiatives, 148 stories validated.                    │
│    Next: Resolve open questions with stakeholders by Jan 6."    │
│    [✓ Post]  [Edit]  [Skip]                                     │
│                                                                  │
│ 2. Update Due Date:                                              │
│    From: 2025-01-09 → To: 2025-01-16                            │
│    Reason: Slack discussion on Dec 28 moved timeline            │
│    [✓ Update]  [Skip]                                           │
│                                                                  │
│ 3. Transition Status:                                            │
│    From: "In Progress" → To: "In Review"                        │
│    [✓ Transition]  [Skip]                                       │
└─────────────────────────────────────────────────────────────────┘
```

**Execution Flow:**
```
1. Daily Closing detects: local progress > Jira status
2. Generates suggested updates (comment, due date, status, etc.)
3. User reviews each update type with hyperlinked card name
4. On approval:
   - Comment: addCommentToJiraIssue(issueIdOrKey, commentBody)
   - Due Date: editJiraIssue(issueIdOrKey, {fields: {duedate: "YYYY-MM-DD"}})
   - Description: editJiraIssue(issueIdOrKey, {fields: {description: updatedDesc}})
   - Status: transitionJiraIssue(issueIdOrKey, transitionId)
5. Show confirmation per update: "✓ Comment posted" / "✓ Due date updated"
6. Offer 30-second undo where applicable
7. Fallback if MCP fails: Copy to clipboard with manual instructions
8. Log all executions in task's Progress Log
```

**Archive Flow:** (Existing Implementation - `examples/workflows/archive-tasks.md`)

**Two Trigger Modes:**

| Mode | Trigger | Use Case |
|------|---------|----------|
| **Batch** | User says "archive my completed tasks" | Weekly cleanup, bulk archival |
| **Single** | Agent detects task completion | Immediate archival on task done |

**Batch Archive Flow:**
```
Trigger: User says "archive my completed tasks" or "archive done tasks"

1. Scan Tasks/ for files with status: d
2. For each completed task:
   - Add completed_date: YYYY-MM-DD if not present
   - Move to Archive/YYYY-MM/ based on completion date
   - Keep original filename
3. Present summary: "✅ Moved N tasks to Archive/YYYY-MM/"
4. Confirm cleanup complete
```

**Single Archive Flow (Agent-Prompted):**
```
Trigger: Daily Closing detects task marked as done (status: d)

1. Agent identifies completed task(s) in Daily Closing summary
2. Prompt user:
   ┌─────────────────────────────────────────────────────────────────┐
   │ 🎉 Task Completed!                                               │
   │                                                                  │
   │ "Review and Finalize Cardholder Agreement V2" is marked done.   │
   │                                                                  │
   │ Would you like to archive it now?                               │
   │                                                                  │
   │ [✓ Archive Now]  [Archive Later]                                │
   └─────────────────────────────────────────────────────────────────┘
3. On "Archive Now":
   - Add completed_date: YYYY-MM-DD
   - Move file to Archive/YYYY-MM/
   - Confirm: "✓ Archived to Archive/2024-12/"
4. On "Archive Later":
   - Task remains in Tasks/ with status: d
   - Will be picked up in next batch archive
```

**Archive Structure:**
```
Archive/
├── 2025-01/
│   └── completed-task-1.md
├── 2025-02/
│   └── completed-task-2.md
```

**Integration with Agents:**
- **Workflow Agent (Daily Closing):** Detects completion, prompts for immediate archival
- **Reflection Agent (Weekly Review):** Reads Archive/ to compile "Delivered This Week" section
- **User:** Triggers batch archive manually (prompt) OR accepts single archive prompt

---

## 4. Implementation Approach

### 4.1 Agent Implementation Options

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| **A: Single LLM + Prompts** | One LLM call with role-specific prompts | Simple, fast | Context limits, less control |
| **B: Multi-Prompt Pipeline** | Sequential LLM calls per agent | Clear separation | More API calls, latency |
| **C: Hybrid** | Context Gatherer as code; others as LLM | Best of both | More complexity |

**Recommended: Option C (Hybrid)**

- **Context Gatherer**: Code-based (MCPs + file parsing) — deterministic, fast
- **Analyzer**: LLM-based — needs reasoning about priorities
- **Workflow/Reflection**: LLM-based — needs natural language generation

### 4.2 File Structure

```
personal-os/
├── core/
│   ├── agents/               # Specialized agent instructions
│   │   ├── orchestrator.md       # Orchestrator instructions
│   │   ├── context-gatherer.md   # Context Gatherer instructions
│   │   ├── analyzer.md           # Analyzer instructions
│   │   ├── workflow.md           # Workflow Agent instructions
│   │   └── reflection.md         # Reflection Agent instructions
│   ├── docs/                 # System documentation (PRD, SPEC, etc.)
│   └── mcp/                  # MCP server
├── AGENTS.md                 # Main entry point (calls orchestrator)
├── scripts/
│   └── logbook-local.py      # Execution engine
└── .github/workflows/
    ├── daily-briefing.yml    # 9:00 AM trigger
    ├── daily-closing.yml     # 5:30 PM trigger
    └── weekly-review.yml     # Friday 4 PM trigger
```

### 4.3 Agent Instruction Files

Each agent has a dedicated instruction file that:
1. Defines its purpose and responsibilities
2. Specifies input/output schemas
3. Contains the LLM prompt template
4. Lists acceptance criteria for validation

Example: `agents/analyzer.md`

```markdown
# Analyzer Agent

## Purpose
Validate task metadata against latest context and suggest corrections.

## Inputs
- Context from Context Gatherer Agent
- Current task files from Tasks/

## Outputs
- List of suggested task updates
- Alerts for attention items
- Confidence levels for each suggestion

## Prompt Template
[LLM prompt goes here]

## Acceptance Criteria
- [ ] Identifies blocker resolved when mentioned in Slack
- [ ] Flags overdue next_action_due
- [ ] Suggests priority change when activity pattern changes
```

---

## 5. Acceptance Criteria by Agent

### Orchestrator Agent

- [ ] Responds to time-based triggers (scheduled workflows at 9:00 AM, 5:30 PM, Friday 4 PM)
- [ ] Responds to event-based triggers (user request via prompt)
- [ ] Extensible to new event triggers without architecture changes
- [ ] Determines appropriate context period for each workflow
- [ ] Triggers Context Gatherer with correct period parameters
- [ ] Routes to correct specialized agent based on trigger/workflow type
- [ ] Aggregates outputs into user-facing format
- [ ] Presents approval prompts for pending actions
- [ ] Executes approved actions (post to Slack, update files)
- [ ] Logs execution history

### Context Gatherer Agent

- [ ] Accepts period parameters from Orchestrator (start/end timestamps)
- [ ] Fetches Slack messages within specified period
- [ ] Fetches Jira updates within specified period
- [ ] Fetches Confluence edits within specified period
- [ ] Reads Git commits to task/knowledge files
- [ ] Parses local task files for current state
- [ ] Parses meeting transcripts from Knowledge/meetings/ (if present)
- [ ] Filters noise (bot messages, automated notifications)
- [ ] Returns arrays of items per source (multiple threads, multiple Jira issues, etc.)
- [ ] Links context to specific tasks when possible
- [ ] Output matches defined schema

### Analyzer Agent

- [ ] Compares task metadata to context
- [ ] Identifies resolved blockers from Slack/Jira evidence
- [ ] Flags overdue `next_action_due` items
- [ ] Suggests `next_action` updates when action completed
- [ ] Assigns confidence levels to suggestions
- [ ] Only auto-recommends high-confidence suggestions

### Workflow Agent

- [ ] Generates Daily Briefing with focus items sorted by due date
- [ ] Excludes blocked tasks from focus recommendations
- [ ] Generates Daily Closing with accomplishments summary
- [ ] Suggests Jira updates when local progress exists but Jira is stale
- [ ] Suggests task file updates based on day's activity

### Reflection Agent

- [ ] Generates Weekly Review with delivered items
- [ ] Calculates planned vs. actual delivery
- [ ] Shows progress toward GOALS.md objectives
- [ ] Identifies tasks blocked > 7 days
- [ ] Suggests focus areas for next week
- [ ] Format is stakeholder-shareable

---

## 6. Open Questions - Analysis

### Q1: Where should agent instructions live?

| Option | Description |
|--------|-------------|
| **(A) Separate `agents/*.md` files** | Each agent has its own instruction file |
| **(B) Embedded in main `AGENTS.md`** | All agent logic in one file |

| Option | Pros | Cons |
|--------|------|------|
| **(A) Separate files** | • Clear separation of concerns | • More files to manage |
| | • Can version/update agents independently | • Need to coordinate changes across files |
| | • Easier to test individual agents | • Potential for drift between agents |
| | • Cleaner git history per agent | |
| **(B) Embedded** | • Single source of truth | • File becomes very long |
| | • Easier to see full system | • Harder to update individual agents |
| | • No coordination needed | • Harder to test in isolation |

**Recommendation: (A) Separate files** ✅ DECIDED

Rationale: As the system grows, maintaining 5+ agents in one file becomes unwieldy. Separate files allow you to iterate on one agent (e.g., improve Analyzer) without touching others. The Orchestrator file can import/reference other agents.

**Implementation:** Agent files will live in `agents/` directory, optimized for usage with AI coding assistants like Cursor and Claude Code:

```
agents/
├── orchestrator.md      # Main coordinator
├── context-gatherer.md  # MCP integration for Slack/Jira/Confluence
├── analyzer.md          # Priority/status/due date analysis
├── workflow.md          # Daily briefing/closing/weekly review
└── reflection.md        # Weekly/monthly retrospectives
```

Each agent file will be self-contained with clear interfaces, allowing Claude Code or Cursor to work on individual agents without loading the entire system context.

---

### Q2: How to handle MCP failures?

| Option | Description |
|--------|-------------|
| **(A) Graceful degradation** | Continue with available data; note what's missing |
| **(B) Abort and alert** | Stop execution; notify user of failure |

| Option | Pros | Cons |
|--------|------|------|
| **(A) Graceful degradation** | • System stays useful even if Slack is down | • May give incomplete picture |
| | • User still gets partial value | • Could miss critical context |
| | • Resilient to transient failures | • Harder to debug what went wrong |
| **(B) Abort and alert** | • Clear failure mode | • System becomes brittle |
| | • User knows exactly what failed | • One failing source blocks everything |
| | • Easier to debug | • Reduces system utility |

**Recommendation: (A) Graceful degradation with visibility** ✅ DECIDED

Rationale: MCP failures (especially Slack) will happen. The system should continue with available data but clearly indicate what's missing:

```yaml
context:
  sources:
    slack:
      status: "failed"
      error: "MCP timeout after 30s"
      data: null
    jira:
      status: "success"
      data: [...]
```

User sees: "⚠️ Slack data unavailable — recommendations based on Jira + local files only"

---

### Q3: Should Analyzer run independently?

| Option | Description |
|--------|-------------|
| **(A) Always with Context Gatherer** | Analyzer only runs after fresh context is fetched |
| **(B) On-demand independently** | Analyzer can run against cached/existing context |

| Option | Pros | Cons |
|--------|------|------|
| **(A) Always coupled** | • Always has fresh data | • Slower (must fetch first) |
| | • No stale analysis | • More API calls |
| | • Simpler mental model | • Can't quickly re-analyze |
| **(B) On-demand** | • Faster for quick checks | • May analyze stale context |
| | • Can run "what if" scenarios | • More complex state management |
| | • Reduces API load | • User might not realize data is old |

**Recommendation: (A) Always with Context, with caching** ✅ DECIDED

Rationale: Analysis on stale data is misleading. However, we can add a short cache so rapid re-runs don't re-fetch everything:

```
If context_age < CONTEXT_CACHE_TTL:
  Use cached context
Else:
  Run Context Gatherer first
```

**Configuration:**
```yaml
# In config.yaml or .env
CONTEXT_CACHE_TTL: 25  # minutes (configurable by user)
```

> **Note:** Default value of 25 minutes was chosen based on personal workflow patterns. Users can adjust this value based on how frequently their external sources update and their tolerance for slightly stale data.

This gives freshness guarantees while avoiding unnecessary API calls.

---

### Q4: How to track user approval patterns?

| Option | Description |
|--------|-------------|
| **(A) Track in local file** | Store approval/rejection history in `Knowledge/agent-feedback.md` |
| **(B) Don't track** | No learning from user behavior |

| Option | Pros | Cons |
|--------|------|------|
| **(A) Track locally** | • Can learn user preferences | • Privacy considerations |
| | • Improve suggestions over time | • Adds storage complexity |
| | • Useful for debugging | • Need to decide what to track |
| | • Evidence for system tuning | |
| **(B) Don't track** | • Simpler implementation | • Can't improve over time |
| | • No privacy concerns | • Repeat same mistakes |
| | • Less state to manage | • No insight into system quality |

**Recommendation: (A) Track locally, minimal data** ✅ DECIDED

Rationale: Understanding why users reject suggestions is valuable for improving the system. Track minimally:

```yaml
# Knowledge/agent-feedback.yaml
feedback:
  - date: "2024-12-30"
    workflow: "daily_closing"
    suggestion_type: "jira_update"
    action: "rejected"
    reason: null  # Optional: user can add reason
  - date: "2024-12-30"
    workflow: "daily_closing"
    suggestion_type: "task_update"
    action: "approved"
```

This helps identify patterns (e.g., "user always rejects Jira sync suggestions for P3 tasks") without storing sensitive content.

---

## 6.1 Decisions Summary

### Architecture Decisions

| Question | Decision | Notes |
|----------|----------|-------|
| Where do agents live? | ✅ **(A) Separate `agents/*.md` files** | Optimized for Claude Code/Cursor |
| How to handle MCP failures? | ✅ **(A) Graceful degradation with visibility** | Continue with available data |
| Should Analyzer run independently? | ✅ **(A) Always with Context + cache** | 25-min TTL (configurable) |
| Track user approval patterns? | ✅ **(A) Track locally, minimal data** | For pattern identification |

### Product Decisions

| Question | Decision | Notes |
|----------|----------|-------|
| Jira auto-execute on approval? | ✅ **(B) Auto-update** | With hyperlink safeguard + (A) copy as fallback |
| Meeting transcripts? | ✅ **(A) Manual download** | Phase 2; path to auto-import in Phase 3 |
| Google Docs/Slides? | ✅ **(A) Out of scope** | Manual `resource_refs`; revisit when Google MCP matures |
| Archive trigger mode? | ✅ **Both batch + single** | User-triggered batch OR agent-prompted on completion |

> All decisions resolved on 2024-12-30.

---

## 7. Next Steps

1. **Validate architecture** — Review with user; adjust agent responsibilities if needed
2. **Define agent prompts** — Create detailed LLM prompts for each agent
3. **Implement Context Gatherer** — Code-based; most deterministic
4. **Implement Analyzer** — LLM-based; validate suggestions
5. **Implement Workflow Agent** — Daily Briefing/Closing
6. **Implement Reflection Agent** — Weekly Review
7. **Implement Orchestrator** — Tie everything together
8. **Integration testing** — End-to-end workflow validation

---

*Last updated: 2024-12-30*  
*Next review: After agent prompts defined*

