# Implementation Plan: Schema v2.0

**Created:** 2024-12-30
**Status:** In Progress

---

## Overview

This plan implements PRD Phase 2: Schema v2.0. It does NOT include the multi-agent architecture from SPEC (that's Phase 3+).

## Changes Summary

### New Fields (Schema v2.0)

| Field | Required | When |
|-------|----------|------|
| `due_date` | Yes | All tasks |
| `next_action` | Yes | When `status: s` AND task has subtasks |
| `next_action_due` | Yes | When `next_action` is set |
| `blocked_type` | Yes | When `status: b` |
| `blocked_by` | Yes | When `status: b` |
| `blocked_expected` | Optional | When `status: b` |

### Behavior Changes

1. **Daily Briefing**: Surface tasks by `next_action_due` (earliest first), not just priority
2. **Exclude blocked**: Tasks with `status: b` NOT shown in focus
3. **Tracking section**: Blocked tasks shown separately with follow-up dates

---

## Phase 2.1: Sync AGENTS.md ✅ (public has it)

- [x] Public repo AGENTS.md already has Schema v2.0
- [ ] Copy to private repo `my-personal-os-new/AGENTS.md`

**Test:** `grep -c "next_action_due" AGENTS.md` returns > 0

---

## Phase 2.2: Migrate Tasks

### Migration Checklist (12 tasks)

| Task | Priority | Current Status | Due Date | Next Action | Blocked? |
|------|----------|----------------|----------|-------------|----------|
| 001-beta-rollout-scope-document.md | P0 | n | ❌ | ❌ | No |
| 002-collections-loan-servicing-split.md | P1 | ? | ❌ | ❌ | ? |
| 004-cardholder-agreement-followup.md | P1 | s | ❌ | ❌ | Yes (Lead Bank) |
| 005-jira-cleanup.md | ? | ? | ❌ | ❌ | ? |
| 006-charging-interest-spreadsheet-update.md | ? | ? | ❌ | ❌ | ? |
| 009-late-fee-penalty-apr-decision.md | P0 | ? | ❌ | ❌ | ? |
| 010-mla-scra-whiteboard-coordination.md | P1 | ? | ❌ | ❌ | ? |
| 011-weekly-1on1-liz-bolton-setup.md | ? | ? | ❌ | ❌ | ? |
| 012-ccf-product-team-prioritization.md | P1 | ? | ❌ | ❌ | ? |
| 013-equifax-questionnaire-followup.md | P1 | ? | ❌ | ❌ | ? |
| 014-beta-confluence-page-update.md | ? | ? | ❌ | ❌ | ? |
| enhance-daily-closing-workflow.md | ? | ? | ❌ | ❌ | ? |

### Migration Rules

1. **If task has multiple `- [ ]` actions**: Set `next_action` to earliest due + `next_action_due`
2. **If task is blocked**: Set `status: b`, add `blocked_type`, `blocked_by`, `blocked_expected`
3. **All tasks**: Add `due_date` (ask user if not clear)

**Test:** Validate script checks all tasks have required fields

---

## Phase 2.3-2.6: Workflow Updates

### Daily Briefing Changes

```yaml
# BEFORE: Sort by priority
tasks_p0 | tasks_p1 | ...

# AFTER: Sort by next_action_due, exclude blocked
1. Filter: status != 'b'
2. Sort by: next_action_due ASC (earliest first)
3. Take top 3 for "Focus Today"
4. Group remaining by priority for context
5. Add "Tracking (Blocked)" section for status: b tasks
```

### Daily Closing Changes

```yaml
# Add: Flag incomplete focus items
1. Check tasks from morning briefing
2. If next_action_due passed without completion → Alert
3. Suggest: Update next_action or move due date
```

### Weekly Review Changes

```yaml
# Add: Blocked > 7 days section
1. Find tasks with status: b
2. Calculate days_blocked = today - last_progress_date
3. If days_blocked > 7 → Surface in "Long-blocked" section
```

---

## Phase 2.7: logbook-local.py Updates

Same logic as GitHub Actions, but in Python:

```python
def get_focus_tasks(tasks):
    # Filter out blocked
    active = [t for t in tasks if t['status'] != 'b']
    
    # Sort by next_action_due (earliest first)
    active.sort(key=lambda t: t.get('next_action_due', t.get('due_date', '9999-12-31')))
    
    return active[:3]

def get_blocked_tasks(tasks):
    return [t for t in tasks if t['status'] == 'b']
```

---

## Phase 2.8: Validation Tests

### Schema Validation Test

```python
def test_schema_compliance():
    """All tasks must have required Schema v2.0 fields."""
    for task in get_all_tasks():
        assert 'due_date' in task, f"{task['title']} missing due_date"
        
        if task['status'] == 's':
            # Started tasks with multiple actions need next_action
            if has_multiple_actions(task):
                assert 'next_action' in task
                assert 'next_action_due' in task
        
        if task['status'] == 'b':
            assert 'blocked_type' in task
            assert 'blocked_by' in task
```

### Focus Logic Test

```python
def test_focus_excludes_blocked():
    """Blocked tasks should not appear in focus recommendations."""
    tasks = [
        {'title': 'Task A', 'status': 's', 'next_action_due': '2024-12-30'},
        {'title': 'Task B', 'status': 'b', 'next_action_due': '2024-12-29'},  # Earlier but blocked
    ]
    focus = get_focus_tasks(tasks)
    assert len(focus) == 1
    assert focus[0]['title'] == 'Task A'

def test_focus_sorted_by_next_action_due():
    """Focus should prioritize earliest next_action_due."""
    tasks = [
        {'title': 'P0 Task', 'priority': 'P0', 'status': 's', 'next_action_due': '2024-12-31'},
        {'title': 'P2 Task', 'priority': 'P2', 'status': 's', 'next_action_due': '2024-12-30'},  # Earlier
    ]
    focus = get_focus_tasks(tasks)
    assert focus[0]['title'] == 'P2 Task'  # Earlier due date wins over priority
```

---

## Execution Order

1. **P2-1**: Sync AGENTS.md (5 min)
2. **P2-2**: Verify core/templates/CLAUDE.md (already done)
3. **P2-3**: Migrate tasks (need user input for due dates)
4. **P2-4-6**: Update GitHub Actions workflows
5. **P2-7**: Update logbook-local.py
6. **P2-8**: Write and run validation tests
7. **P2-9**: Commit and sync repos

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Missing due_date for tasks | Ask user for all tasks upfront |
| Workflow breaks during transition | Test locally before deploying |
| Logic divergence between Actions and local script | Single source of truth in Knowledge/ |

---

*Next review: After all tasks migrated*

