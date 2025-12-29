# Archive Tasks Workflow

Move completed tasks from `Tasks/` to `Archive/` organized by completion month.

## When to Use

- Weekly review to clean up completed work
- When saying "archive my completed tasks" or "archive done tasks"
- To keep `Tasks/` folder focused on active work only

## Archive Structure

```
Archive/
├── 2025-01/
│   └── completed-task-1.md
├── 2025-02/
│   └── completed-task-2.md
└── ...
```

## Steps

### 1. Identify Completed Tasks

Scan all files in `Tasks/` for tasks with `status: d` (done).

```yaml
# Tasks with this frontmatter are ready to archive
status: d  # done
```

### 2. Add Completion Date

If not already present, add `completed_date` to the frontmatter:

```yaml
---
title: Example Task
status: d
completed_date: 2025-01-15  # Add this if missing
---
```

### 3. Move to Archive

Move each completed task to `Archive/YYYY-MM/` based on its `completed_date`:

- Create the month folder if it doesn't exist
- Keep the original filename
- Preserve all task content

### 4. Confirm and Summarize

Present a summary:

```
## Archived Tasks

✅ Moved 3 tasks to Archive/2025-01/:
- task-001-feature-x.md
- task-005-bug-fix.md
- task-012-documentation.md

Tasks/ now contains 8 active tasks.
```

## Trigger Phrases

- "Archive my completed tasks"
- "Archive done tasks"
- "Move finished tasks to archive"
- "Clean up completed work"

## Notes

- Always confirm before archiving
- Tasks remain searchable in Archive/
- Use `git log` to see task history
- Monthly organization makes finding old tasks easy

