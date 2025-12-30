# Personal OS Schema v2.0 - Update Plan

**Created:** 2024-12-30
**Status:** In Progress

## Overview

This document outlines the migration from Schema v1.0 to Schema v2.0, introducing:
- `next_action` and `next_action_due` fields for granular focus
- Enhanced blocking support (`blocked_type`, `blocked_by`, `blocked_expected`)
- Clearer status semantics

---

## Schema v2.0 Definition

```yaml
---
# === Identity ===
title: [Actionable task name]
category: [technical|outreach|research|writing|admin|personal|other]

# === Priority & Status ===
priority: [P0|P1|P2|P3]  # Criticality (goal alignment), NOT urgency
status: [n|s|b|d]        # not_started | started | blocked | done

# === Blocking (only when status: b) ===
blocked_type: [external|dependency|decision]  # required when blocked
blocked_by: [Who/what is blocking]            # required when blocked
blocked_expected: [YYYY-MM-DD]                # optional - when to check back

# === Dates ===
created_date: [YYYY-MM-DD]
due_date: [YYYY-MM-DD]           # Final deadline
completed_date: [YYYY-MM-DD]     # Added when archived

# === Focus (when status: s AND task has multiple next actions) ===
next_action: [Single action with earliest due date, or "TBD" if unclear]
next_action_due: [YYYY-MM-DD]    # When this action is due
next_review_date: [YYYY-MM-DD]   # Only when next_action: TBD - when to revisit

# === Estimates & References ===
estimated_time: [minutes]        # optional
resource_refs: []                # optional
---
```

### Schema Field Requirements

| Field | When Required |
|-------|---------------|
| `priority` | Always |
| `status` | Always |
| `due_date` | Always (final deadline) |
| `blocked_*` | Only when `status: b` |
| `next_action` | When `status: s` AND task has multiple subtasks |
| `next_action_due` | When `next_action` is set (and not TBD) |
| `next_review_date` | Only when `next_action: TBD` |

### Priority vs Urgency Clarification

| Concept | Field | Meaning |
|---------|-------|---------|
| **Criticality** | `priority: P0-P3` | How important to goals |
| **Urgency** | `next_action_due` or `due_date` | When to act |

A P0 task might not need action today (if `next_action_due` is next week).
A P2 task might need immediate action (if `next_action_due` is today).

---

## Phase 1: Documentation Updates

### 1.1 Update `AGENTS.md` (Public Repo)

**File:** `personal-os-public/AGENTS.md`

**Changes:**
- [ ] Update Task Template section with new schema
- [ ] Add "Focus Management" section explaining `next_action` fields
- [ ] Add "Blocked Tasks" section explaining blocking fields
- [ ] Update "Daily Guidance" to reference `next_action_due`
- [ ] Add guardrails documentation
- [ ] Update status codes to clarify blocked vs waiting

**New Sections to Add:**
```markdown
## Focus Management (next_action fields)

Every active task (`status: s`) should have:
- `next_action`: The action with the EARLIEST due date among all pending actions
- `next_action_due`: When that specific action is due

**Guardrails:**
1. `next_action` must be a SINGLE action (no "and")
2. Must match a `- [ ]` item in the Next Actions list
3. When completed, update immediately to the next action (by earliest due date)
4. If multiple actions have the same due date, pick any one
5. When creating/updating tasks with multiple next actions, AI should ask: "What is the earliest due date for any of these actions?"

## Blocked Tasks

When a task is blocked (`status: b`), specify:
- `blocked_type`: external | dependency | decision
- `blocked_by`: Who or what is blocking progress
- `blocked_expected`: When to follow up (optional but recommended)

**AI Behavior:**
- Blocked tasks are tracked but NOT surfaced as "focus today"
- AI reminds you to check blocked items at `blocked_expected` date
- When unblocked, clear blocking fields and set `next_action`
```

### 1.2 Update `core/templates/CLAUDE.md`

**File:** `personal-os/personal-os/core/templates/CLAUDE.md`

**Changes:**
- [ ] Update Task File Format section with new schema
- [ ] Update Task Status Codes to include blocking semantics
- [ ] Add Focus Management section
- [ ] Update automatic system integrity checks to use new fields

### 1.3 Update `Knowledge/prioritization-rules.md`

**File:** Both repos

**Changes:**
- [ ] Add section on how `next_action_due` interacts with prioritization
- [ ] Clarify that blocked tasks are deprioritized automatically

---

## Phase 2: Task Migration

### 2.1 Active Tasks to Migrate (9 tasks)

| Task | Current Status | New Fields Needed |
|------|---------------|-------------------|
| 001-beta-rollout-scope-document.md | s (started) | next_action, next_action_due |
| 004-cardholder-agreement-followup.md | s (started) | blocked_*, next_action |
| 005-jira-cleanup.md | n (not started) | next_action, next_action_due |
| 006-charging-interest-spreadsheet-update.md | ? | TBD |
| 009-late-fee-penalty-apr-decision.md | s (started) | blocked_*, next_action |
| 010-mla-scra-whiteboard-coordination.md | ip (→ s) | next_action, next_action_due |
| 012-ccf-product-team-prioritization.md | ? | TBD |
| 013-equifax-questionnaire-followup.md | s (started) | blocked_*, next_action |
| 014-confluence-documentation-update.md | ? | TBD |

### 2.2 Migration Steps per Task

For each task:
1. Read current frontmatter
2. Ensure `due_date` is set (final deadline)
3. If task has multiple `- [ ]` items AND `status: s`:
   - Identify action with EARLIEST due date → `next_action`
   - Set `next_action_due` for that action
   - If unclear, set `next_action: TBD` + `next_review_date`
4. If status suggests blocked, add `blocked_*` fields
5. Normalize status codes (ip → s)
6. Write updated frontmatter

### 2.3 Migration Decision Tree

```
Is task status: s (started)?
├── NO → Only ensure due_date is set
└── YES → Does task have multiple next actions?
    ├── NO (single action) → Only ensure due_date is set
    └── YES (multiple actions) → Is there a clear next action?
        ├── YES → Set next_action + next_action_due (earliest)
        └── NO → Set next_action: TBD + next_review_date
```

---

## Phase 3: Workflow Updates

### 3.1 GitHub Actions Workflows

**Files:**
- `.github/workflows/daily-briefing.yml`
- `.github/workflows/daily-closing.yml`
- `.github/workflows/weekly-review.yml`

**Changes:**

#### Daily Briefing
- [ ] Update task parsing to read `next_action` and `next_action_due`
- [ ] AI prompt: Surface tasks by `next_action_due` not just `priority`
- [ ] AI prompt: Skip `status: b` tasks from focus recommendations
- [ ] AI prompt: Show blocked tasks in separate "Tracking" section

#### Daily Closing
- [ ] AI prompt: Compare `next_action` to completed items
- [ ] AI prompt: Suggest updating `next_action` for tasks where action was completed
- [ ] AI prompt: Flag tasks where `next_action_due` passed without completion
- [ ] AI prompt: Suggest updating `blocked_expected` dates

#### Weekly Review
- [ ] Summarize tasks by blocking status
- [ ] Show tasks where `blocked_expected` passed without resolution
- [ ] Highlight completed `next_action` items as wins

### 3.2 Local Scripts

**File:** `scripts/logbook-local.py`

**Changes:**
- [ ] Update `read_tasks()` to parse new fields
- [ ] Update AI prompts to match GitHub Actions changes
- [ ] Add `next_action_due` to task context passed to AI
- [ ] Filter blocked tasks separately in focus recommendations

---

## Phase 4: Validation & Sync

### 4.1 Validation Checklist

- [ ] All 9 tasks have valid `next_action` (or are blocked)
- [ ] All started tasks have `next_action_due`
- [ ] All blocked tasks have `blocked_type` and `blocked_by`
- [ ] No `status: ip` remaining (normalized to `s`)
- [ ] AGENTS.md matches between public and private repos
- [ ] Workflows work with sample task data

### 4.2 Repository Sync

1. Update public repo (`personal-os-public`)
2. Copy changes to private repo (`my-personal-os-new`)
3. Copy changes to personal-os/personal-os (if separate)
4. Commit and push all repos

---

## Phase 5: Future Work (Deferred)

### P0/P1/P2/P3 Model Refinement

**Issue:** Current model conflates:
- **Criticality** (P0 = critical to goals)
- **Urgency** (P0 = do today)

**Proposed Resolution Options:**

1. **Keep Priority as Criticality, Use Due Dates for Urgency**
   - P0 = Critical to quarterly goals
   - P1 = Important but not critical
   - `next_action_due` = When to actually do it

2. **Rename to Avoid Confusion**
   - C0/C1/C2/C3 for Criticality
   - Use `next_action_due` as the "when" signal

3. **Hybrid Model**
   - Priority = Criticality
   - Add `urgency` field (high/medium/low)
   - AI combines both for recommendations

**To Do:** Create separate task to evaluate and decide on model refinement.

---

## Execution Order

1. ✅ Create this plan document
2. 🔲 Update AGENTS.md (public repo)
3. 🔲 Update core/templates/CLAUDE.md
4. 🔲 Migrate 9 active tasks
5. 🔲 Update daily-briefing.yml
6. 🔲 Update daily-closing.yml
7. 🔲 Update weekly-review.yml
8. 🔲 Update logbook-local.py
9. 🔲 Sync to private repo
10. 🔲 Create task for P0-P3 model refinement

