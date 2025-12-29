# Prioritization Rules for AI Focus Recommendations

These rules guide how tasks are prioritized in daily briefings. Edit this file to customize your prioritization criteria.

---

## Stack Ranking (Highest to Lowest Priority)

### 1. 🚨 Hard Deadlines
- Tasks with imminent due dates (today or tomorrow)
- External commitments that cannot be rescheduled
- **Weight: Critical** — always surface these first

### 2. 🔗 Blocking Others
- Tasks that unblock teammates or cross-functional partners
- Approvals, reviews, or inputs others are waiting on
- **Weight: High** — delays compound across the team

### 3. 🎯 Strategic Goal Alignment
- Tasks directly tied to quarterly objectives or OKRs
- Work that moves key initiatives forward
- Reference `GOALS.md` for current strategic priorities
- **Weight: High** — ensures work matters

### 4. 📈 Momentum & Progress
- Tasks already in progress that are close to completion
- Quick wins that can be finished in <30 minutes
- Work that builds on recent activity (e.g., Jira updates, meetings)
- **Weight: Medium** — keeps energy and delivery flowing

### 5. ⚠️ Risk & Dependencies
- Tasks with external dependencies that could slip
- Work requiring stakeholder alignment before proceeding
- Items at risk of becoming blockers if delayed
- **Weight: Medium** — proactive risk management

### 6. 🧠 Cognitive Load Matching
- Complex tasks when energy is high (morning)
- Administrative tasks when energy is lower
- **Weight: Low** — nice-to-have optimization

---

## How to Use This File

1. **Stack Ranking**: Higher-numbered criteria override lower ones
2. **Customize**: Add, remove, or reorder criteria based on your work style
3. **Context Matters**: The AI will weigh these against your current task list, recent activity, and goals

## Example Priority Decision

Given two tasks:
- Task A: P1, no deadline, aligned with Q1 goal
- Task B: P0, due tomorrow, blocks design team

**Result**: Task B wins (Hard Deadline + Blocking Others > Goal Alignment)

---

*Customize this file to match your prioritization style!*

