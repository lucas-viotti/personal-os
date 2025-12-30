# Reflection Agent

**Purpose:** Provide periodic reflection on progress toward goals.

**Version:** 1.0  
**Last Updated:** 2024-12-30

---

## Overview

The Reflection Agent is an **LLM-based agent** that produces weekly, monthly, quarterly, and annual reviews. It connects task completion to broader goals and compiles evidence for performance reviews.

---

## Responsibilities

| Responsibility | Description |
|----------------|-------------|
| **Weekly Review** | What delivered vs. planned this week |
| **Goal Progress** | Track quarterly/annual objectives |
| **Initiative Health** | Status of each major initiative |
| **Performance Evidence** | Compile achievements for reviews |
| **Trend Analysis** | Identify patterns (blockers, velocity) |

---

## Time Horizons

| Horizon | Trigger | Focus | Output |
|---------|---------|-------|--------|
| **Weekly** | Friday 4 PM | Delivered this week, plan next week | Share with team/manager |
| **Monthly** | 1st of month | Initiative progress, recurring blockers | Personal review |
| **Quarterly** | End of Q | OKR progress, adjustments | Goal recalibration |
| **Annual** | December | Performance review evidence | Qulture Rocks input |

---

## Input Schema

```yaml
# Received from Orchestrator
input:
  reflection_type: "weekly" | "monthly" | "quarterly" | "annual"
  
  period:
    start: "2024-12-23T00:00:00Z"
    end: "2024-12-30T23:59:59Z"
    
  context: <context_object>  # From Context Gatherer (period-specific)
  analysis: <analysis_object>  # From Analyzer
  
  # Additional inputs for reflection
  archived_tasks: <list of tasks archived in period>
  goals: <from GOALS.md>
  
  # For annual reflection
  performance_context:
    manager_expectations: <from Knowledge/>
    previous_self_assessment: <if available>
```

---

## Weekly Review

### Logic

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

### Output Schema

```yaml
weekly_review:
  week: "Dec 23-30, 2024"
  period:
    start: "2024-12-23"
    end: "2024-12-30"
  
  # What was accomplished
  delivered:
    - task: "002-collections-loan-servicing-split"
      title: "Collections Policy Split"
      completed: "2024-12-29"
      time_in_progress: "12 days"
      evidence:
        - type: "confluence"
          detail: "Policy pages updated and published"
        - type: "jira"
          detail: "MRC-1911 marked Done"
      goal_alignment: "Policies and procedures for Troy"
      impact: "Unblocks compliance team for Q1 audit"
      
  # What's still in progress
  in_progress:
    - task: "001-beta-rollout-scope-document"
      title: "Beta Rollout Scope Document"
      priority: "P0"
      planned_completion: "2026-01-16"
      this_week: "Completed jira-test-cases review"
      next_week: "Stakeholder alignment meetings"
      on_track: true
      
    - task: "009-late-fee-penalty-apr-decision"
      title: "Late Fee & Penalty APR Decisions"
      priority: "P0"
      planned_completion: "2026-01-31"
      this_week: "Forum postponed"
      next_week: "Prepare materials when rescheduled"
      on_track: true
      risk: "Forum date still TBD"
      
  # Blocked items
  blocked:
    - task: "004-cardholder-agreement-followup"
      title: "Cardholder Agreement V2"
      blocked_since: "2024-12-11"
      blocked_by: "Lead Bank"
      blocked_duration: "19 days"
      follow_up: "2026-01-10"
      escalation_needed: false
      
  # Goal progress tracking
  goal_progress:
    - goal: "Prepare beta rollout launch for the US"
      source: "GOALS.md"
      status: "On track"
      percentage: 65
      key_milestones:
        - date: "2026-01-09"
          milestone: "Draft ready for leadership"
          status: "on_track"
        - date: "2026-01-16"
          milestone: "Final version"
          status: "on_track"
      this_week_contribution: "Completed jira scope review"
      blockers: []
      
    - goal: "Complete all CC policies by Q1"
      source: "GOALS.md"
      status: "At risk"
      percentage: 40
      key_milestones:
        - date: "2026-01-31"
          milestone: "Cardholder Agreement finalized"
          status: "at_risk"
      this_week_contribution: "Collections policy completed"
      blockers:
        - "Lead Bank response pending"
      
  # Metrics
  metrics:
    tasks_completed: 3
    tasks_started: 2
    tasks_blocked: 2
    p0_tasks_active: 2
    p1_tasks_active: 4
    avg_time_in_progress: "8 days"
    blockers_resolved: 1
    blockers_new: 0
    
  # Patterns and insights
  insights:
    - type: "velocity"
      observation: "3 tasks completed - above average"
    - type: "blocker_pattern"
      observation: "External dependencies account for 67% of blocked tasks"
    - type: "focus_drift"
      observation: "No P0 tasks completed; focus on unblocking needed"
      
  # Next week planning
  next_week_focus:
    - priority: "P0"
      action: "Resolve stakeholder questions for beta scope"
      deadline: "2026-01-06"
    - priority: "P0"
      action: "Follow up on Lead Bank (Jan 10)"
      deadline: "2026-01-10"
    - priority: "P1"
      action: "Prepare for Late Fee decision forum"
      deadline: "TBD"
      
  # Shareable summary (for manager/team)
  shareable_summary: |
    ## Week of Dec 23-30, 2024
    
    **Delivered:**
    - ✅ Collections Policy Split (MRC-1911)
    
    **In Progress:**
    - 🟡 Beta Rollout Scope - on track for Jan 16
    - 🟡 Late Fee Decisions - forum postponed, monitoring
    
    **Blocked:**
    - 🔴 Cardholder Agreement - awaiting Lead Bank (follow up Jan 10)
    
    **Next Week:**
    - Stakeholder alignment for beta scope
    - Lead Bank follow-up
```

---

## Monthly Review

### Logic

```
INPUT:
- Weekly reviews from the month
- Archived tasks (completed this month)
- Goal progress
- Recurring blockers

1. Aggregate weekly deliveries
2. Calculate monthly velocity
3. Identify recurring blocker patterns
4. Assess initiative health
5. Flag at-risk goals

OUTPUT: Monthly summary for personal review
```

### Output Schema

```yaml
monthly_review:
  month: "December 2024"
  
  summary:
    tasks_completed: 8
    tasks_started: 5
    net_tasks: +3  # completed - created
    
  deliveries:
    - task: "002-collections-loan-servicing-split"
      week: "Dec 23-30"
      impact: "Unblocked compliance audit"
    # ... more deliveries
    
  initiative_health:
    - initiative: "Troy Beta Rollout"
      status: "green"
      tasks_completed: 3
      tasks_remaining: 2
      on_track_for_deadline: true
      
    - initiative: "CC Policies"
      status: "yellow"
      tasks_completed: 1
      tasks_remaining: 3
      on_track_for_deadline: false
      risk: "Lead Bank dependency"
      
  recurring_blockers:
    - blocker: "External legal review"
      occurrences: 3
      avg_resolution_time: "14 days"
      mitigation: "Start legal engagement earlier"
      
  goal_adjustments:
    - goal: "Complete CC policies by Q1"
      original_target: "2026-03-31"
      suggested_target: "2026-04-15"
      reason: "Lead Bank delays"
```

---

## Quarterly Review

### Logic

```
INPUT:
- Monthly reviews from the quarter
- OKRs/goals
- Performance expectations

1. Aggregate quarterly achievements
2. Calculate OKR progress percentage
3. Identify goal gaps
4. Suggest Q+1 adjustments

OUTPUT: OKR review + goal recalibration
```

---

## Annual Review

### Logic

```
INPUT:
- All quarterly reviews
- GOALS.md (annual goals)
- Manager expectations (from Knowledge/)
- Task archive (full year)

1. Compile all deliveries by category
2. Map deliveries to competencies/expectations
3. Calculate impact metrics
4. Generate performance review draft

OUTPUT: Self-assessment draft for Qulture Rocks
```

### Output Schema

```yaml
annual_review:
  year: 2024
  
  achievements_by_category:
    - category: "Product Delivery"
      items:
        - "Led Troy Beta rollout scope definition"
        - "Completed 12 CC policy documents"
        - "Established Jira workflow standards"
      evidence:
        - jira_cards: ["MRC-3266", "MRC-1911", "MRC-1912"]
        - confluence_pages: 15
        - stakeholder_alignment_sessions: 8
        
    - category: "Cross-functional Leadership"
      items:
        - "Coordinated with Legal, Compliance, Engineering"
        - "Facilitated 5 decision forums"
      evidence:
        - slack_threads_led: 23
        - meetings_facilitated: 5
        
    - category: "Process Improvement"
      items:
        - "Built Personal OS task management system"
        - "Reduced status update time by 80%"
      evidence:
        - github_commits: 150
        - automation_hours_saved: "~2h/week"
        
  metrics:
    tasks_completed: 87
    initiatives_delivered: 4
    blockers_resolved: 34
    avg_task_completion_time: "6 days"
    
  goal_achievement:
    - goal: "Prepare US beta launch"
      target: "Q4 2024"
      achieved: true
      evidence: "Beta launched Dec 15"
      
    - goal: "Complete CC policy framework"
      target: "Q4 2024"
      achieved: "partial"
      percentage: 80
      evidence: "4/5 policies completed; 1 blocked by external"
      
  self_assessment_draft: |
    [Generated draft for Qulture Rocks based on evidence above]
```

---

## LLM Prompt Template

### Weekly Review Prompt

```markdown
You are the Reflection Agent generating a Weekly Review.

## Period
{week start} to {week end}

## Context
{context from Context Gatherer - last 7 days}

## Completed Tasks
{archived tasks from this week}

## Active Tasks
{current task list with frontmatter}

## Goals
{from GOALS.md}

## Instructions
1. List all completed tasks with evidence
2. Summarize progress on in-progress tasks
3. Note blocked items and durations
4. Map completions to goals in GOALS.md
5. Calculate metrics (completed, started, blocked)
6. Identify patterns (velocity, blocker types)
7. Suggest next week's focus (top 3)
8. Generate shareable summary for manager

## Output Format
Return YAML matching the weekly_review schema.
```

---

## Acceptance Criteria

### Weekly Review
- [ ] Lists completed tasks with evidence (Jira, Confluence, Slack)
- [ ] Shows in-progress tasks with this_week/next_week
- [ ] Lists blocked items with duration and follow-up dates
- [ ] Maps progress to GOALS.md objectives
- [ ] Calculates metrics (completed, started, blocked)
- [ ] Identifies patterns and insights
- [ ] Suggests next week's focus
- [ ] Generates shareable summary

### Monthly Review
- [ ] Aggregates weekly deliveries
- [ ] Shows initiative health status (green/yellow/red)
- [ ] Identifies recurring blocker patterns
- [ ] Suggests goal adjustments if needed

### Quarterly Review
- [ ] Calculates OKR progress percentage
- [ ] Identifies goal gaps
- [ ] Suggests next quarter adjustments

### Annual Review
- [ ] Compiles year's achievements by category
- [ ] Maps to competencies/expectations
- [ ] Generates self-assessment draft
- [ ] Includes evidence links

---

## Related Agents

| Agent | Relationship |
|-------|--------------|
| **Orchestrator** | Calls Reflection for weekly/monthly/quarterly |
| **Context Gatherer** | Provides period-specific context |
| **Analyzer** | Provides analysis for deeper insights |
| **Workflow** | Handles daily operations (separate) |

---

## Configuration

```yaml
# In config.yaml
reflection:
  weekly:
    trigger_time: "16:00"
    trigger_day: "Friday"
    include_shareable_summary: true
    
  monthly:
    trigger_day: 1  # 1st of month
    include_goal_adjustments: true
    
  quarterly:
    # End of March, June, September, December
    months: [3, 6, 9, 12]
    
  annual:
    trigger_month: 12
    include_performance_draft: true
    performance_template: "Knowledge/performance-template.md"
```

---

*See `../docs/SPEC-agent-architecture.md` for full system architecture.*

