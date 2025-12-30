#!/usr/bin/env python3
"""
Logbook Local - Personal OS Daily/Weekly Reports with Full Slack Access

This script provides the same functionality as the GitHub Actions workflows,
but runs locally on your machine. This enables:
- Full Slack access via MCP OAuth tokens (no company restrictions)
- VPN/internal network access for Atlassian APIs
- Integration with local tools and credentials
- Git changes detection for task file updates

Usage:
    python logbook-local.py briefing   # Morning briefing
    python logbook-local.py closing    # End-of-day closing
    python logbook-local.py weekly     # Weekly review

Configuration:
    Copy .env.example to .env and fill in your credentials.
    See README in scripts/ folder for detailed setup.

For Slack MCP users:
    The script can read tokens from the Slack MCP OAuth flow.
    Set SLACK_MCP_TOKEN_PATH in .env to your MCP's token location.
"""

import os
import sys
import json
import base64
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
import urllib.request
import urllib.parse
import urllib.error

# ============================================================================
# CONFIGURATION
# ============================================================================

def load_config() -> Dict[str, str]:
    """Load configuration from environment variables or .env file."""
    config = {}
    
    # Try to load .env file (check scripts folder first, then repo root)
    possible_env_files = [
        Path(__file__).parent / ".env",           # scripts/.env
        Path(__file__).parent.parent / ".env",    # repo root/.env
    ]
    
    for env_file in possible_env_files:
        if env_file.exists():
            print(f"  Loading config from {env_file}")
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        config[key.strip()] = value.strip().strip('"').strip("'")
            break  # Use first found .env file
    
    # Environment variables override .env
    env_vars = [
        "ATLASSIAN_DOMAIN", "ATLASSIAN_EMAIL", "ATLASSIAN_API_TOKEN",
        "JIRA_PROJECT", "CONFLUENCE_SPACES",
        "LLM_API_URL", "LLM_API_KEY", "LLM_MODEL",
        "SLACK_BOT_TOKEN", "SLACK_CHANNEL_ID", "SLACK_USER_TOKEN",
        "SLACK_MCP_TOKEN_PATH", "TASKS_DIR"
    ]
    
    for var in env_vars:
        if os.environ.get(var):
            config[var] = os.environ[var]
    
    # Defaults
    config.setdefault("LLM_MODEL", "gpt-4o-mini")
    config.setdefault("TASKS_DIR", str(Path(__file__).parent.parent / "Tasks"))
    
    return config


# ============================================================================
# API HELPERS
# ============================================================================

def api_request(url: str, headers: Dict[str, str] = None, data: bytes = None, 
                method: str = "GET") -> Optional[Dict]:
    """Make an HTTP request and return JSON response."""
    try:
        req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        try:
            error_body = json.loads(e.read().decode())
            print(f"Error details: {error_body}")
        except:
            pass
        return None
    except Exception as e:
        print(f"Request error: {e}")
        return None


def get_slack_token(config: Dict[str, str]) -> Optional[str]:
    """Get Slack token with fallback chain."""
    # Option 1: Direct user token
    if config.get("SLACK_USER_TOKEN"):
        return config["SLACK_USER_TOKEN"]
    
    # Option 2: Read from Slack MCP token storage
    mcp_token_path = config.get("SLACK_MCP_TOKEN_PATH")
    if mcp_token_path:
        token_file = Path(mcp_token_path).expanduser()
        if token_file.exists():
            try:
                with open(token_file) as f:
                    token_data = json.load(f)
                    return token_data.get("access_token") or token_data.get("token")
            except Exception as e:
                print(f"Could not read MCP token: {e}")
    
    # Option 3: Try macOS keychain
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", "slack-mcp", "-w"],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except:
        pass
    
    # Option 4: Fallback to bot token
    return config.get("SLACK_BOT_TOKEN")


# ============================================================================
# DATA FETCHERS
# ============================================================================

def fetch_jira_activity(config: Dict[str, str], days: int = 1) -> Dict[str, Any]:
    """
    Fetch Jira activity with changelog and comments.
    Uses new POST API, filters by user, extracts actual changes.
    """
    domain = config.get("ATLASSIAN_DOMAIN")
    email = config.get("ATLASSIAN_EMAIL")
    token = config.get("ATLASSIAN_API_TOKEN")
    project = config.get("JIRA_PROJECT")
    
    if not all([domain, email, token, project]):
        return {"count": 0, "data": "_Jira not configured_", "detailed": "", "linked": "", "issues": []}
    
    print(f"  Fetching Jira activity for last {days} day(s)...")
    
    # Build JQL with user filter
    if days == 1:
        time_filter = "updated >= startOfDay()"
    else:
        time_filter = f"updated >= -{days}d"
    
    jql = f'project = {project} AND (assignee = "{email}" OR reporter = "{email}" OR watcher = "{email}") AND {time_filter} ORDER BY updated DESC'
    
    # Use new POST API endpoint
    url = f"https://{domain}/rest/api/3/search/jql?expand=changelog"
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
    
    payload = json.dumps({
        "jql": jql,
        "maxResults": 20,
        "fields": ["key", "summary", "status", "description", "comment"]
    }).encode()
    
    response = api_request(url, headers, payload, method="POST")
    
    if not response or "issues" not in response:
        return {"count": 0, "data": "_Could not fetch Jira data_", "detailed": "", "linked": "", "issues": []}
    
    # Parse each issue for actual changes
    today_start = (datetime.now() - timedelta(days=days)).isoformat()
    
    detailed_output = []
    linked_output = []
    actual_count = 0
    
    for issue in response.get("issues", []):
        key = issue.get("key", "")
        summary = issue.get("fields", {}).get("summary", "")
        status = issue.get("fields", {}).get("status", {}).get("name", "")
        
        # Extract today's changelog entries
        changes = []
        changelog = issue.get("changelog", {}).get("histories", [])
        for history in changelog:
            created = history.get("created", "")
            if created >= today_start:
                for item in history.get("items", []):
                    field = item.get("field", "")
                    from_val = item.get("fromString", "empty")
                    to_val = item.get("toString", "empty")
                    changes.append(f"  - {field}: {from_val} → {to_val}")
        
        # Extract today's comments
        comments = []
        comment_data = issue.get("fields", {}).get("comment", {}).get("comments", [])
        for comment in comment_data:
            created = comment.get("created", "")
            if created >= today_start:
                body = comment.get("body", {})
                # Extract text from ADF format
                text = ""
                try:
                    text = body.get("content", [{}])[0].get("content", [{}])[0].get("text", "")[:100]
                except:
                    text = "comment added"
                comments.append(f"  - Comment: \"{text}...\"")
        
        # Only include if there were actual changes
        if changes or comments:
            actual_count += 1
            
            detail = f"<https://{domain}/browse/{key}|{key}> - {summary}\n"
            detail += "\n".join(changes[:5])
            if comments:
                detail += "\n" + "\n".join(comments[:3])
            detailed_output.append(detail)
            
            linked_output.append(f"• <https://{domain}/browse/{key}|{key}>: {summary[:50]} [{status}]")
    
    print(f"  Found {actual_count} issues with actual changes")
    
    if actual_count == 0:
        return {
            "count": 0,
            "data": f"_No actual Jira changes in the last {days} day(s)_",
            "detailed": "_No actual Jira changes_",
            "linked": "_No Jira changes_",
            "issues": []
        }
    
    return {
        "count": actual_count,
        "data": "\n".join(linked_output),
        "detailed": "\n\n".join(detailed_output),
        "linked": "\n".join(linked_output),
        "issues": response.get("issues", [])
    }


def fetch_confluence_activity(config: Dict[str, str], days: int = 1) -> Dict[str, Any]:
    """Fetch Confluence activity for the specified time period."""
    domain = config.get("ATLASSIAN_DOMAIN")
    email = config.get("ATLASSIAN_EMAIL")
    token = config.get("ATLASSIAN_API_TOKEN")
    spaces = config.get("CONFLUENCE_SPACES", "").split(",")
    
    if not all([domain, email, token]) or not spaces[0]:
        return {"count": 0, "data": "_Confluence not configured_", "pages": []}
    
    print(f"  Fetching Confluence activity for last {days} day(s)...")
    
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
    
    since_date = (datetime.now() - timedelta(days=days)).isoformat()
    all_pages = []
    
    for space in spaces:
        space = space.strip()
        if not space:
            continue
            
        url = f"https://{domain}/wiki/rest/api/content?spaceKey={space}&expand=history.lastUpdated&limit=20"
        response = api_request(url, headers)
        
        if response and "results" in response:
            for page in response["results"]:
                updated = page.get("history", {}).get("lastUpdated", {}).get("when", "")
                if updated > since_date:
                    all_pages.append({
                        "title": page["title"],
                        "id": page["id"],
                        "url": f"https://{domain}/wiki{page.get('_links', {}).get('webui', '')}"
                    })
    
    count = len(all_pages)
    print(f"  Found {count} Confluence pages")
    
    if count == 0:
        data = f"_No Confluence edits in the last {days} day(s)_"
    else:
        data = "\n".join([f"• {p['title']}" for p in all_pages[:10]])
    
    return {"count": count, "data": data, "pages": all_pages}


def fetch_slack_activity(config: Dict[str, str], days: int = 1) -> Dict[str, Any]:
    """Fetch Slack activity using Search API."""
    token = get_slack_token(config)
    
    if not token:
        return {"count": 0, "data": "_Slack not configured_", "messages": []}
    
    print(f"  Fetching Slack activity for last {days} day(s)...")
    
    since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    query = f"from:me after:{since_date}"
    
    url = f"https://slack.com/api/search.messages?query={urllib.parse.quote(query)}&count=20"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = api_request(url, headers)
    
    if response and response.get("ok"):
        messages = response.get("messages", {}).get("matches", [])
        count = response.get("messages", {}).get("total", 0)
        
        print(f"  Found {count} Slack messages")
        
        if count == 0:
            data = f"_No Slack messages in the last {days} day(s)_"
        else:
            channels = {}
            for msg in messages[:20]:
                ch = msg.get("channel", {}).get("name", "DM")
                channels[ch] = channels.get(ch, 0) + 1
            
            data = f"*{count} messages* across {len(channels)} conversations"
            if channels:
                top_channels = sorted(channels.items(), key=lambda x: -x[1])[:5]
                data += "\n" + "\n".join([f"• #{ch}: {n} messages" for ch, n in top_channels])
        
        return {"count": count, "data": data, "messages": messages}
    
    if response and not response.get("ok"):
        error = response.get("error", "unknown")
        if error == "missing_scope":
            return {"count": 0, "data": "_Slack search requires user token_", "messages": []}
    
    return {"count": 0, "data": "_Could not fetch Slack data_", "messages": []}


def fetch_git_changes(config: Dict[str, str], days: int = 1) -> Dict[str, Any]:
    """Check for git changes to task files."""
    tasks_dir = Path(config.get("TASKS_DIR", "Tasks"))
    repo_root = tasks_dir.parent
    
    print(f"  Checking git changes for last {days} day(s)...")
    
    try:
        # Get today's date for filtering
        since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00")
        
        # Get list of changed files
        result = subprocess.run(
            ["git", "log", f"--since={since_date}", "--name-only", "--pretty=format:", "--", "Tasks/*.md", "Knowledge/*.md"],
            capture_output=True, text=True, cwd=str(repo_root)
        )
        
        changed_files = [f for f in result.stdout.strip().split("\n") if f.strip()]
        changed_files = list(set(changed_files))  # Dedupe
        
        if not changed_files:
            print("  No task files changed")
            return {"count": 0, "changes": "_No task files were modified._", "files": []}
        
        print(f"  Found {len(changed_files)} changed files")
        
        # Get diffs for each file
        changes_output = []
        for filepath in changed_files[:10]:
            filename = Path(filepath).stem
            
            # Get the diff
            diff_result = subprocess.run(
                ["git", "log", f"--since={since_date}", "-p", "--", filepath],
                capture_output=True, text=True, cwd=str(repo_root)
            )
            
            # Extract added lines
            added_lines = [line[1:] for line in diff_result.stdout.split("\n") 
                         if line.startswith("+") and not line.startswith("+++")][:10]
            
            if added_lines:
                changes_output.append(f"📝 *{filename}*:\n" + "\n".join([f"  + {line[:80]}" for line in added_lines[:5]]))
        
        return {
            "count": len(changed_files),
            "changes": "\n\n".join(changes_output) if changes_output else "_Files changed but no diff available_",
            "files": changed_files
        }
    
    except Exception as e:
        print(f"  Git error: {e}")
        return {"count": 0, "changes": "_Could not check git changes_", "files": []}


def read_tasks(config: Dict[str, str]) -> Dict[str, Any]:
    """Read tasks from the Tasks directory, grouped by status (Schema v2.0)."""
    tasks_dir = Path(config.get("TASKS_DIR", "Tasks"))
    today = datetime.now().strftime("%Y-%m-%d")
    
    if not tasks_dir.exists():
        return {
            "p0_count": 0, "p1_count": 0, "blocked_count": 0, "done_count": 0, "total": 0,
            "p0_not_started": "", "p0_in_progress": "",
            "p1_not_started": "", "p1_in_progress": "",
            "blocked_tasks": "", "task_details": "", "backlog_items": "✅ Clear!",
            "actions_due_today": ""
        }
    
    print("  Reading tasks...")
    
    tasks = {
        "P0": {"not_started": [], "in_progress": []},
        "P1": {"not_started": [], "in_progress": []},
        "blocked": [], "done": [], "all": []
    }
    actions_due_today = []
    
    for filepath in tasks_dir.glob("*.md"):
        if filepath.name == "README.md":
            continue
            
        with open(filepath) as f:
            content = f.read()
        
        # Parse frontmatter (Schema v2.0 fields)
        title = priority = status = due_date = ""
        next_action = next_action_due = ""
        blocked_type = blocked_by = blocked_expected = ""
        
        if content.startswith("---"):
            try:
                frontmatter = content.split("---")[1]
                for line in frontmatter.split("\n"):
                    line = line.strip()
                    if line.startswith("#"):  # Skip comments
                        continue
                    if line.startswith("title:"):
                        title = line.split(":", 1)[1].strip()
                    elif line.startswith("priority:"):
                        priority = line.split(":", 1)[1].strip()
                    elif line.startswith("status:"):
                        status = line.split(":", 1)[1].strip()
                    elif line.startswith("due_date:"):
                        due_date = line.split(":", 1)[1].strip()
                    elif line.startswith("next_action:"):
                        next_action = line.split(":", 1)[1].strip()
                    elif line.startswith("next_action_due:"):
                        next_action_due = line.split(":", 1)[1].strip()
                    elif line.startswith("blocked_type:"):
                        blocked_type = line.split(":", 1)[1].strip()
                    elif line.startswith("blocked_by:"):
                        blocked_by = line.split(":", 1)[1].strip()
                    elif line.startswith("blocked_expected:"):
                        blocked_expected = line.split(":", 1)[1].strip()
            except:
                pass
        
        if not title:
            title = filepath.stem.replace("-", " ").title()
        
        status_emoji = {"n": "🔴", "s": "🟡", "ip": "🟡", "b": "🟠", "d": "✅"}.get(status, "⚪")
        status_text = {"n": "Not Started", "s": "In Progress", "ip": "In Progress", 
                       "b": "Blocked", "d": "Done"}.get(status, "Unknown")
        
        task_info = {
            "title": title, "priority": priority, "status": status,
            "emoji": status_emoji, "status_text": status_text,
            "due_date": due_date, "content": content, "filepath": str(filepath),
            "next_action": next_action, "next_action_due": next_action_due,
            "blocked_type": blocked_type, "blocked_by": blocked_by, 
            "blocked_expected": blocked_expected
        }
        
        tasks["all"].append(task_info)
        
        # Track actions due today or overdue (Schema v2.0 feature)
        if next_action_due and next_action_due <= today and status not in ["b", "d"]:
            actions_due_today.append({
                "priority": priority,
                "next_action": next_action,
                "title": title,
                "next_action_due": next_action_due
            })
        
        # Group by priority and status (skip blocked from active lists)
        if status == "b":
            tasks["blocked"].append(task_info)
        elif status == "d":
            tasks["done"].append(task_info)
        elif priority == "P0":
            if status == "n":
                tasks["P0"]["not_started"].append(task_info)
            elif status in ["s", "ip"]:
                tasks["P0"]["in_progress"].append(task_info)
        elif priority == "P1":
            if status == "n":
                tasks["P1"]["not_started"].append(task_info)
            elif status in ["s", "ip"]:
                tasks["P1"]["in_progress"].append(task_info)
    
    def format_task_list(task_list):
        return "\n".join([f"• {t['title']}" for t in task_list])
    
    def format_tasks_detailed(task_list):
        return "\n".join([f"• {t['emoji']} [{t['priority']}] {t['title']} — {t['status_text']}" for t in task_list])
    
    def format_blocked_tasks(task_list):
        """Format blocked tasks with blocked_by info (Schema v2.0)."""
        lines = []
        for t in task_list:
            line = f"• {t['title']}"
            if t.get('blocked_by'):
                line += f" — _blocked by: {t['blocked_by']}_"
            if t.get('blocked_expected'):
                line += f" (check {t['blocked_expected']})"
            lines.append(line)
        return "\n".join(lines)
    
    def format_actions_due_today(actions):
        """Format actions due today/overdue (Schema v2.0)."""
        return "\n".join([
            f"• {a['priority']}: {a['next_action']} ({a['title']})"
            for a in sorted(actions, key=lambda x: (x.get('next_action_due', ''), x.get('priority', '')))
        ])
    
    # Check backlog
    backlog_file = tasks_dir.parent / "BACKLOG.md"
    backlog_items = "✅ Clear!"
    if backlog_file.exists():
        with open(backlog_file) as f:
            backlog_content = f.read()
        backlog_count = sum(1 for line in backlog_content.split("\n") 
                          if line.strip().startswith(("-", "*", "1", "2", "3", "4", "5", "6", "7", "8", "9")))
        if backlog_count > 0:
            backlog_items = f"{backlog_count} items pending"
    
    p0_count = len(tasks["P0"]["not_started"]) + len(tasks["P0"]["in_progress"])
    p1_count = len(tasks["P1"]["not_started"]) + len(tasks["P1"]["in_progress"])
    
    print(f"  Found {p0_count} P0 tasks, {p1_count} P1 tasks, {len(actions_due_today)} actions due today")
    
    return {
        "p0_count": p0_count,
        "p1_count": p1_count,
        "blocked_count": len(tasks["blocked"]),
        "done_count": len(tasks["done"]),
        "total": len(tasks["all"]),
        "p0_not_started": format_task_list(tasks["P0"]["not_started"]),
        "p0_in_progress": format_task_list(tasks["P0"]["in_progress"]),
        "p1_not_started": format_task_list(tasks["P1"]["not_started"]),
        "p1_in_progress": format_task_list(tasks["P1"]["in_progress"]),
        "blocked_tasks": format_blocked_tasks(tasks["blocked"]),  # Schema v2.0: includes blocked_by
        "task_details": format_tasks_detailed(tasks["all"]),
        "actions_due_today": format_actions_due_today(actions_due_today),  # Schema v2.0
        "backlog_items": backlog_items,
        "all_tasks": tasks["all"]
    }


def read_prioritization_rules(config: Dict[str, str]) -> str:
    """Read prioritization rules from Knowledge folder."""
    tasks_dir = Path(config.get("TASKS_DIR", "Tasks"))
    rules_file = tasks_dir.parent / "Knowledge" / "prioritization-rules.md"
    
    if rules_file.exists():
        print("  Found prioritization rules")
        with open(rules_file) as f:
            return f.read()
    
    return "Default: Prioritize by 1) Deadlines 2) Blocking others 3) Goal alignment 4) Quick wins"


# ============================================================================
# AI ANALYSIS
# ============================================================================

def get_ai_analysis(config: Dict[str, str], prompt: str, max_tokens: int = 800) -> str:
    """Call LLM API for AI analysis."""
    api_url = config.get("LLM_API_URL", "https://api.openai.com")
    api_key = config.get("LLM_API_KEY")
    model = config.get("LLM_MODEL", "gpt-4o-mini")
    
    if not api_key:
        return "_AI analysis not configured. Set LLM_API_KEY._"
    
    print("  Calling AI for analysis...")
    
    url = f"{api_url}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }).encode()
    
    response = api_request(url, headers, payload, method="POST")
    
    if response and "choices" in response:
        return response["choices"][0]["message"]["content"]
    elif response and "error" in response:
        return f"_AI error: {response['error'].get('message', 'Unknown error')}_"
    
    return "_AI analysis unavailable_"


# ============================================================================
# SLACK POSTING
# ============================================================================

def post_to_slack(config: Dict[str, str], message: str, title: str = "Logbook", 
                  thread_message: str = None) -> Optional[str]:
    """Post a message to Slack, optionally with a thread reply. Returns message ts."""
    token = config.get("SLACK_BOT_TOKEN")
    channel = config.get("SLACK_CHANNEL_ID")
    
    if not token or not channel:
        print("\n📨 Slack not configured. Message would be:")
        print("=" * 60)
        print(message)
        if thread_message:
            print("\n--- Thread Reply ---")
            print(thread_message)
        print("=" * 60)
        return None
    
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Post main message
    payload = json.dumps({
        "channel": channel,
        "text": title,
        "blocks": [{
            "type": "section",
            "text": {"type": "mrkdwn", "text": message[:2900]}  # Slack limit
        }]
    }).encode()
    
    response = api_request(url, headers, payload, method="POST")
    
    if response and response.get("ok"):
        print(f"✅ Posted to Slack: {title}")
        message_ts = response.get("ts")
        
        # Post thread reply if provided
        if thread_message and message_ts:
            thread_payload = json.dumps({
                "channel": channel,
                "thread_ts": message_ts,
                "text": "Activity Details",
                "blocks": [{
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": thread_message[:2900]}
                }]
            }).encode()
            
            thread_response = api_request(url, headers, thread_payload, method="POST")
            if thread_response and thread_response.get("ok"):
                print("✅ Posted thread reply")
            else:
                print("⚠️ Could not post thread reply")
        
        return message_ts
    else:
        error = response.get("error", "Unknown error") if response else "No response"
        print(f"❌ Failed to post to Slack: {error}")
        print("\n📨 Message would be:")
        print("=" * 60)
        print(message)
        print("=" * 60)
        return None


# ============================================================================
# REPORT GENERATORS
# ============================================================================

def generate_daily_briefing(config: Dict[str, str]) -> tuple:
    """Generate morning briefing report. Returns (main_message, thread_message)."""
    print("\n📊 Generating Daily Briefing...")
    
    jira = fetch_jira_activity(config, days=1)
    confluence = fetch_confluence_activity(config, days=1)
    tasks = read_tasks(config)
    rules = read_prioritization_rules(config)
    
    # AI Prompt - matches GitHub Actions workflow
    prompt = f"""You are a productivity assistant. Generate a Slack daily briefing.

CRITICAL: Output must be UNDER 2500 characters total.
Use Slack mrkdwn: *bold*, _italic_, • for bullets

Generate this EXACT structure (follow formatting precisely):

*☀️ Daily Briefing — [TODAY's DATE]*

*🚨 P0 Tasks (Do Today)*
*🔴 Not started*
• [task name]
*🟡 In Progress*
• [task name]

*⚡ P1 Tasks (This Week)*
*🔴 Not started*
• [task name]
*🟡 In Progress*
• [task name]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

*💡 AI Focus Recommendation*
Based on prioritization rules, your current priorities and recent activity, here's what to focus on:

• 🔴 *[P0 Task name]*
_[2-3 sentences explaining WHY this is critical today. Reference specific criteria from prioritization rules.]_

• 🟡 *[P1 Task name]*
_[2-3 sentences explaining the importance.]_

• 🟡 *[Another task]*
_[2-3 sentences with reasoning.]_

_📊 See thread for detailed activity (Jira & Confluence) →_

RULES:
- Status headers: *🔴 Not started* and *🟡 In Progress* as bold headers
- Task bullets: NO emoji, just • [task name]
- Skip empty status groups entirely

TODAY: {datetime.now().strftime('%A, %B %d, %Y')}

P0 TASKS:
Not started: {tasks['p0_not_started'] or '_None_'}
In progress: {tasks['p0_in_progress'] or '_None_'}

P1 TASKS:
Not started: {tasks['p1_not_started'] or '_None_'}
In progress: {tasks['p1_in_progress'] or '_None_'}

JIRA ({jira['count']} issues):
{jira['data'][:500]}

CONFLUENCE ({confluence['count']} pages):
{confluence['data'][:300]}

PRIORITIZATION RULES:
{rules[:1000]}

TASK DETAILS:
{tasks['task_details'][:1000]}"""

    main_report = get_ai_analysis(config, prompt, max_tokens=1000)
    
    # Build thread message with detailed activity
    thread = f"*📊 Recent Activity Details (24h)*\n\n"
    thread += f"*📋 Jira ({jira['count']} issues)*\n"
    thread += jira.get('linked', jira['data']) or "_No Jira activity_"
    thread += "\n\n"
    
    if confluence['count'] > 0:
        thread += f"*📝 Confluence ({confluence['count']} pages)*\n"
        thread += confluence['data']
    
    return main_report, thread


def generate_daily_closing(config: Dict[str, str]) -> tuple:
    """Generate end-of-day closing report. Returns (main_message, thread_message)."""
    print("\n📊 Generating Daily Closing...")
    
    jira = fetch_jira_activity(config, days=1)
    confluence = fetch_confluence_activity(config, days=1)
    git_changes = fetch_git_changes(config, days=1)
    tasks = read_tasks(config)
    
    # AI Prompt - Clean Daily Closing format (matches Daily Briefing style)
    prompt = f"""Generate a concise Slack end-of-day report.

RULES:
1. UNDER 2000 characters
2. Slack mrkdwn: *bold*, _italic_, • bullets
3. ONLY report ACTUAL changes from the data
4. Be crisp and specific

OUTPUT FORMAT:

*📊 Daily Closing — [TODAY's DATE]*

*✅ Completed Today*
• *[Task/Card name]*: [one-line summary of what was done]
If nothing completed: "_No completions recorded_"

*📈 Progress Made*
• 🚩 *[P0 task]*: [specific progress]
• 📌 *[P1 task]*: [specific progress]
Only list tasks with ACTUAL evidence of progress. Skip if none.

*🔄 Status Changes*
List any tasks that changed status (started, blocked, etc):
• *[Task name]*: [old status] → [new status]
    _Reason:_ [why it changed, if known]

*💡 Suggested Updates*
For tasks needing attention:
• 🔴 *[Incomplete P0]*: _Reschedule or mark blocked_
• 🟡 *[Task with Jira activity]*: _Log <URL|KEY> update to task file_

Keep suggestions actionable and brief.

_See thread for details →_

TODAY: {datetime.now().strftime('%A, %B %d, %Y')}

--- DATA ---

FILE CHANGES ({git_changes['count']}):
{git_changes['changes'][:1200]}

TASKS:
🚩 P0: {tasks['p0_in_progress'] or tasks['p0_not_started'] or 'None'}
📌 P1: {tasks['p1_in_progress'][:200] if tasks['p1_in_progress'] else 'None'}

JIRA ({jira['count']}):
{jira.get('detailed', jira['data'])[:1000]}

CONFLUENCE ({confluence['count']}):
{confluence['data'][:400]}"""

    main_report = get_ai_analysis(config, prompt, max_tokens=1000)
    
    # Build thread message with detailed activity
    thread = f"*📊 Today's Activity Details*\n\n"
    thread += f"*📋 Jira ({jira['count']} issues)*\n"
    thread += jira.get('linked', jira['data']) or "_No Jira changes_"
    thread += "\n\n"
    
    if confluence['count'] > 0:
        thread += f"*📝 Confluence ({confluence['count']} pages)*\n"
        thread += confluence['data']
        thread += "\n\n"
    
    # Run Jira sync detection and add to thread
    print("\n🔍 Detecting Jira sync opportunities...")
    suggestions = scan_tasks_for_jira_updates(config)
    
    if suggestions:
        save_pending_jira_updates(suggestions)
        thread += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        thread += f"*🔄 Jira Sync Suggestions ({len(suggestions)} cards)*\n"
        for s in suggestions[:5]:  # Limit to 5 in thread
            thread += f"• <{s['jira_url']}|{s['jira_key']}>: {len(s['updates'])} update(s)\n"
        if len(suggestions) > 5:
            thread += f"_...and {len(suggestions) - 5} more_\n"
        thread += "\n_Run `python3 scripts/logbook-local.py jira-sync` to review and post_"
    
    return main_report, thread


def find_recent_logbook_message(config: Dict[str, str]) -> Optional[Dict]:
    """Find the most recent Logbook message in the DM channel."""
    token = config.get("SLACK_BOT_TOKEN")
    user_id = config.get("SLACK_CHANNEL_ID")  # This is actually the user ID
    
    if not token or not user_id:
        return None
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # First, open/get the DM channel with the user
    open_url = "https://slack.com/api/conversations.open"
    open_payload = json.dumps({"users": user_id}).encode()
    open_response = api_request(open_url, headers, open_payload, method="POST")
    
    if not open_response or not open_response.get("ok"):
        error = open_response.get('error', 'unknown') if open_response else 'no response'
        print(f"  ⚠️ Could not open DM: {error}")
        return None
    
    channel = open_response.get("channel", {}).get("id")
    if not channel:
        print("  ⚠️ Could not get DM channel ID")
        return None
    
    print(f"  Found DM channel: {channel}")
    
    # Get recent messages from the DM
    url = f"https://slack.com/api/conversations.history?channel={channel}&limit=20"
    
    response = api_request(url, headers)
    
    if not response or not response.get("ok"):
        error = response.get('error', 'unknown') if response else 'no response'
        if error == "missing_scope":
            print("  ⚠️ Bot needs 'im:history' scope to read DM history")
            print("     Add this scope in Slack App settings and reinstall")
        elif error == "channel_not_found":
            print("  ⚠️ DM channel not found - bot may not have access")
        else:
            print(f"  Could not fetch DM history: {error}")
        return None
    
    # Find a recent Logbook message (posted by bot)
    messages = response.get("messages", [])
    print(f"  Found {len(messages)} messages in DM history")
    
    for msg in messages:
        text = msg.get("text", "")
        # Check if it looks like a Logbook report
        if "P0 Tasks" in text or "P1 Tasks" in text or "Daily Briefing" in text or "Daily Closing" in text:
            print(f"  ✅ Found Logbook message!")
            return {
                "ts": msg.get("ts"),
                "text": text[:200],
                "channel": channel
            }
    
    print("  ⚠️ No recent Logbook message found in DM")
    return None


def enrich_with_slack_context(config: Dict[str, str]):
    """
    Enrich the most recent Logbook thread with Slack context.
    Uses Slack MCP or user token to read recent messages.
    """
    print("\n🔍 Finding recent Logbook message...")
    
    recent_msg = find_recent_logbook_message(config)
    
    # Try to get Slack user token for reading messages
    user_token = get_slack_token(config)
    
    slack_context = None
    if user_token:
        print("\n📱 Fetching recent Slack activity with user token...")
        slack_context = fetch_slack_activity_with_token(config, user_token)
    
    if slack_context and recent_msg:
        # We have Slack context AND found the thread - analyze with AI and post
        print("\n🤖 Analyzing Slack context with AI...")
        
        tasks = read_tasks(config)
        
        prompt = f"""Based on recent Slack activity, identify any updates or action items relevant to these tasks:

TASKS:
{tasks['task_details']}

RECENT SLACK ACTIVITY:
{slack_context}

Generate a brief Slack message (under 1500 chars) with:
1. Any task-related updates found in Slack
2. Action items or follow-ups mentioned
3. Important mentions or requests

Format for Slack mrkdwn. If nothing relevant found, say "No task-related Slack activity detected."
"""
        
        enrichment = get_ai_analysis(config, prompt, max_tokens=500)
        
        # Post to thread
        post_to_thread(config, recent_msg["ts"], f"*💬 Slack Context*\n\n{enrichment}")
        
    else:
        # Provide instructions for using Cursor's Slack MCP
        tasks = read_tasks(config)
        task_list = tasks.get('task_details', 'No tasks found')[:500]
        
        print("\n" + "=" * 60)
        print("📋 USE CURSOR'S SLACK MCP")
        print("=" * 60)
        print("""
To add Slack context to your Logbook, use Cursor's Slack MCP:

1. Open Cursor IDE (or use this chat)
2. Ask Cursor to search your recent Slack messages:
""")
        print("-" * 60)
        print(f"""
COPY THIS PROMPT TO CURSOR:

"Using the Slack MCP, search my messages from the last 24 hours.
Look for any updates, action items, or discussions related to:
{task_list}

Summarize what's relevant to my current tasks."
""")
        print("-" * 60)
        print("""
3. Ask Cursor to save the summary:
   "Save that summary to scripts/.slack-context.md"

4. Then run: python3 scripts/logbook-local.py post-context
   → This will post the summary to your Logbook thread!
""")
        print("=" * 60)


def fetch_slack_activity_with_token(config: Dict[str, str], token: str) -> Optional[str]:
    """Fetch recent Slack activity using user token."""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Search recent messages
    query = "from:me"  # Messages from the user
    url = f"https://slack.com/api/search.messages?query={query}&count=20&sort=timestamp"
    
    response = api_request(url, headers)
    
    if not response or not response.get("ok"):
        print(f"  Slack search failed: {response.get('error', 'unknown')}")
        return None
    
    messages = response.get("messages", {}).get("matches", [])
    
    if not messages:
        return "_No recent Slack messages found_"
    
    # Format messages
    output = []
    for msg in messages[:10]:
        channel = msg.get("channel", {}).get("name", "DM")
        text = msg.get("text", "")[:200]
        output.append(f"• #{channel}: {text}")
    
    return "\n".join(output)


def post_to_thread(config: Dict[str, str], thread_ts: str, message: str, channel: str = None):
    """Post a message to an existing thread."""
    token = config.get("SLACK_BOT_TOKEN")
    if not channel:
        channel = config.get("SLACK_CHANNEL_ID")
    
    if not token or not channel:
        print("\n📨 Would post to thread:")
        print(message)
        return False
    
    # If channel is a user ID, open DM first
    if channel.startswith("U") or channel.startswith("W"):
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        open_url = "https://slack.com/api/conversations.open"
        open_payload = json.dumps({"users": channel}).encode()
        open_response = api_request(open_url, headers, open_payload, method="POST")
        if open_response and open_response.get("ok"):
            channel = open_response.get("channel", {}).get("id")
    
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = json.dumps({
        "channel": channel,
        "thread_ts": thread_ts,
        "text": "Slack Activity Summary",
        "blocks": [{
            "type": "section",
            "text": {"type": "mrkdwn", "text": message[:2900]}
        }]
    }).encode()
    
    response = api_request(url, headers, payload, method="POST")
    
    if response and response.get("ok"):
        print("✅ Posted Slack context to thread")
        return True
    else:
        print(f"❌ Could not post to thread: {response.get('error', 'unknown')}")
        return False


def post_context_from_file(config: Dict[str, str]):
    """
    Read context from .slack-context.md and post to the most recent Logbook thread.
    This enables the workflow: 
    1. Run 'enrich' -> Cursor searches Slack MCP
    2. Cursor writes summary to .slack-context.md
    3. Run 'post-context' -> Posts to thread
    """
    context_file = Path(__file__).parent / ".slack-context.md"
    
    if not context_file.exists():
        print("❌ No context file found at scripts/.slack-context.md")
        print("\nTo create one, ask Cursor to search your Slack and save the summary:")
        print('   "Search my Slack for task updates and save to scripts/.slack-context.md"')
        return
    
    # Read the context
    with open(context_file) as f:
        context = f.read().strip()
    
    if not context:
        print("❌ Context file is empty")
        return
    
    print(f"📄 Read context ({len(context)} chars)")
    
    # Find recent Logbook message
    print("\n🔍 Finding recent Logbook message...")
    recent_msg = find_recent_logbook_message(config)
    
    if not recent_msg:
        print("❌ No recent Logbook message found")
        print("   Run a briefing/closing first, or check your Slack DM")
        return
    
    print(f"  Found thread: {recent_msg['text'][:50]}...")
    
    # Post to thread (context file should already be formatted)
    success = post_to_thread(config, recent_msg["ts"], context, recent_msg["channel"])
    
    if success:
        # Delete the context file after successful post
        context_file.unlink()
        print("🗑️ Cleaned up context file")


def generate_weekly_review(config: Dict[str, str]) -> tuple:
    """Generate weekly review report. Returns (main_message, thread_message)."""
    print("\n📊 Generating Weekly Review...")
    
    jira = fetch_jira_activity(config, days=7)
    confluence = fetch_confluence_activity(config, days=7)
    git_changes = fetch_git_changes(config, days=7)
    tasks = read_tasks(config)
    
    # AI Prompt
    prompt = f"""You are a productivity coach helping a Product Manager reflect on their week.

CRITICAL: Output must be UNDER 2500 characters. Use Slack mrkdwn formatting.

Generate this structure:

*📅 Weekly Review — Week of [DATE]*

*📈 This Week's Activity*
[Summarize actual activity - only what's in the data]

*📋 Task Overview*
• 🚨 P0: *{tasks['p0_count']}* | ⚡ P1: *{tasks['p1_count']}* | 🟠 Blocked: *{tasks['blocked_count']}* | ✅ Done: *{tasks['done_count']}*

*🚨 P0 Tasks*
*🔴 Not started*
{tasks['p0_not_started'] or '_None_'}
*🟡 In Progress*
{tasks['p0_in_progress'] or '_None_'}

*📥 Backlog:* {tasks['backlog_items']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

*💡 Weekly Reflection*
Based on the data, provide:
1. Key accomplishments (cite specific evidence)
2. Tasks needing attention
3. Next week focus recommendations

_📊 See thread for detailed activity (Jira & Confluence) →_

WEEK ENDING: {datetime.now().strftime('%B %d, %Y')}

WEEKLY ACTIVITY:
- Jira: {jira['count']} issues
- Confluence: {confluence['count']} pages edited
- Task files changed: {git_changes['count']}

JIRA DETAILS:
{jira.get('detailed', jira['data'])[:1000]}

TASK STATUS:
{tasks['task_details'][:1000]}"""

    main_report = get_ai_analysis(config, prompt, max_tokens=1000)
    
    # Build thread message
    thread = f"*📊 Weekly Activity Details*\n\n"
    thread += f"*📋 Jira ({jira['count']} issues)*\n"
    thread += jira.get('linked', jira['data']) or "_No Jira activity_"
    thread += "\n\n"
    
    if confluence['count'] > 0:
        thread += f"*📝 Confluence ({confluence['count']} pages)*\n"
        thread += confluence['data']
    
    return main_report, thread


# ============================================================================
# MAIN
# ============================================================================

def enrich_with_agent(config: Dict[str, str], raw_messages_file: str = None, auto_post: bool = True):
    """
    Use the Agent Orchestrator to generate intelligent Slack context summary.
    
    Args:
        config: Configuration dict
        raw_messages_file: Path to file containing raw Slack messages
        auto_post: If True, automatically post to thread after generating
    """
    import subprocess
    
    script_dir = Path(__file__).parent
    orchestrator_path = script_dir / "agent_orchestrator.py"
    context_file = script_dir / ".slack-context.md"
    
    if not orchestrator_path.exists():
        print("❌ Agent orchestrator not found at scripts/agent_orchestrator.py")
        return
    
    # Check for raw messages file
    if raw_messages_file:
        raw_file = Path(raw_messages_file)
        if not raw_file.exists():
            print(f"❌ Raw messages file not found: {raw_messages_file}")
            return
    else:
        # Check for default raw messages file
        raw_file = script_dir / ".slack-raw.txt"
        if not raw_file.exists():
            print("❌ No raw messages file found")
            print("\nTo use agent enrichment:")
            print("1. Save raw Slack messages to scripts/.slack-raw.txt")
            print("2. Run: python3 scripts/logbook-local.py enrich-agent")
            print("\nOr provide a file path:")
            print("   python3 scripts/logbook-local.py enrich-agent /path/to/messages.txt")
            return
    
    print(f"📄 Reading raw messages from {raw_file}")
    
    # Load environment for LLM API
    env = os.environ.copy()
    env_file = script_dir / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env[key.strip()] = value.strip()
    
    print("🤖 Running Agent Orchestrator for Slack enrichment...")
    
    # Run the agent orchestrator
    result = subprocess.run(
        ["python3", str(orchestrator_path), "slack-enrich", str(raw_file)],
        capture_output=True,
        text=True,
        env=env
    )
    
    if result.returncode != 0:
        print(f"❌ Agent orchestrator failed:")
        print(result.stderr)
        return
    
    # Extract the output (everything after "--- OUTPUT ---")
    output = result.stdout
    if "--- OUTPUT ---" in output:
        enriched_content = output.split("--- OUTPUT ---")[1].strip()
    else:
        enriched_content = output.strip()
    
    if not enriched_content:
        print("❌ No output generated from agent")
        return
    
    print(f"✅ Generated enriched summary ({len(enriched_content)} chars)")
    
    # Save to context file
    with open(context_file, "w") as f:
        f.write(enriched_content)
    print(f"💾 Saved to {context_file}")
    
    # Auto-post if requested
    if auto_post:
        print("\n📤 Auto-posting to thread...")
        post_context_from_file(config)
    else:
        print(f"\nTo post, run: python3 scripts/logbook-local.py post-context")
    
    # Cleanup raw file
    if raw_file.exists() and raw_file.name == ".slack-raw.txt":
        raw_file.unlink()
        print("🗑️ Cleaned up raw messages file")


# ============================================================================
# JIRA SYNC - PHASE 1: DETECTION INFRASTRUCTURE
# ============================================================================

import re
from typing import Tuple

SCRIPT_DIR = Path(__file__).parent

def extract_jira_keys(task_file: Path) -> List[str]:
    """
    Extract Jira keys from a task file's resource_refs and content.
    
    Looks for:
    - URLs like https://domain.atlassian.net/browse/MRC-3266
    - Inline references like [MRC-3266] or (MRC-3266)
    - Markdown links like [MRC-3266](url)
    """
    jira_keys = set()
    
    try:
        content = task_file.read_text()
        
        # Pattern for Jira URLs: https://domain.atlassian.net/browse/KEY-123
        url_pattern = r'https?://[^/]+/browse/([A-Z]+-\d+)'
        jira_keys.update(re.findall(url_pattern, content))
        
        # Pattern for inline references: [KEY-123], (KEY-123), KEY-123
        inline_pattern = r'\b([A-Z]{2,10}-\d+)\b'
        jira_keys.update(re.findall(inline_pattern, content))
        
    except Exception as e:
        print(f"  Warning: Could not read {task_file}: {e}")
    
    return list(jira_keys)


def fetch_jira_issue_state(config: Dict[str, str], jira_key: str) -> Optional[Dict]:
    """
    Fetch the current state of a single Jira issue.
    
    Returns:
        {
            'key': 'MRC-3266',
            'summary': 'Issue title',
            'status': 'In Progress',
            'due_date': '2025-01-09',
            'description': '...',
            'last_comment_date': '2024-12-28T...',
            'last_comment_text': '...',
            'last_updated': '2024-12-30T...',
            'url': 'https://domain.atlassian.net/browse/MRC-3266'
        }
    """
    domain = config.get("ATLASSIAN_DOMAIN")
    email = config.get("ATLASSIAN_EMAIL")
    token = config.get("ATLASSIAN_API_TOKEN")
    
    if not all([domain, email, token]):
        return None
    
    url = f"https://{domain}/rest/api/3/issue/{jira_key}?fields=summary,status,duedate,description,comment,updated"
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
    
    response = api_request(url, headers)
    
    if not response:
        return None
    
    fields = response.get("fields", {})
    
    # Extract last comment
    comments = fields.get("comment", {}).get("comments", [])
    last_comment_date = None
    last_comment_text = None
    if comments:
        last_comment = comments[-1]
        last_comment_date = last_comment.get("created")
        try:
            last_comment_text = last_comment.get("body", {}).get("content", [{}])[0].get("content", [{}])[0].get("text", "")
        except:
            last_comment_text = "[complex comment]"
    
    return {
        "key": jira_key,
        "summary": fields.get("summary", ""),
        "status": fields.get("status", {}).get("name", ""),
        "due_date": fields.get("duedate"),
        "description": fields.get("description", ""),
        "last_comment_date": last_comment_date,
        "last_comment_text": last_comment_text,
        "last_updated": fields.get("updated"),
        "url": f"https://{domain}/browse/{jira_key}"
    }


def parse_progress_log(task_file: Path) -> List[Dict]:
    """
    Parse the Progress Log section from a task file.
    
    Returns list of: [{'date': '2024-12-30', 'content': 'Notes...'}, ...]
    """
    entries = []
    
    try:
        content = task_file.read_text()
        
        # Find Progress Log section
        progress_match = re.search(r'## Progress Log\s*\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
        if not progress_match:
            return entries
        
        progress_section = progress_match.group(1)
        
        # Parse entries: - YYYY-MM-DD: Content
        entry_pattern = r'-\s*(\d{4}-\d{2}-\d{2}):\s*(.+?)(?=\n-\s*\d{4}|\Z)'
        for match in re.finditer(entry_pattern, progress_section, re.DOTALL):
            date_str = match.group(1)
            content = match.group(2).strip()
            entries.append({
                "date": date_str,
                "content": content
            })
    
    except Exception as e:
        print(f"  Warning: Could not parse progress log from {task_file}: {e}")
    
    return entries


def parse_task_frontmatter(task_file: Path) -> Dict:
    """Parse YAML frontmatter from a task file."""
    try:
        content = task_file.read_text()
        
        # Extract frontmatter between ---
        fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if not fm_match:
            return {}
        
        frontmatter = {}
        for line in fm_match.group(1).split('\n'):
            line = line.strip()
            if ':' in line and not line.startswith('#'):
                key, value = line.split(':', 1)
                frontmatter[key.strip()] = value.strip()
        
        return frontmatter
    
    except Exception as e:
        print(f"  Warning: Could not parse frontmatter from {task_file}: {e}")
        return {}


def detect_jira_gaps(task_file: Path, task_data: Dict, jira_state: Dict) -> List[Dict]:
    """
    Compare local task state with Jira state to identify updates needed.
    
    Returns list of suggested updates:
    [
        {
            'type': 'comment',
            'content': 'Update 2024-12-30: ...',
            'reason': 'Local progress since last Jira update',
            'confidence': 'high'
        },
        {
            'type': 'due_date',
            'current': '2025-01-09',
            'suggested': '2025-01-16',
            'reason': 'Task due_date differs from Jira',
            'confidence': 'medium'
        }
    ]
    """
    suggestions = []
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Get progress log entries
    progress_entries = parse_progress_log(task_file)
    
    # --- Check 1: Local progress since last Jira comment ---
    if progress_entries:
        latest_entry = progress_entries[0]  # Most recent
        latest_entry_date = latest_entry['date']
        
        # Compare with Jira's last comment date
        jira_last_comment = jira_state.get('last_comment_date', '')
        if jira_last_comment:
            jira_comment_date = jira_last_comment[:10]  # Extract YYYY-MM-DD
        else:
            jira_comment_date = '1970-01-01'  # No comments = very old
        
        # If local progress is newer than Jira's last comment, suggest update
        if latest_entry_date > jira_comment_date:
            # Find all entries since last Jira comment
            new_entries = [e for e in progress_entries if e['date'] > jira_comment_date]
            
            if new_entries:
                # Generate comment content
                summary_points = []
                for entry in new_entries[:3]:  # Max 3 most recent
                    summary_points.append(f"- {entry['content'][:150]}")
                
                comment_content = f"Update {today}: " + "\n".join(summary_points)
                
                # Add next action if available
                next_action = task_data.get('next_action', '')
                next_action_due = task_data.get('next_action_due', '')
                if next_action:
                    comment_content += f"\n\nNext: {next_action}"
                    if next_action_due:
                        comment_content += f" (by {next_action_due})"
                
                suggestions.append({
                    'type': 'comment',
                    'content': comment_content,
                    'reason': f'Local progress since {jira_comment_date}',
                    'confidence': 'high'
                })
    
    # --- Check 2: Due date mismatch ---
    task_due = task_data.get('due_date', '')
    jira_due = jira_state.get('due_date', '')
    
    if task_due and jira_due and task_due != jira_due:
        suggestions.append({
            'type': 'due_date',
            'current': jira_due,
            'suggested': task_due,
            'reason': 'Local task due_date differs from Jira',
            'confidence': 'medium'
        })
    elif task_due and not jira_due:
        suggestions.append({
            'type': 'due_date',
            'current': 'Not set',
            'suggested': task_due,
            'reason': 'Jira has no due date but task has one',
            'confidence': 'medium'
        })
    
    # --- Check 3: Status mismatch (task done but Jira not) ---
    task_status = task_data.get('status', '')
    jira_status = jira_state.get('status', '').lower()
    
    if task_status == 'd' and jira_status not in ['done', 'closed', 'resolved']:
        suggestions.append({
            'type': 'transition',
            'current': jira_state.get('status', ''),
            'suggested': 'Done',
            'reason': 'Local task is marked done but Jira is not',
            'confidence': 'high'
        })
    
    return suggestions


def scan_tasks_for_jira_updates(config: Dict[str, str]) -> List[Dict]:
    """
    Scan all task files and detect Jira updates needed.
    
    Returns list of suggestions grouped by Jira card:
    [
        {
            'jira_key': 'MRC-3266',
            'jira_title': 'Beta Rollout Scope Document',
            'jira_url': 'https://...',
            'task_file': 'Tasks/001-beta-rollout-scope-document.md',
            'task_title': 'Finish Troy\'s CC Beta rollout scope document',
            'updates': [...]
        }
    ]
    """
    tasks_dir = Path(config.get("TASKS_DIR", "Tasks"))
    all_suggestions = []
    
    print("\n🔍 Scanning tasks for Jira sync opportunities...")
    
    task_files = list(tasks_dir.glob("*.md"))
    task_files = [f for f in task_files if f.name != "README.md"]
    
    print(f"  Found {len(task_files)} task files")
    
    for task_file in task_files:
        # Parse task data
        task_data = parse_task_frontmatter(task_file)
        task_title = task_data.get('title', task_file.stem)
        
        # Skip done tasks (already archived typically)
        if task_data.get('status') == 'd':
            continue
        
        # Extract Jira keys
        jira_keys = extract_jira_keys(task_file)
        
        if not jira_keys:
            continue
        
        print(f"  📄 {task_file.name} → Jira: {', '.join(jira_keys)}")
        
        for jira_key in jira_keys:
            # Fetch Jira state
            jira_state = fetch_jira_issue_state(config, jira_key)
            
            if not jira_state:
                print(f"    ⚠️ Could not fetch {jira_key}")
                continue
            
            # Detect gaps
            updates = detect_jira_gaps(task_file, task_data, jira_state)
            
            if updates:
                print(f"    ✨ Found {len(updates)} update(s) for {jira_key}")
                all_suggestions.append({
                    'jira_key': jira_key,
                    'jira_title': jira_state.get('summary', ''),
                    'jira_url': jira_state.get('url', ''),
                    'jira_status': jira_state.get('status', ''),
                    'task_file': str(task_file),
                    'task_title': task_title,
                    'updates': updates
                })
    
    print(f"\n📊 Total: {len(all_suggestions)} card(s) with suggested updates")
    
    return all_suggestions


def save_pending_jira_updates(suggestions: List[Dict]):
    """Save suggestions to pending file for later review."""
    pending_file = SCRIPT_DIR / ".jira-sync-pending.json"
    
    data = {
        'generated': datetime.now().isoformat(),
        'suggestions': suggestions
    }
    
    with open(pending_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n💾 Saved to {pending_file}")
    return pending_file


def jira_sync_detect(config: Dict[str, str]):
    """
    Phase 1: Detect and save Jira update suggestions.
    Run this from Daily Closing or manually.
    """
    suggestions = scan_tasks_for_jira_updates(config)
    
    if not suggestions:
        print("\n✅ All Jira cards are up to date!")
        return
    
    # Save for later review
    pending_file = save_pending_jira_updates(suggestions)
    
    # Print summary
    print("\n" + "="*60)
    print("📝 JIRA SYNC SUGGESTIONS")
    print("="*60)
    
    for i, suggestion in enumerate(suggestions, 1):
        print(f"\n[{i}] {suggestion['jira_key']}: {suggestion['jira_title'][:50]}")
        print(f"    🔗 {suggestion['jira_url']}")
        print(f"    📄 Task: {suggestion['task_title'][:50]}")
        print(f"    Updates: {len(suggestion['updates'])}")
        for update in suggestion['updates']:
            print(f"      • {update['type']}: {update['reason']}")
    
    print("\n" + "="*60)
    print(f"To review and post: python3 scripts/logbook-local.py jira-sync")
    print("="*60)


def edit_jira_update(update: Dict) -> Optional[Dict]:
    """
    Open update in user's preferred editor for modification.
    Returns modified update dict, or None if cancelled.
    """
    import tempfile
    
    update_type = update['type']
    
    # Build content based on type
    if update_type == 'comment':
        header = f"""# Edit Jira Comment
# Lines starting with # are ignored
# Save and close to apply changes
# ─────────────────────────────────────────────────

"""
        content = update.get('content', '')
    
    elif update_type == 'due_date':
        header = f"""# Edit Due Date
# Change the date on the 'New:' line (format: YYYY-MM-DD)
# Save and close to apply
# ─────────────────────────────────────────────────

Current: {update.get('current', 'Not set')}
New: """
        content = update.get('suggested', '')
    
    elif update_type == 'description':
        header = f"""# Edit Jira Description Addition
# Lines starting with # are ignored
# Save and close to apply
# ─────────────────────────────────────────────────

"""
        content = update.get('content', '')
    
    else:
        print(f"❌ Edit not supported for type: {update_type}")
        return None
    
    # Write to temp file
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.md',
        delete=False,
        prefix='jira-edit-'
    ) as f:
        f.write(header + content)
        temp_path = f.name
    
    # Get user's preferred editor
    editor = os.environ.get('EDITOR', os.environ.get('VISUAL', 'nano'))
    
    # Open in editor and wait
    print(f"📝 Opening in {editor}...")
    result = subprocess.run([editor, temp_path])
    
    if result.returncode != 0:
        print("❌ Editor exited with error. Skipping this update.")
        os.unlink(temp_path)
        return None
    
    # Read back edited content
    with open(temp_path) as f:
        edited_lines = f.readlines()
    
    os.unlink(temp_path)
    
    # Filter out comment lines and extract content
    if update_type == 'due_date':
        # Find the "New: " line
        for line in edited_lines:
            if line.strip().startswith('New:'):
                new_date = line.replace('New:', '').strip()
                if new_date and re.match(r'\d{4}-\d{2}-\d{2}', new_date):
                    update['suggested'] = new_date
                    return update
                else:
                    print(f"❌ Invalid date format: {new_date}. Use YYYY-MM-DD.")
                    return None
        print("❌ Could not find 'New:' line in edited content.")
        return None
    else:
        # Filter comment lines for text content
        edited_content = ''.join(
            line for line in edited_lines
            if not line.strip().startswith('#')
        ).strip()
        
        if not edited_content:
            print("❌ Empty content after editing. Skipping.")
            return None
        
        # Show diff preview
        original = update.get('content', '')[:100]
        edited = edited_content[:100]
        
        print(f"\n📝 Your changes:")
        print(f"   Before: {original}...")
        print(f"   After:  {edited}...")
        
        confirm = input("\nApply these changes? [Y/n]: ").lower().strip()
        if confirm in ['', 'y', 'yes']:
            update['content'] = edited_content
            return update
        else:
            print("Changes discarded.")
            return None


def execute_jira_comment(config: Dict[str, str], jira_key: str, comment: str) -> bool:
    """
    Post a comment to a Jira issue via REST API.
    Returns True on success.
    """
    domain = config.get("ATLASSIAN_DOMAIN")
    email = config.get("ATLASSIAN_EMAIL")
    token = config.get("ATLASSIAN_API_TOKEN")
    
    if not all([domain, email, token]):
        print("❌ Atlassian credentials not configured")
        return False
    
    url = f"https://{domain}/rest/api/3/issue/{jira_key}/comment"
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }
    
    # Convert plain text to ADF (Atlassian Document Format)
    adf_body = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": comment}
                    ]
                }
            ]
        }
    }
    
    payload = json.dumps(adf_body).encode()
    response = api_request(url, headers, payload, method="POST")
    
    if response and response.get("id"):
        return True
    return False


def execute_jira_due_date(config: Dict[str, str], jira_key: str, due_date: str) -> bool:
    """
    Update the due date of a Jira issue via REST API.
    Returns True on success.
    """
    domain = config.get("ATLASSIAN_DOMAIN")
    email = config.get("ATLASSIAN_EMAIL")
    token = config.get("ATLASSIAN_API_TOKEN")
    
    if not all([domain, email, token]):
        print("❌ Atlassian credentials not configured")
        return False
    
    url = f"https://{domain}/rest/api/3/issue/{jira_key}"
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }
    
    payload = json.dumps({
        "fields": {
            "duedate": due_date
        }
    }).encode()
    
    response = api_request(url, headers, payload, method="PUT")
    
    # PUT returns empty on success
    return response is not None or True  # api_request returns None on 204


def execute_jira_transition(config: Dict[str, str], jira_key: str, target_status: str) -> bool:
    """
    Transition a Jira issue to a new status.
    Returns True on success.
    """
    domain = config.get("ATLASSIAN_DOMAIN")
    email = config.get("ATLASSIAN_EMAIL")
    token = config.get("ATLASSIAN_API_TOKEN")
    
    if not all([domain, email, token]):
        print("❌ Atlassian credentials not configured")
        return False
    
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }
    
    # First, get available transitions
    transitions_url = f"https://{domain}/rest/api/3/issue/{jira_key}/transitions"
    transitions = api_request(transitions_url, headers)
    
    if not transitions:
        print(f"❌ Could not fetch transitions for {jira_key}")
        return False
    
    # Find the target transition
    target_transition = None
    target_lower = target_status.lower()
    for t in transitions.get("transitions", []):
        if t.get("name", "").lower() == target_lower or t.get("to", {}).get("name", "").lower() == target_lower:
            target_transition = t
            break
    
    if not target_transition:
        available = [t.get("name") for t in transitions.get("transitions", [])]
        print(f"❌ Transition to '{target_status}' not available.")
        print(f"   Available: {', '.join(available)}")
        return False
    
    # Execute the transition
    payload = json.dumps({
        "transition": {"id": target_transition["id"]}
    }).encode()
    
    response = api_request(transitions_url, headers, payload, method="POST")
    return True  # Transition POST returns 204 No Content on success


def fallback_to_clipboard(update: Dict, jira_key: str, jira_url: str):
    """Copy update content to clipboard with instructions."""
    content = ""
    
    if update['type'] == 'comment':
        content = update.get('content', '')
    elif update['type'] == 'due_date':
        content = f"Due date: {update.get('suggested', '')}"
    elif update['type'] == 'transition':
        content = f"Status: {update.get('suggested', '')}"
    
    try:
        subprocess.run(['pbcopy'], input=content.encode(), check=True)
        print(f"📋 Copied to clipboard!")
        print(f"   Open {jira_url} and paste manually.")
    except Exception as e:
        print(f"❌ Could not copy to clipboard: {e}")
        print(f"   Content: {content[:200]}...")


def execute_jira_update(config: Dict[str, str], jira_key: str, jira_url: str, update: Dict) -> bool:
    """
    Execute a single Jira update. Returns True on success.
    Falls back to clipboard if API fails.
    """
    update_type = update['type']
    success = False
    
    try:
        if update_type == 'comment':
            success = execute_jira_comment(config, jira_key, update['content'])
        elif update_type == 'due_date':
            success = execute_jira_due_date(config, jira_key, update['suggested'])
        elif update_type == 'transition':
            success = execute_jira_transition(config, jira_key, update['suggested'])
        else:
            print(f"❌ Unknown update type: {update_type}")
            return False
        
        if success:
            print(f"✅ {update_type.upper()} posted to {jira_key}")
            return True
        else:
            print(f"❌ API failed. Falling back to clipboard...")
            fallback_to_clipboard(update, jira_key, jira_url)
            return False
    
    except Exception as e:
        print(f"❌ Error executing update: {e}")
        fallback_to_clipboard(update, jira_key, jira_url)
        return False


def log_to_task_progress(task_file: str, jira_key: str, update: Dict):
    """Log successful Jira update to task's Progress Log."""
    try:
        task_path = Path(task_file)
        if not task_path.exists():
            return
        
        content = task_path.read_text()
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Build log entry
        update_type = update['type']
        if update_type == 'comment':
            log_entry = f"- {today}: [Jira Sync] Posted comment to {jira_key}"
        elif update_type == 'due_date':
            log_entry = f"- {today}: [Jira Sync] Updated {jira_key} due date to {update.get('suggested')}"
        elif update_type == 'transition':
            log_entry = f"- {today}: [Jira Sync] Transitioned {jira_key} to {update.get('suggested')}"
        else:
            log_entry = f"- {today}: [Jira Sync] Updated {jira_key}"
        
        # Find Progress Log section and append
        if '## Progress Log' in content:
            # Insert after ## Progress Log header
            parts = content.split('## Progress Log')
            if len(parts) == 2:
                header_end = parts[1].find('\n')
                if header_end == -1:
                    header_end = 0
                new_content = parts[0] + '## Progress Log' + parts[1][:header_end+1] + log_entry + '\n' + parts[1][header_end+1:]
                task_path.write_text(new_content)
                print(f"   📝 Logged to {task_path.name}")
    except Exception as e:
        print(f"   ⚠️ Could not log to task file: {e}")


def log_agent_feedback(workflow: str, suggestion_type: str, action: str):
    """
    Track user approval/rejection patterns for learning.
    Logs minimal data to Knowledge/agent-feedback.yaml
    """
    feedback_file = SCRIPT_DIR.parent / "Knowledge" / "agent-feedback.yaml"
    
    try:
        # Ensure directory exists
        feedback_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing feedback
        entries = []
        if feedback_file.exists():
            content = feedback_file.read_text()
            # Simple YAML-like parsing (avoid dependency)
            for line in content.split('\n'):
                if line.strip().startswith('- date:'):
                    entries.append({})
                elif entries and ':' in line:
                    key, value = line.strip().strip('- ').split(':', 1)
                    entries[-1][key.strip()] = value.strip()
        
        # Add new entry
        today = datetime.now().strftime('%Y-%m-%d')
        new_entry = f"""- date: "{today}"
  workflow: "{workflow}"
  suggestion_type: "{suggestion_type}"
  action: "{action}"
"""
        
        # Append to file
        with open(feedback_file, 'a') as f:
            if not feedback_file.exists() or feedback_file.stat().st_size == 0:
                f.write("# Agent Feedback Log\n# Tracks approval/rejection patterns for system learning\n\nfeedback:\n")
            f.write(new_entry)
    
    except Exception as e:
        # Non-critical, don't interrupt flow
        pass


def jira_sync_review(config: Dict[str, str]):
    """
    Phase 3+4: Interactive review and execution of pending Jira updates.
    
    For each suggestion:
    - Show preview with hyperlinked card name
    - Allow: [A]pprove / [E]dit / [S]kip / [Q]uit
    - Execute approved updates via REST API
    - Fall back to clipboard if API fails
    - Log successful updates to task Progress Log
    """
    pending_file = SCRIPT_DIR / ".jira-sync-pending.json"
    
    if not pending_file.exists():
        print("❌ No pending Jira updates found.")
        print("   Run 'jira-detect' first to scan for updates.")
        return
    
    # Load pending suggestions
    with open(pending_file) as f:
        data = json.load(f)
    
    suggestions = data.get('suggestions', [])
    generated = data.get('generated', 'unknown')
    
    if not suggestions:
        print("✅ No pending updates!")
        pending_file.unlink()
        return
    
    # Check if file is stale (>24h old)
    try:
        gen_time = datetime.fromisoformat(generated)
        age_hours = (datetime.now() - gen_time).total_seconds() / 3600
        if age_hours > 24:
            print(f"⚠️ Warning: Pending file is {age_hours:.1f} hours old.")
            print("   Consider running 'jira-detect' again for fresh data.")
            if input("   Continue anyway? [y/N]: ").lower() != 'y':
                return
    except:
        pass
    
    print("\n" + "="*60)
    print("📝 JIRA SYNC - Review Pending Updates")
    print("="*60)
    print(f"Generated: {generated}")
    print(f"Cards: {len(suggestions)}")
    print("\nCommands: [A]pprove / [E]dit / [S]kip / [Q]uit")
    
    approved_count = 0
    skipped_count = 0
    failed_count = 0
    
    for i, suggestion in enumerate(suggestions, 1):
        jira_key = suggestion['jira_key']
        jira_title = suggestion['jira_title']
        jira_url = suggestion['jira_url']
        task_file = suggestion['task_file']
        task_title = suggestion['task_title']
        updates = suggestion['updates']
        
        print(f"\n{'='*60}")
        print(f"[{i}/{len(suggestions)}] 📋 {jira_key}: {jira_title}")
        print(f"🔗 {jira_url}")
        print(f"📄 Task: {task_title}")
        print("="*60)
        
        for j, update in enumerate(updates, 1):
            update_type = update['type'].upper()
            reason = update.get('reason', '')
            confidence = update.get('confidence', 'medium')
            
            print(f"\n[{j}/{len(updates)}] {update_type} ({confidence} confidence)")
            print(f"Reason: {reason}")
            print("-"*50)
            
            # Show preview based on type
            if update['type'] == 'comment':
                print(update['content'])
            elif update['type'] == 'due_date':
                print(f"Current:   {update.get('current', 'Not set')}")
                print(f"Suggested: {update.get('suggested', 'Not set')}")
            elif update['type'] == 'transition':
                print(f"Current:   {update.get('current', 'Unknown')}")
                print(f"Suggested: {update.get('suggested', 'Done')}")
            
            print("-"*50)
            
            # Prompt for action
            choice = input("\n[A]pprove / [E]dit / [S]kip / [Q]uit: ").lower().strip()
            
            if choice == 'q':
                print("\n⏹️ Quitting. Remaining updates saved for later.")
                # Save remaining suggestions
                remaining = suggestions[i-1:]
                remaining[0]['updates'] = updates[j-1:]
                save_pending_jira_updates(remaining)
                return
            
            elif choice == 'a':
                success = execute_jira_update(config, jira_key, jira_url, update)
                if success:
                    approved_count += 1
                    log_to_task_progress(task_file, jira_key, update)
                    log_agent_feedback("jira_sync", update['type'], "approved")
                else:
                    failed_count += 1
                    log_agent_feedback("jira_sync", update['type'], "failed")
            
            elif choice == 'e':
                edited = edit_jira_update(update)
                if edited:
                    success = execute_jira_update(config, jira_key, jira_url, edited)
                    if success:
                        approved_count += 1
                        log_to_task_progress(task_file, jira_key, edited)
                        log_agent_feedback("jira_sync", update['type'], "approved_edited")
                    else:
                        failed_count += 1
                        log_agent_feedback("jira_sync", update['type'], "failed")
                else:
                    skipped_count += 1
                    log_agent_feedback("jira_sync", update['type'], "edit_cancelled")
            
            else:  # 's' or any other
                print("⏭️ Skipped")
                skipped_count += 1
                log_agent_feedback("jira_sync", update['type'], "skipped")
    
    # Cleanup
    pending_file.unlink()
    
    print("\n" + "="*60)
    print("✅ JIRA SYNC COMPLETE")
    print("="*60)
    print(f"✅ Approved & Posted: {approved_count}")
    print(f"⏭️ Skipped:          {skipped_count}")
    if failed_count:
        print(f"❌ Failed (clipboard): {failed_count}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nAvailable commands:")
        print("  briefing      - Morning focus report (9:00 AM)")
        print("  closing       - End-of-day wrap-up (5:30 PM)")
        print("  weekly        - Weekly review (Friday)")
        print("  enrich        - Show prompt for Cursor to search Slack")
        print("  enrich-agent  - Use Agent Orchestrator for smart enrichment")
        print("  post-context  - Post .slack-context.md to Logbook thread")
        print("  jira-detect   - Scan tasks and detect Jira updates needed")
        print("  jira-sync     - Review and post pending Jira updates")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    config = load_config()
    
    print(f"\n🚀 Logbook Local - {command.replace('-', ' ').title()}")
    print("=" * 50)
    
    if command == "briefing":
        main_msg, thread_msg = generate_daily_briefing(config)
        post_to_slack(config, main_msg, "Daily Briefing", thread_msg)
    elif command == "closing":
        main_msg, thread_msg = generate_daily_closing(config)
        post_to_slack(config, main_msg, "Daily Closing", thread_msg)
    elif command == "weekly":
        main_msg, thread_msg = generate_weekly_review(config)
        post_to_slack(config, main_msg, "Weekly Review", thread_msg)
    elif command == "enrich":
        enrich_with_slack_context(config)
    elif command == "enrich-agent":
        # Optional: pass file path as second argument
        raw_file = sys.argv[2] if len(sys.argv) > 2 else None
        enrich_with_agent(config, raw_file)
    elif command == "post-context":
        post_context_from_file(config)
    elif command == "jira-detect":
        jira_sync_detect(config)
    elif command == "jira-sync":
        jira_sync_review(config)
    else:
        print(f"Unknown command: {command}")
        print("Available commands: briefing, closing, weekly, enrich, enrich-agent, post-context, jira-detect, jira-sync")
        sys.exit(1)
    
    print("\n✅ Done!")


if __name__ == "__main__":
    main()
