# Tasks

Your personal task files live here. Each task is a markdown file with YAML frontmatter containing metadata like priority, status, and category.

This directory is gitignored—your tasks stay private and local.

## Creating Tasks

Tasks are created automatically when you say "process my backlog" to your AI assistant. You can also create them manually using the template in `examples/example_task.md`.

## Task Structure

```yaml
---
title: Task name
category: technical|outreach|research|writing|admin|personal|other
priority: P0|P1|P2|P3
status: n  # n=not_started, s=started, b=blocked, d=done
created_date: YYYY-MM-DD
---
```

See `examples/example_task.md` for a complete template.
