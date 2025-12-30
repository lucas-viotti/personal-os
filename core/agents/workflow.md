# Workflow Agent

**Purpose:** Generate daily operational outputs for user review.

**Version:** 1.0  
**Last Updated:** 2024-12-30

---

## Overview

The Workflow Agent is an **LLM-based agent** that produces the daily briefing, daily closing, and on-demand status checks. It transforms context and analysis into user-friendly, actionable outputs.

---

## Responsibilities

| Responsibility | Description |
|----------------|-------------|
| **Daily Briefing** | Morning focus recommendations (max 3 items) |
| **Daily Closing** | End-of-day summary + Jira sync suggestions |
| **Status Check** | Answer "Where are we on X?" questions |

---

## Workflows

### 1. Daily Briefing

**Trigger:** 8:30 AM or "What should I focus on?"

**Logic:**
```
INPUT: Analyzer output + Local tasks + prioritization_rules

1. Filter tasks where status != 'b' (exclude blocked)
2. Identify actions due today (next_action_due == today)
3. Sort remaining by next_action_due ASC (earliest first)
4. Take top 2-3 as "Focus Today"
5. Group remaining by priority (P0, P1)
6. List blocked tasks with follow-up dates (Tracking section)
7. Include any Analyzer alerts (overdue, etc.)

OUTPUT: Structured briefing for Slack
```

**Output Schema:**
```yaml
briefing:
  date: "2024-12-30"
  
  focus_today:
    - task: "001-beta-rollout-scope-document"
      title: "Finish Troy's CC Beta rollout scope document"
      next_action: "Complete review of jira-test-cases.md"
      due: "2024-12-30"
      reason: "Due today; critical for Jan 9 milestone"
    - task: "009-late-fee-penalty-apr-decision"
      title: "Late Fee & Penalty APR Decisions"
      next_action: "Prepare for Open Agenda forum"
      due: "2025-01-08"
      reason: "P0; requires prep before forum"
      
  p0_tasks:  # Remaining P0 tasks (not in focus)
    - title: "Task X"
      status: "s"
      next_action_due: "2025-01-05"
      
  p1_tasks:  # P1 tasks for visibility
    - title: "Task Y"
      status: "s"
      next_action_due: "2025-01-10"
      
  tracking_blocked:
    - task: "004-cardholder-agreement-followup"
      title: "Review and Finalize Cardholder Agreement V2"
      blocked_by: "Lead Bank review"
      follow_up: "2026-01-10"
      
  alerts:
    - type: "overdue_action"
      message: "005-jira-cleanup: overdue since Dec 15"
```

---

### 2. Daily Closing

**Trigger:** 5:50 PM or "Summarize my day"

**Logic:**
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
7. Check for tasks that should be archived

OUTPUT: Closing summary + pending Jira updates for approval
```

**Output Schema:**
```yaml
closing:
  date: "2024-12-30"
  
  accomplished:
    - task: "001-beta-rollout-scope"
      title: "Finish Troy's CC Beta rollout scope document"
      action: "Completed jira-test-cases review"
      evidence:
        - "Local file updated"
        - "Jira MRC-3266 comment"
      
  pending_jira_updates:
    - jira_key: "MRC-3266"
      jira_title: "Beta Rollout Scope Document"
      jira_url: "https://domain.atlassian.net/browse/MRC-3266"
      updates:
        - type: "comment"
          content: |
            Update 2024-12-30: Completed review of jira-test-cases.md. 
            10 BA Initiatives, 148 stories validated.
            Next: Resolve open questions with stakeholders by Jan 6.
          status: "awaiting_approval"
        - type: "due_date"
          from: "2025-01-09"
          to: "2025-01-16"
          reason: "Slack discussion moved timeline"
          status: "awaiting_approval"
        - type: "transition"
          from: "In Progress"
          to: "In Review"
          status: "awaiting_approval"
        - type: "description"
          changes: "Added test case validation results section"
          status: "awaiting_approval"
      
  incomplete_focus:
    - task: "009-late-fee-penalty-apr-decision"
      title: "Late Fee & Penalty APR Decisions"
      planned: "Prepare for Open Agenda forum"
      note: "No activity detected today"
      
  suggested_task_updates:
    - task: "001-beta-rollout-scope"
      file: "Tasks/001-beta-rollout-scope-document.md"
      updates:
        - field: "next_action"
          from: "Complete review of jira-test-cases.md"
          to: "Resolve open questions with stakeholders"
        - field: "next_action_due"
          from: "2024-12-30"
          to: "2026-01-06"
      status: "awaiting_approval"
      
  completed_tasks:  # Archive prompts
    - task: "002-collections-loan-servicing-split"
      title: "Collections Policy Split"
      completed_evidence:
        - "Jira MRC-1911 transitioned to Done"
        - "Slack: 'Collections handover complete'"
      archive_prompt:
        status: "awaiting_approval"
        destination: "Archive/2024-12/"
```

---

### 3. Status Check

**Trigger:** "Where are we on X?" or "Status of [initiative]"

**Logic:**
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
```

**Output Schema:**
```yaml
status_check:
  query: "Where are we on Troy Beta?"
  matched_tasks:
    - task: "001-beta-rollout-scope-document"
      title: "Finish Troy's CC Beta rollout scope document"
      
  summary: |
    **Troy Beta Rollout** is currently *in progress* (P0).
    
    Last action completed: Reviewed jira-test-cases.md (Dec 30)
    Next action: Resolve open questions with stakeholders (due Jan 6)
    
    Recent progress:
    - Dec 30: Completed test case validation
    - Dec 28: Updated milestone timeline
    - Dec 20: Initial scope draft completed
    
    No blockers currently.
    
  evidence:
    - type: "jira"
      key: "MRC-3266"
      url: "https://domain.atlassian.net/browse/MRC-3266"
      status: "In Review"
    - type: "slack"
      thread: "C081E1LDD60/p1765284956532589"
      topic: "Beta timeline discussion"
    - type: "confluence"
      page: "Milestones & Rollout Stages"
      url: "https://domain.atlassian.net/wiki/..."
```

**Validation:** User can respond accurately to "Where are we on X?" within 30 seconds.

---

## Input Schema

```yaml
# Received from Orchestrator
input:
  workflow_type: "daily_briefing" | "daily_closing" | "status_check"
  
  context: <context_object>  # From Context Gatherer
  analysis: <analysis_object>  # From Analyzer
  
  # For status_check only
  query: "Where are we on Troy Beta?"
  
  # Prioritization rules for focus selection
  prioritization_rules: <from Knowledge/prioritization-rules.md>
```

---

## LLM Prompt Templates

### Daily Briefing Prompt

```markdown
You are the Workflow Agent generating a Daily Briefing.

## Date
{today's date}

## Context
{context summary from Context Gatherer}

## Analysis
{analysis from Analyzer}

## Active Tasks
{list of non-blocked tasks with frontmatter}

## Prioritization Rules
{rules from Knowledge/prioritization-rules.md}

## Instructions
1. Select 2-3 items for "Focus Today" based on:
   - next_action_due earliest first
   - P0 before P1
   - Analyzer alerts (overdue items)
2. Provide brief reason for each focus item
3. List remaining P0/P1 tasks
4. Show blocked tasks with follow-up dates
5. Include any alerts from Analyzer

## Output Rules
- Max 3 focus items
- Reasons should be 1 sentence
- Do NOT include task counts in headers
- Do NOT repeat status icons (🔴/🟡) for each task

## Format
Return YAML matching the briefing output schema.
```

### Daily Closing Prompt

```markdown
You are the Workflow Agent generating a Daily Closing report.

## Date
{today's date}

## Morning State
{tasks state from morning briefing}

## Current State
{current tasks from Context Gatherer}

## Day's Context
{context from Context Gatherer - full day}

## Analysis
{analysis from Analyzer}

## Instructions
1. Identify what was accomplished today (compare states)
2. For each task with progress, check linked Jira:
   - If Jira is stale, generate comment update
   - Format: "Update YYYY-MM-DD: [what happened]"
   - Include due date updates if implicit changes detected
3. List incomplete focus items from morning
4. Suggest next_action updates for progressed tasks
5. Identify completed tasks ready for archiving

## Jira Update Format
Comments should follow: "Update YYYY-MM-DD: [summary of progress]. Next: [next step]."

## Output Rules
- Hyperlink Jira card titles for verification
- Include specific evidence for accomplishments
- Always include due date review in suggestions

## Format
Return YAML matching the closing output schema.
```

---

## Jira Update Format

All Jira comments follow a consistent format:

```
Update YYYY-MM-DD: [Summary of what was done].
[Additional context if needed].
Next: [Next step and target date].
```

**Example:**
```
Update 2024-12-30: Completed review of jira-test-cases.md. 
10 BA Initiatives validated, 148 stories mapped.
Next: Resolve open questions with stakeholders by Jan 6.
```

---

## Action Execution

When user approves pending actions, Orchestrator executes:

| Action Type | MCP/Method | Parameters |
|-------------|------------|------------|
| `jira_comment` | `mcp_atlassian_addCommentToJiraIssue` | `issueIdOrKey`, `commentBody` |
| `jira_transition` | `mcp_atlassian_transitionJiraIssue` | `issueIdOrKey`, `transition.id` |
| `jira_due_date` | `mcp_atlassian_editJiraIssue` | `issueIdOrKey`, `fields.duedate` |
| `jira_description` | `mcp_atlassian_editJiraIssue` | `issueIdOrKey`, `fields.description` |
| `task_update` | Local file edit | Update frontmatter |
| `archive_task` | File move | `Tasks/X.md` → `Archive/YYYY-MM/X.md` |

---

## Acceptance Criteria

### Daily Briefing
- [ ] Produces 2-3 focus recommendations (not more)
- [ ] Excludes blocked tasks from focus
- [ ] Sorts by next_action_due
- [ ] Includes reason for each focus item
- [ ] Lists blocked tasks with follow-up dates
- [ ] Includes Analyzer alerts

### Daily Closing
- [ ] Summarizes day's accomplishments with evidence
- [ ] Generates Jira update suggestions with correct format
- [ ] Flags incomplete focus items
- [ ] Suggests next_action updates
- [ ] Identifies tasks ready for archiving
- [ ] Hyperlinks Jira cards for verification

### Status Check
- [ ] Matches query to relevant task(s)
- [ ] Returns current status and next action
- [ ] Shows recent progress (last 3-5 entries)
- [ ] Links to evidence (Jira, Slack, Confluence)
- [ ] User can answer "Where are we?" in 30 seconds

---

## Related Agents

| Agent | Relationship |
|-------|--------------|
| **Orchestrator** | Calls Workflow with context + analysis |
| **Context Gatherer** | Provides context object |
| **Analyzer** | Provides analysis (alerts, suggestions) |
| **Reflection** | Handles weekly/monthly (separate agent) |

---

## Configuration

```yaml
# In config.yaml
workflow:
  daily_briefing:
    max_focus_items: 3
    include_p2_tasks: false
    
  daily_closing:
    jira_comment_format: "Update {date}: {summary}\n\nNext: {next_step}"
    always_suggest_due_date_review: true
    
  status_check:
    progress_log_entries: 5  # How many to show
    include_slack_evidence: true
```

---

*See `../docs/SPEC-agent-architecture.md` for full system architecture.*

