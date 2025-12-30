# Personal OS - Product Requirements Document

**Version:** 1.0  
**Last Updated:** 2024-12-30

---

## Problem Statement

### The Core Challenge

Knowledge workers managing multiple tools (Slack, Jira, Confluence, calendars, documents) struggle to:
1. **Keep track of deliveries** in a timely manner with comprehensive context
2. **Maintain visibility** of work status to stakeholders
3. **Reduce context-switching overhead** between fragmented tools
4. **Compile evidence** for performance reviews efficiently

### Pain Points

| Pain Point | Description | Impact |
|------------|-------------|--------|
| **Scattered context** | Information lives in 5+ tools | Hours lost context-switching |
| **Stale updates** | External tools (Jira) not updated | Appears disorganized to others |
| **Manual evidence gathering** | Fetching updates from multiple sources | 5-10 minutes per update |
| **Performance review burden** | Compiling year's achievements | Days of effort at year-end |
| **Inconsistent updates** | Updates only happen "when remembered" | Lost track of deliveries |

### Who Experiences This

- **Product Managers** juggling multiple initiatives
- **Engineering Managers** coordinating teams
- **Individual Contributors** with cross-functional work
- **Anyone** whose work spans multiple tools and stakeholders

---

## Opportunity

### Core Insight

> "I want complexity being taken out of my hands on gathering updates, but I want control to review them to ensure relevant updates."

The opportunity is to **automate the tedious data gathering** while **preserving human judgment** for what gets shared.

### Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Status check response time | < 30 seconds | User can answer "Where are we on X?" |
| Jira sync effort | Near-zero | Updates suggested, user just approves |
| Performance review prep | < 1 hour | Auto-compiled evidence from year's tasks |
| Context consistency | 100% | All task updates have linked evidence |

---

## User Stories

### Daily Workflow

#### US-1: Morning Focus
> "As a knowledge worker, I want to see what I should focus on today, so I start my day with clarity."

**Acceptance Criteria:**
- [ ] Shows 2-3 focus items based on `next_action_due`
- [ ] Excludes blocked tasks from focus
- [ ] Shows blocked tasks separately with follow-up dates
- [ ] Surfaces overdue items as alerts

#### US-2: End-of-Day Sync
> "As a knowledge worker, I want suggested Jira updates based on my day's activity, so I don't have to manually compile updates."

**Acceptance Criteria:**
- [ ] Compares morning state to evening state
- [ ] Generates Jira comment suggestions in standard format
- [ ] User can approve/reject each update
- [ ] Approved updates execute automatically

#### US-3: Status Check
> "As a stakeholder-facing worker, I want to answer 'Where are we on X?' in 30 seconds."

**Acceptance Criteria:**
- [ ] Query matches to relevant task(s)
- [ ] Shows current status, next action, last updates
- [ ] Links to evidence (Jira, Slack, Confluence)
- [ ] Concise enough to relay verbally

### Task Management

#### US-4: Task Tracking
> "As a knowledge worker, I want to track my work locally with rich context, so I have a single source of truth."

**Acceptance Criteria:**
- [ ] Task files include all relevant metadata (Schema v2.0)
- [ ] Progress log captures updates over time
- [ ] Links to external resources (Jira, Confluence)
- [ ] Easy to query and filter

#### US-5: Blocked Task Handling
> "As a project owner, I want blocked tasks tracked separately with follow-up dates, so nothing falls through the cracks."

**Acceptance Criteria:**
- [ ] Blocked tasks have `blocked_by` and `blocked_expected`
- [ ] Not surfaced in daily focus
- [ ] Reminder when follow-up date arrives
- [ ] Easy to unblock and resume

### Reflection & Review

#### US-6: Weekly Review
> "As someone with multiple initiatives, I want a weekly summary of what was delivered, so I can share progress with my manager."

**Acceptance Criteria:**
- [ ] Lists completed tasks with evidence
- [ ] Shows goal progress
- [ ] Identifies patterns (velocity, blockers)
- [ ] Generates shareable summary

#### US-7: Performance Evidence
> "As an employee in performance review season, I want my achievements compiled automatically, so review prep takes hours not days."

**Acceptance Criteria:**
- [ ] Year's deliveries organized by category
- [ ] Mapped to competencies/expectations
- [ ] Includes evidence links
- [ ] Draft generated for review system

---

## Solution Overview

### Multi-Agent Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR AGENT                          │
│  • Time-based triggers (8:30 AM, 5:50 PM, Friday 4 PM)          │
│  • Event-based triggers (user prompts)                           │
└───────────────────────────┬──────────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
   │   CONTEXT   │──▶│  ANALYZER   │──▶│  WORKFLOW   │
   │   GATHERER  │   │             │   │             │
   └─────────────┘   └─────────────┘   └─────────────┘
```

### Agent Responsibilities

| Agent | Purpose | Type |
|-------|---------|------|
| **Orchestrator** | Coordinates triggers and routing | Hybrid |
| **Context Gatherer** | Fetches Slack, Jira, Confluence, Git | Code-based |
| **Analyzer** | Validates priorities, suggests changes | LLM-based |
| **Workflow** | Generates briefings, closings | LLM-based |
| **Reflection** | Weekly/quarterly reviews | LLM-based |

### Task Schema (v2.0)

```yaml
---
title: [Task name]
priority: [P0|P1|P2|P3]
status: [n|s|b|d]  # not_started | started | blocked | done

# Focus
next_action: [Single action with earliest due date]
next_action_due: [YYYY-MM-DD]

# Blocking (when status: b)
blocked_type: [external|dependency|decision]
blocked_by: [Who/what is blocking]
blocked_expected: [YYYY-MM-DD]

# Dates
due_date: [YYYY-MM-DD]
---
```

---

## Non-Goals (Out of Scope)

| Item | Reason |
|------|--------|
| Real-time Slack monitoring | Privacy concerns, company policies |
| Auto-posting without approval | User maintains control |
| Google Docs integration | No robust MCP available yet |
| Team-wide deployment | Personal tool first |

---

## Implementation Phases

| Phase | Status | Focus |
|-------|--------|-------|
| 1. Foundation | ✅ Complete | Task files, workflows, Slack integration |
| 2. Schema v2.0 | ✅ Complete | next_action, blocked fields |
| 3. Multi-Agent | ✅ Complete | Specialized agents |
| 4. Integration | 🔲 Planned | Connect agents to scripts |

---

## Related Documents

- `SPEC-agent-architecture.md` — Technical architecture
- `schema-v2-update-plan.md` — Schema migration details
- `implementation-plan-v2.md` — Implementation roadmap

---

*This PRD is a living document. Update as requirements evolve.*

