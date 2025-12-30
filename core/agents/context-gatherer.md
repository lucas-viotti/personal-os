# Context Gatherer Agent

**Purpose:** Fetch and synthesize data from all sources into a unified context.

**Version:** 1.0  
**Last Updated:** 2024-12-30

---

## Overview

The Context Gatherer is a **code-based agent** (not LLM-based) that connects to external sources via MCPs and local file system to build a comprehensive context object for other agents.

---

## Responsibilities

| Responsibility | Description |
|----------------|-------------|
| **Source Integration** | Connect to Slack, Jira, Confluence, Git, local files |
| **Data Extraction** | Pull relevant updates within specified period |
| **Synthesis** | Combine raw data into structured context |
| **Relevance Filtering** | Surface only task-relevant information |
| **Task Linking** | Associate external data with local task files |

---

## Data Sources

| Source | Integration | Data Extracted |
|--------|-------------|----------------|
| **Slack** | Slack MCP | Messages, threads, mentions, decisions |
| **Jira** | Atlassian MCP | Status changes, comments, assignee updates, due date changes |
| **Confluence** | Atlassian MCP | Page edits, comments |
| **Git** | Local CLI (`git log`) | Commits to Tasks/, Knowledge/ |
| **Local Files** | File system | Task files with frontmatter |
| **Meetings** | File system | Gemini transcripts in Knowledge/meetings/ (manual import) |

---

## Input Schema

```yaml
# Received from Orchestrator
input:
  period:
    type: "last_24h" | "last_7d" | "since_timestamp" | "custom"
    start: "2024-12-29T08:30:00Z"
    end: "2024-12-30T17:50:00Z"
  
  # Optional filters
  filters:
    sources: ["slack", "jira", "confluence", "git", "local"]  # Which to fetch
    task_filter: "active"  # active | all | specific_task
```

---

## Output Schema

```yaml
context:
  timestamp: "2024-12-30T17:50:00Z"
  period:
    type: "last_24h"
    start: "2024-12-29T08:30:00Z"
    end: "2024-12-30T17:50:00Z"
  
  sources:
    slack:
      status: "success" | "failed" | "partial"
      error: null | "MCP timeout after 30s"
      messages_analyzed: 47
      relevant_threads:
        - thread_id: "C081E1LDD60/p1765284956532589"
          channel: "#troy-project"
          topic: "Lead Bank overlimit clause"
          key_points:
            - "Lead confirmed no 3-cycle delay"
            - "Must include in minimum payment immediately"
          related_tasks: ["004-cardholder-agreement"]
          timestamp: "2024-12-30T14:30:00Z"
        - thread_id: "C08TR3PKC1W/p1765551881487039"
          channel: "#us-markets"
          topic: "Late Fee decision forum scheduling"
          key_points:
            - "Thiago requested postponement due to holidays"
            - "New date likely mid-January"
          related_tasks: ["009-late-fee-penalty-apr-decision"]
          timestamp: "2024-12-30T10:15:00Z"
          
    jira:
      status: "success"
      issues_updated:
        - key: "MRC-3266"
          url: "https://domain.atlassian.net/browse/MRC-3266"
          summary: "Beta Rollout Scope Document"
          current_status: "In Review"
          changes:
            - field: "status"
              from: "In Progress"
              to: "In Review"
              timestamp: "2024-12-30T15:00:00Z"
            - field: "comment"
              content: "Draft sent to Legal"
              author: "Lucas Viotti"
              timestamp: "2024-12-30T15:30:00Z"
          related_tasks: ["001-beta-rollout-scope"]
        - key: "MRC-1912"
          url: "https://domain.atlassian.net/browse/MRC-1912"
          summary: "Cardholder Agreement"
          current_status: "In Progress"
          changes:
            - field: "comment"
              content: "Awaiting Lead Bank response on overlimit clause"
          related_tasks: ["004-cardholder-agreement"]
          
    confluence:
      status: "success"
      pages_edited:
        - page_id: "264465777127"
          url: "https://domain.atlassian.net/wiki/spaces/TROY/pages/264465777127"
          title: "Milestones & Rollout Stages"
          edit_summary: "Updated beta timeline"
          editor: "Lucas Viotti"
          timestamp: "2024-12-30T11:00:00Z"
          related_tasks: ["001-beta-rollout-scope"]
          
    git:
      status: "success"
      commits:
        - hash: "abc123"
          timestamp: "2024-12-30T14:30:00Z"
          message: "Update progress on cardholder agreement"
          files:
            - "Tasks/004-cardholder-agreement-followup.md"
        - hash: "def456"
          timestamp: "2024-12-30T16:00:00Z"
          message: "Complete collections policy split task"
          files:
            - "Tasks/002-collections-loan-servicing-split.md"
          
    local_tasks:
      status: "success"
      tasks:
        - file: "Tasks/001-beta-rollout-scope-document.md"
          title: "Finish Troy's CC Beta rollout scope document"
          priority: "P0"
          status: "s"
          due_date: "2026-01-16"
          next_action: "Complete review of jira-test-cases.md"
          next_action_due: "2025-12-30"
          blocked_by: null
        - file: "Tasks/004-cardholder-agreement-followup.md"
          title: "Review and Finalize Cardholder Agreement V2"
          priority: "P1"
          status: "b"
          due_date: "2026-01-31"
          next_action: null
          blocked_by: "Lead Bank - overlimit clause response"
          blocked_expected: "2026-01-10"
        - file: "Tasks/009-late-fee-penalty-apr-decision.md"
          title: "Late Fee & Penalty APR Decisions"
          priority: "P0"
          status: "s"
          due_date: "2026-01-31"
          next_action: "Attend decision forum when scheduled"
          next_action_due: "2026-01-08"
          blocked_by: null
          
    meetings:  # Optional - only if transcripts exist
      status: "success"
      transcripts:
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

---

## Implementation Details

### Slack Fetching

```python
def fetch_slack(period_start, period_end):
    """
    Uses Slack MCP to search messages.
    
    1. Search messages in relevant channels
    2. Filter by date range
    3. Group by thread
    4. Extract key points (decisions, action items)
    5. Link to tasks by keyword matching
    """
    # Use: mcp_slack_conversations_search_messages
    # Filter: filter_date_after, filter_date_before
    # Group threads by thread_ts
```

### Jira Fetching

```python
def fetch_jira(period_start, period_end, project_key):
    """
    Uses Atlassian MCP to get issue updates.
    
    1. Search issues updated in period (JQL)
    2. Expand changelog and comments
    3. Filter to user's issues (assignee, reporter, watcher)
    4. Extract field changes with before/after
    5. Link to tasks by issue key in resource_refs
    """
    # Use: mcp_atlassian_searchJiraIssuesUsingJql
    # JQL: project = X AND updated >= -24h AND (assignee = user OR reporter = user OR watcher = user)
    # Expand: changelog, comment
```

### Confluence Fetching

```python
def fetch_confluence(period_start, period_end, spaces):
    """
    Uses Atlassian MCP to get page edits.
    
    1. Get recently modified pages in spaces
    2. Filter by date range
    3. Extract edit summary from version history
    4. Link to tasks by page title matching
    """
    # Use: mcp_atlassian_getPagesInConfluenceSpace
    # Filter: sort=-modified-date
```

### Git Fetching

```python
def fetch_git(period_start, period_end):
    """
    Uses local git CLI to get commits.
    
    1. Run: git log --since="period_start" --until="period_end" -- Tasks/ Knowledge/
    2. Parse commit hash, message, files changed
    3. Link commits to tasks by file path
    """
    # Command: git log --since="24 hours ago" --name-only --pretty=format:"%H|%aI|%s" -- Tasks/*.md Knowledge/*.md
```

### Local Tasks Fetching

```python
def fetch_local_tasks():
    """
    Reads all task files from Tasks/ directory.
    
    1. Glob Tasks/*.md
    2. Parse YAML frontmatter
    3. Extract Schema v2.0 fields
    4. Return structured task list
    """
    # Fields: title, priority, status, due_date, next_action, next_action_due, blocked_by, blocked_expected
```

---

## Pre-processing Rules

Before returning context, apply these filters:

1. **Filter noise** — Remove bot messages, automated notifications
2. **Group by task** — Associate external data with local task files
3. **Extract decisions** — Pull out key decisions from Slack threads
4. **Extract action items** — Identify committed actions with owners/dates
5. **Flag blockers** — Highlight blocker mentions
6. **Flag deadline changes** — Surface implicit date changes

---

## Error Handling

```yaml
# On MCP failure, return partial context
sources:
  slack:
    status: "failed"
    error: "MCP timeout after 30s"
    messages_analyzed: 0
    relevant_threads: []
  jira:
    status: "success"
    # ... normal data
```

**Rule:** Never block entire workflow for one source failure. Continue with available data.

---

## Task Linking Logic

Link external data to local tasks using:

1. **Jira key in resource_refs** — `MRC-3266` → task with `resource_refs: [MRC-3266]`
2. **File name in commit** — `Tasks/001-beta-rollout-scope.md` → that task
3. **Keyword matching** — "Beta rollout" in Slack → task with "beta rollout" in title
4. **Explicit mention** — "@task:001-beta-rollout" in Slack (future)

---

## Acceptance Criteria

- [ ] Accepts period parameters from Orchestrator (start/end timestamps)
- [ ] Fetches Slack messages within specified period
- [ ] Fetches Jira updates within specified period (changelog, comments)
- [ ] Fetches Confluence edits within specified period
- [ ] Reads Git commits to task/knowledge files
- [ ] Parses local task files for current state (Schema v2.0)
- [ ] Parses meeting transcripts from Knowledge/meetings/ (if present)
- [ ] Filters noise (bot messages, automated notifications)
- [ ] Returns arrays of items per source (multiple threads, issues, etc.)
- [ ] Links context to specific tasks when possible
- [ ] Handles MCP failures gracefully (continues with available data)
- [ ] Output matches defined schema

---

## Related Agents

| Agent | Relationship |
|-------|--------------|
| **Orchestrator** | Calls Context Gatherer with period parameters |
| **Analyzer** | Receives context, validates task metadata |
| **Workflow** | Receives context, generates briefing/closing |
| **Reflection** | Receives context, generates weekly review |

---

## Configuration

```yaml
# In config.yaml
context_gatherer:
  cache_ttl: 25  # minutes - reuse cached context if < this age
  
  slack:
    enabled: true
    channels: []  # Empty = search all accessible
    
  jira:
    enabled: true
    project_key: "${JIRA_PROJECT}"
    
  confluence:
    enabled: true
    spaces: "${CONFLUENCE_SPACES}"  # Comma-separated
    
  git:
    enabled: true
    paths: ["Tasks/", "Knowledge/"]
```

---

*See `../docs/SPEC-agent-architecture.md` for full system architecture.*

