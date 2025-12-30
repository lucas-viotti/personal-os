# Analyzer Agent

**Purpose:** Validate task metadata against latest context and suggest corrections.

**Version:** 1.0  
**Last Updated:** 2024-12-30

---

## Overview

The Analyzer is an **LLM-based agent** that reviews task metadata against fresh context and suggests updates. It acts as a "sanity check" before surfacing tasks to the user.

> **Cache TTL:** 25 minutes (configurable). If context is < 25 min old, reuse cached analysis.

---

## Responsibilities

| Responsibility | Description |
|----------------|-------------|
| **Priority Validation** | Check if P0-P3 still makes sense given recent activity |
| **Status Review** | Verify blocked/started/not-started is accurate |
| **Due Date Verification** | Check for implicit deadline changes in discussions |
| **Blocker Detection** | Identify resolved or new blockers from context |
| **Consistency Check** | Ensure `next_action` matches reality |
| **Action Due Alerts** | Surface actions due today or overdue |

---

## Analysis Checks

| Check | Input | Logic | Output |
|-------|-------|-------|--------|
| **Priority drift** | Context + Task | High activity on low-priority task | `suggest_priority_change: P2 → P1` |
| **Stale blocker** | Context + blocked_expected | Blocker discussed as resolved in Slack | `suggest_status_change: b → s` |
| **Missed deadline** | Context + next_action_due | Date passed without completion | `alert: overdue_action` |
| **Implicit date change** | Context (Slack/Jira) | Discussion mentions new date | `suggest_due_date_change` |
| **Completed action** | Context + next_action | Action discussed as done | `suggest_next_action_update` |
| **New blocker** | Context (Slack/Jira) | Discussion indicates new blocker | `suggest_status_change: s → b` |

---

## Input Schema

```yaml
# Received from Orchestrator (via Context Gatherer)
input:
  context: <context_object>  # Full context from Context Gatherer
  
  # Prioritization rules (loaded from Knowledge/prioritization-rules.md)
  prioritization_rules:
    categories:
      - name: "Critical & Urgent"
        priority: P0
        criteria:
          - "Blocks multiple people or critical deadlines"
          - "Executive escalation"
          - "Production incident"
      - name: "Important & Time-Sensitive"
        priority: P1
        criteria:
          - "Weekly commitments"
          - "External stakeholder expectations"
      # ...
```

---

## Output Schema

```yaml
analysis:
  timestamp: "2024-12-30T17:52:00Z"
  cache_valid_until: "2024-12-30T18:17:00Z"  # +25 min
  
  task_reviews:
    - task: "004-cardholder-agreement-followup"
      file: "Tasks/004-cardholder-agreement-followup.md"
      current:
        priority: "P1"
        status: "b"
        blocked_by: "Lead Bank - overlimit clause"
        blocked_expected: "2026-01-10"
        next_action: null
        next_action_due: null
      findings:
        - type: "blocker_resolved"
          evidence: "Slack thread C081E1LDD60 - Lead confirmed resolution Dec 16"
          confidence: "high"
      suggestions:
        - action: "update_status"
          field: "status"
          from: "b"
          to: "s"
          reason: "Blocker resolved per Slack discussion"
        - action: "set_next_action"
          field: "next_action"
          value: "Update agreement with Lead Bank decision"
          field2: "next_action_due"
          value2: "2025-12-31"
          reason: "Blocker resolved, task can proceed"
          
    - task: "001-beta-rollout-scope-document"
      file: "Tasks/001-beta-rollout-scope-document.md"
      current:
        priority: "P0"
        status: "s"
        next_action: "Complete review of jira-test-cases.md"
        next_action_due: "2025-12-30"
      findings:
        - type: "action_due_today"
          severity: "high"
          message: "Next action due TODAY"
      suggestions: []  # No changes needed, just surface as focus
      
    - task: "009-late-fee-penalty-apr-decision"
      file: "Tasks/009-late-fee-penalty-apr-decision.md"
      current:
        priority: "P0"
        status: "s"
        next_action: "Attend decision forum"
        next_action_due: "2026-01-08"
      findings:
        - type: "implicit_date_change"
          evidence: "Slack #us-markets: Thiago requested postponement, new date mid-Jan"
          confidence: "medium"
      suggestions:
        - action: "update_due_date"
          field: "next_action_due"
          from: "2026-01-08"
          to: "2026-01-15"
          reason: "Forum postponed per Slack discussion"
          requires_confirmation: true  # Medium confidence → ask user
      
  alerts:
    - type: "overdue_action"
      task: "005-jira-cleanup"
      file: "Tasks/005-jira-cleanup.md"
      message: "next_action_due was Dec 15, no update since"
      severity: "medium"
      suggested_action: "Review task and update next_action_due or mark complete"
      
    - type: "stale_task"
      task: "012-ccf-product-team-prioritization"
      file: "Tasks/012-ccf-product-team-prioritization.md"
      message: "No activity in 14+ days"
      severity: "low"
      suggested_action: "Verify task is still relevant"
      
  no_issues:
    - task: "002-collections-loan-servicing-split"
      reason: "Recently completed, metadata appears current"
```

---

## Confidence Levels

| Level | Criteria | Auto-Recommend? |
|-------|----------|-----------------|
| **High** | Direct evidence (explicit Slack message, Jira status change) | ✅ Yes |
| **Medium** | Inferred (discussion suggests completion, but not explicit) | ⚠️ Ask user |
| **Low** | Speculative (related topic discussed, unclear if applies) | ❌ No, just note |

---

## LLM Prompt Template

```markdown
You are the Analyzer Agent for Personal OS.

## Your Task
Review each task's metadata against the provided context and identify:
1. Tasks needing status changes (blocked ↔ started)
2. Tasks needing priority changes
3. Actions that are due today or overdue
4. Implicit deadline changes mentioned in context
5. Blockers that appear resolved

## Prioritization Rules
{prioritization_rules from Knowledge/prioritization-rules.md}

## Context
{context object from Context Gatherer}

## Current Tasks
{list of task files with frontmatter}

## Analysis Guidelines
- Only suggest changes with HIGH confidence evidence
- For MEDIUM confidence, mark requires_confirmation: true
- For LOW confidence, add to findings but no suggestion
- Always cite specific evidence (Slack thread ID, Jira key, etc.)
- Never suggest changes without evidence from context
- Flag any task where next_action_due is today or past

## Output Format
Return YAML matching the output schema above.
```

---

## Execution Flow

```
1. Receive context from Context Gatherer
2. Load prioritization rules from Knowledge/prioritization-rules.md
3. For each active task:
   a. Check if any context references this task
   b. If yes, analyze for suggested changes
   c. Check next_action_due against today's date
   d. Check blocked_expected against today's date
   e. Compare current status with context evidence
4. Generate alerts for overdue/stale items
5. Return structured analysis
```

---

## Caching

To reduce API calls and latency:

```yaml
# Cache key: hash of (context.timestamp + task_list)
cache:
  enabled: true
  ttl: 25  # minutes
  storage: "memory"  # or "file" for persistence
```

If cached analysis is < 25 minutes old and task list unchanged, return cached results.

---

## Error Handling

```yaml
# On LLM error
analysis:
  timestamp: "2024-12-30T17:52:00Z"
  status: "partial"
  error: "LLM timeout after 30s"
  
  task_reviews: []  # Empty on failure
  
  alerts:
    - type: "analyzer_error"
      message: "Analysis incomplete - LLM timeout"
      severity: "high"
```

**Fallback:** If Analyzer fails, Workflow Agent proceeds with raw task data (no suggestions).

---

## Acceptance Criteria

- [ ] Receives context object from Context Gatherer
- [ ] Loads prioritization rules from Knowledge/prioritization-rules.md
- [ ] Reviews each active task against context
- [ ] Detects priority drift (activity on low-priority tasks)
- [ ] Detects stale blockers (resolved in context)
- [ ] Detects missed deadlines (next_action_due in past)
- [ ] Detects implicit date changes (discussed in Slack/Jira)
- [ ] Assigns confidence levels (high/medium/low) to suggestions
- [ ] Only auto-recommends high confidence suggestions
- [ ] Flags medium confidence for user confirmation
- [ ] Caches results for 25 minutes
- [ ] Output matches defined schema
- [ ] Handles LLM timeout gracefully

---

## Related Agents

| Agent | Relationship |
|-------|--------------|
| **Orchestrator** | Calls Analyzer with context |
| **Context Gatherer** | Provides context object |
| **Workflow** | Receives analysis, generates outputs |
| **Reflection** | Receives analysis for weekly summaries |

---

## Configuration

```yaml
# In config.yaml
analyzer:
  cache_ttl: 25  # minutes - configurable, default 25
  
  confidence_thresholds:
    high: 0.85
    medium: 0.60
    low: 0.30
    
  checks_enabled:
    priority_drift: true
    stale_blocker: true
    missed_deadline: true
    implicit_date_change: true
    completed_action: true
    new_blocker: true
    stale_task: true
    
  stale_task_threshold_days: 14  # Alert if no activity in X days
```

---

*See `../docs/SPEC-agent-architecture.md` for full system architecture.*

