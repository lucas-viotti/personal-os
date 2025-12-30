#!/usr/bin/env python3
"""
Agent Orchestrator for Personal OS

This script coordinates the multi-agent system for generating daily briefings,
closings, and weekly reviews. It reads agent instructions from markdown files
and calls the LLM in sequence.

Agent Flow:
  Orchestrator → Context Gatherer → Analyzer → Workflow/Reflection

Usage:
  python agent_orchestrator.py daily-briefing
  python agent_orchestrator.py daily-closing
  python agent_orchestrator.py weekly-review
"""

import os
import sys
import json
import re
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

# Configuration
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
AGENTS_DIR = PROJECT_ROOT / "core" / "agents"
TASKS_DIR = PROJECT_ROOT / "Tasks"
KNOWLEDGE_DIR = PROJECT_ROOT / "Knowledge"

# LLM Configuration (from environment)
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.openai.com")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Cache Configuration
CONTEXT_CACHE_TTL_MINUTES = int(os.getenv("CONTEXT_CACHE_TTL", "25"))


def load_agent_instructions(agent_name: str) -> str:
    """Load agent instructions from markdown file."""
    agent_file = AGENTS_DIR / f"{agent_name}.md"
    if not agent_file.exists():
        raise FileNotFoundError(f"Agent file not found: {agent_file}")
    
    content = agent_file.read_text()
    
    # Extract the main content (skip frontmatter-like sections)
    # Keep everything after the first --- separator if present
    if content.startswith("#"):
        return content
    
    # If there's YAML-like frontmatter, skip it
    parts = content.split("---", 2)
    if len(parts) >= 3:
        return parts[2].strip()
    
    return content


def load_prioritization_rules() -> str:
    """Load user's prioritization rules."""
    rules_file = KNOWLEDGE_DIR / "prioritization-rules.md"
    if rules_file.exists():
        return rules_file.read_text()
    return "No prioritization rules configured."


def read_tasks() -> Dict[str, Any]:
    """Read all tasks and categorize them."""
    tasks = {
        "all_tasks": [],
        "actions_due_today": [],
        "actions_due_this_week": [],
        "blocked_tasks": [],
        "p0_tasks": [],
        "p1_tasks": [],
    }
    
    if not TASKS_DIR.exists():
        return tasks
    
    today = datetime.now().date()
    week_end = today + timedelta(days=7)
    
    for task_file in TASKS_DIR.glob("*.md"):
        content = task_file.read_text()
        
        # Parse frontmatter
        frontmatter = parse_frontmatter(content)
        if not frontmatter:
            continue
        
        task_data = {
            "file": task_file.name,
            "title": frontmatter.get("title", task_file.stem),
            "priority": frontmatter.get("priority", "P2"),
            "status": frontmatter.get("status", "n"),
            "due_date": frontmatter.get("due_date"),
            "next_action": frontmatter.get("next_action"),
            "next_action_due": frontmatter.get("next_action_due"),
            "blocked_by": frontmatter.get("blocked_by"),
            "blocked_type": frontmatter.get("blocked_type"),
            "blocked_expected": frontmatter.get("blocked_expected"),
        }
        
        tasks["all_tasks"].append(task_data)
        
        # Categorize
        status = task_data["status"]
        priority = task_data["priority"]
        
        # Blocked tasks
        if status == "b":
            tasks["blocked_tasks"].append(task_data)
            continue
        
        # Done tasks - skip
        if status == "d":
            continue
        
        # Parse next_action_due
        next_action_due = None
        if task_data["next_action_due"]:
            try:
                next_action_due = datetime.strptime(
                    str(task_data["next_action_due"]), "%Y-%m-%d"
                ).date()
            except ValueError:
                pass
        
        # Actions due today (or overdue)
        if next_action_due and next_action_due <= today:
            tasks["actions_due_today"].append(task_data)
        # Actions due this week (but not today)
        elif next_action_due and next_action_due <= week_end:
            tasks["actions_due_this_week"].append(task_data)
        
        # Priority categorization (excluding blocked)
        if priority == "P0":
            tasks["p0_tasks"].append(task_data)
        elif priority == "P1":
            tasks["p1_tasks"].append(task_data)
    
    return tasks


def parse_frontmatter(content: str) -> Optional[Dict[str, Any]]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return None
    
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    
    frontmatter_text = parts[1].strip()
    result = {}
    
    for line in frontmatter_text.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            
            # Remove quotes
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            
            # Handle empty values
            if value == "" or value == "null":
                value = None
            
            result[key] = value
    
    return result


def call_llm(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1500,
    temperature: float = 0.5
) -> str:
    """Call the LLM API with given prompts."""
    if not LLM_API_KEY:
        return "Error: LLM_API_KEY not configured"
    
    url = f"{LLM_API_URL}/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        return f"Error calling LLM: {str(e)}"
    except (KeyError, IndexError) as e:
        return f"Error parsing LLM response: {str(e)}"


def run_context_gatherer(context_period: str = "24h") -> Dict[str, Any]:
    """
    Context Gatherer Agent
    
    Collects data from various sources and structures it for other agents.
    Note: Slack/Jira/Confluence fetching is done by GitHub Actions shell scripts.
    This function structures the local task data.
    """
    print("[Context Gatherer] Reading local tasks...")
    
    tasks = read_tasks()
    prioritization_rules = load_prioritization_rules()
    
    # Format for downstream agents
    context = {
        "timestamp": datetime.now().isoformat(),
        "context_period": context_period,
        "local_tasks": tasks,
        "prioritization_rules": prioritization_rules,
        "today": datetime.now().strftime("%A, %B %d, %Y"),
    }
    
    return context


def run_analyzer(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyzer Agent
    
    Validates priorities, checks for issues, and flags items needing attention.
    """
    print("[Analyzer] Analyzing tasks...")
    
    analyzer_instructions = load_agent_instructions("analyzer")
    
    # Build analyzer prompt
    system_prompt = f"""You are the Analyzer Agent for Personal OS.

{analyzer_instructions}

Respond ONLY with valid JSON. No markdown, no explanation."""
    
    tasks = context["local_tasks"]
    
    user_prompt = f"""Analyze these tasks and return a JSON object with your findings.

TODAY: {context['today']}

TASKS DATA:
- Actions Due Today: {json.dumps(tasks['actions_due_today'], indent=2)}
- Actions Due This Week: {json.dumps(tasks['actions_due_this_week'], indent=2)}
- Blocked Tasks: {json.dumps(tasks['blocked_tasks'], indent=2)}
- P0 Tasks: {json.dumps(tasks['p0_tasks'], indent=2)}
- P1 Tasks: {json.dumps(tasks['p1_tasks'], indent=2)}

PRIORITIZATION RULES:
{context['prioritization_rules']}

Return JSON with this structure:
{{
  "alerts": [
    {{"type": "overdue_action", "task": "...", "message": "..."}},
    {{"type": "priority_mismatch", "task": "...", "message": "..."}}
  ],
  "recommendations": [
    {{"task": "...", "action": "...", "reason": "..."}}
  ],
  "validation": {{
    "tasks_analyzed": 0,
    "issues_found": 0,
    "blocked_count": 0
  }}
}}"""
    
    response = call_llm(system_prompt, user_prompt, max_tokens=1000, temperature=0.3)
    
    # Try to parse JSON from response
    try:
        # Extract JSON if wrapped in markdown code block
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
        if json_match:
            response = json_match.group(1)
        
        analysis = json.loads(response)
    except json.JSONDecodeError:
        analysis = {
            "alerts": [],
            "recommendations": [],
            "validation": {"error": "Failed to parse analyzer response"},
            "raw_response": response[:500]
        }
    
    return analysis


def run_workflow_agent(
    context: Dict[str, Any],
    analysis: Dict[str, Any],
    workflow_type: str = "daily-briefing"
) -> str:
    """
    Workflow Agent
    
    Generates the final user-facing output (Slack message).
    """
    print(f"[Workflow Agent] Generating {workflow_type}...")
    
    workflow_instructions = load_agent_instructions("workflow")
    
    # Build workflow prompt based on type
    if workflow_type == "daily-briefing":
        output_format = """Generate a Slack daily briefing message with this structure:

*☀️ Daily Briefing — [TODAY]*

*🎯 Actions Due Today*
[List actions with next_action_due = TODAY or OVERDUE]
• [next_action] — _[task name]_
[If none: "_No actions due today._"]

*📅 Actions Due This Week*
[List actions due within 7 days, grouped by priority]
• 🔴 [P0 action] — _[task name]_ (due [date])
• 🟡 [P1 action] — _[task name]_ (due [date])
[If none, skip this section]

*⏳ Tracking (Blocked)*
• [task name] — _blocked by: [who/what]_
[If none, skip this section]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

*💡 AI Focus Recommendation*
Based on your deadlines, priorities, and recent activity:

• 🔴 *[next_action]* — [task name]
_Due: [date]. [1-2 sentences explaining why prioritized.]_

• 🟡 *[next_action]* — [task name]
_Due: [date]. [1-2 sentences with reasoning.]_

_📊 See thread for detailed activity (Jira & Confluence) →_

RULES:
- Max 2500 characters
- Use Slack mrkdwn: *bold*, _italic_, • for bullets
- Max 2-3 focus recommendations
- Skip empty sections"""

    elif workflow_type == "daily-closing":
        output_format = """Generate a Slack daily closing message with this structure:

*🌆 Daily Closing — [TODAY]*

*📈 Today's Progress*
[Summarize what was accomplished based on task changes]

*📋 Task Status*
*🎯 Actions Due Today*:
[Status of today's actions - completed or not]

*📅 Actions Due This Week*:
[Brief status of upcoming items]

*💡 Suggested Task Updates*
[For each task that had progress, suggest Jira updates]
• *[Task name]*: [Suggested update]

_Update Jira cards to reflect today's progress._

RULES:
- Max 2500 characters
- Use Slack mrkdwn
- Focus on actionable updates"""

    else:  # weekly-review
        output_format = """Generate a weekly review message."""
    
    system_prompt = f"""You are the Workflow Agent for Personal OS.

{workflow_instructions}

{output_format}"""
    
    tasks = context["local_tasks"]
    
    user_prompt = f"""Generate the {workflow_type} output.

TODAY: {context['today']}

CONTEXT DATA:
- Actions Due Today: {json.dumps(tasks['actions_due_today'], indent=2)}
- Actions Due This Week: {json.dumps(tasks['actions_due_this_week'], indent=2)}
- Blocked Tasks: {json.dumps(tasks['blocked_tasks'], indent=2)}
- All Tasks Count: {len(tasks['all_tasks'])}

ANALYZER FINDINGS:
{json.dumps(analysis, indent=2)}

PRIORITIZATION RULES:
{context['prioritization_rules']}

Generate the Slack message now. Keep it under 2500 characters."""
    
    return call_llm(system_prompt, user_prompt, max_tokens=1200, temperature=0.5)


def orchestrate(workflow_type: str) -> str:
    """
    Orchestrator Agent
    
    Coordinates the agent pipeline and returns the final output.
    """
    print(f"\n{'='*60}")
    print(f"[Orchestrator] Starting {workflow_type}")
    print(f"{'='*60}\n")
    
    # Determine context period based on workflow
    context_periods = {
        "daily-briefing": "24h",
        "daily-closing": "since_briefing",
        "weekly-review": "7d",
    }
    context_period = context_periods.get(workflow_type, "24h")
    
    # Step 1: Gather Context
    context = run_context_gatherer(context_period)
    print(f"[Orchestrator] Context gathered: {len(context['local_tasks']['all_tasks'])} tasks")
    
    # Step 2: Run Analyzer
    analysis = run_analyzer(context)
    alerts_count = len(analysis.get("alerts", []))
    print(f"[Orchestrator] Analysis complete: {alerts_count} alerts")
    
    # Step 3: Generate Output
    output = run_workflow_agent(context, analysis, workflow_type)
    print(f"[Orchestrator] Output generated: {len(output)} characters")
    
    print(f"\n{'='*60}")
    print(f"[Orchestrator] {workflow_type} complete")
    print(f"{'='*60}\n")
    
    return output


def enrich_slack_context(slack_messages: str) -> str:
    """
    Slack Enrichment Agent
    
    Takes raw Slack messages and generates a formatted, task-aware summary
    using the Context Gatherer and Workflow agents.
    """
    print(f"\n{'='*60}")
    print("[Orchestrator] Starting Slack Enrichment")
    print(f"{'='*60}\n")
    
    # Step 1: Gather local task context
    context = run_context_gatherer("24h")
    print(f"[Orchestrator] Context gathered: {len(context['local_tasks']['all_tasks'])} tasks")
    
    # Step 2: Use LLM to analyze Slack messages and link to tasks
    context_gatherer_instructions = load_agent_instructions("context-gatherer")
    
    system_prompt = f"""You are the Context Gatherer Agent for Personal OS, specialized in Slack message analysis.

{context_gatherer_instructions}

Your job is to:
1. Categorize Slack messages by topic/project
2. Extract action items from conversations
3. Identify which messages relate to known tasks
4. Highlight important decisions or updates

Output in Slack mrkdwn format (not markdown).
Use: *bold*, _italic_, • for bullets, no tables."""

    tasks_summary = "\n".join([
        f"- {t['title']} (P{t['priority'][-1] if t['priority'] else '?'}, {t['status']})"
        for t in context['local_tasks']['all_tasks'][:10]
    ])
    
    user_prompt = f"""Analyze these Slack messages and create a formatted summary.

TODAY: {context['today']}

KNOWN TASKS (for linking):
{tasks_summary}

RAW SLACK MESSAGES:
{slack_messages}

Generate a Slack-formatted summary with:
1. *Key Conversations Today* - grouped by topic
2. *Action Items* - extracted from messages
3. *Task-Related Updates* - link to known tasks where relevant

Use Slack mrkdwn:
- *bold* for headers and emphasis
- _italic_ for task names and secondary info
- • for bullet points
- No markdown tables (use bullets instead)

Keep under 1500 characters for Slack."""

    print("[Context Gatherer] Analyzing Slack messages...")
    enriched_summary = call_llm(system_prompt, user_prompt, max_tokens=800, temperature=0.5)
    
    print(f"[Orchestrator] Enrichment complete: {len(enriched_summary)} characters")
    print(f"{'='*60}\n")
    
    return enriched_summary


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python agent_orchestrator.py <workflow-type> [args]")
        print("  workflow-type: daily-briefing | daily-closing | weekly-review | slack-enrich")
        print("  For slack-enrich: provide path to file with raw Slack messages")
        sys.exit(1)
    
    workflow_type = sys.argv[1]
    valid_workflows = ["daily-briefing", "daily-closing", "weekly-review", "slack-enrich"]
    
    if workflow_type not in valid_workflows:
        print(f"Error: Invalid workflow type '{workflow_type}'")
        print(f"Valid types: {', '.join(valid_workflows)}")
        sys.exit(1)
    
    if workflow_type == "slack-enrich":
        # Read Slack messages from file or stdin
        if len(sys.argv) > 2:
            slack_file = Path(sys.argv[2])
            if slack_file.exists():
                slack_messages = slack_file.read_text()
            else:
                print(f"Error: File not found: {slack_file}")
                sys.exit(1)
        else:
            # Read from stdin
            print("Reading Slack messages from stdin...")
            slack_messages = sys.stdin.read()
        
        output = enrich_slack_context(slack_messages)
    else:
        output = orchestrate(workflow_type)
    
    # Output to stdout (for GitHub Actions to capture)
    print("\n--- OUTPUT ---")
    print(output)
    
    # Also save to file for debugging
    output_file = SCRIPT_DIR / ".agent-output.txt"
    output_file.write_text(output)
    print(f"\n[Saved to {output_file}]")


if __name__ == "__main__":
    main()

