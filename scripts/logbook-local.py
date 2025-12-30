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
    
    # Try to load .env file
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip().strip('"').strip("'")
    
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
    
    # Use new POST API with changelog expansion
    url = f"https://{domain}/rest/api/3/search/jql"
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
    
    payload = json.dumps({
        "jql": jql,
        "maxResults": 20,
        "fields": ["key", "summary", "status", "description", "comment"],
        "expand": ["changelog"]
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
            
        url = f"https://{domain}/wiki/rest/api/content?spaceKey={space}&expand=history.lastUpdated&limit=20&orderby=history.lastUpdated%20desc"
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
    """Read tasks from the Tasks directory, grouped by status."""
    tasks_dir = Path(config.get("TASKS_DIR", "Tasks"))
    
    if not tasks_dir.exists():
        return {
            "p0_count": 0, "p1_count": 0, "blocked_count": 0, "done_count": 0, "total": 0,
            "p0_not_started": "", "p0_in_progress": "",
            "p1_not_started": "", "p1_in_progress": "",
            "blocked_tasks": "", "task_details": "", "backlog_items": "✅ Clear!"
        }
    
    print("  Reading tasks...")
    
    tasks = {
        "P0": {"not_started": [], "in_progress": []},
        "P1": {"not_started": [], "in_progress": []},
        "blocked": [], "done": [], "all": []
    }
    
    for filepath in tasks_dir.glob("*.md"):
        with open(filepath) as f:
            content = f.read()
        
        # Parse frontmatter
        title = priority = status = due_date = ""
        if content.startswith("---"):
            try:
                frontmatter = content.split("---")[1]
                for line in frontmatter.split("\n"):
                    if line.startswith("title:"):
                        title = line.split(":", 1)[1].strip()
                    elif line.startswith("priority:"):
                        priority = line.split(":", 1)[1].strip()
                    elif line.startswith("status:"):
                        status = line.split(":", 1)[1].strip()
                    elif line.startswith("due_date:"):
                        due_date = line.split(":", 1)[1].strip()
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
            "due_date": due_date, "content": content, "filepath": str(filepath)
        }
        
        tasks["all"].append(task_info)
        
        # Group by priority and status
        if priority == "P0":
            if status == "n":
                tasks["P0"]["not_started"].append(task_info)
            elif status in ["s", "ip"]:
                tasks["P0"]["in_progress"].append(task_info)
        elif priority == "P1":
            if status == "n":
                tasks["P1"]["not_started"].append(task_info)
            elif status in ["s", "ip"]:
                tasks["P1"]["in_progress"].append(task_info)
        
        if status == "b":
            tasks["blocked"].append(task_info)
        if status == "d":
            tasks["done"].append(task_info)
    
    def format_task_list(task_list):
        return "\n".join([f"• {t['title']}" for t in task_list])
    
    def format_tasks_detailed(task_list):
        return "\n".join([f"• {t['emoji']} [{t['priority']}] {t['title']} — {t['status_text']}" for t in task_list])
    
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
    
    print(f"  Found {p0_count} P0 tasks, {p1_count} P1 tasks")
    
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
        "blocked_tasks": format_task_list(tasks["blocked"]),
        "task_details": format_tasks_detailed(tasks["all"]),
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
    
    # AI Prompt - matches GitHub Actions workflow
    prompt = f"""You are a productivity assistant. Generate a Slack end-of-day report.

CRITICAL RULES:
1. Output must be UNDER 2500 characters total
2. Use Slack mrkdwn: *bold*, _italic_, • for bullets
3. ONLY report items with ACTUAL changes in the data - NEVER invent or assume
4. If no changes, say so honestly - don't make up progress
5. Be SPECIFIC - say exactly what changed, not vague summaries

Generate this EXACT structure:

*📊 Daily Closing — [TODAY's DATE]*

*📈 Today's Progress*
ONLY list items from the data that had ACTUAL changes:
• 📝 *[filename]*: [quote the specific change from git diff]
• 📋 *<Jira URL|ticket> - [card name]*: [exact change from changelog]
• 📄 *[Confluence page]*: [what was edited]

SKIP any item without real changes. If nothing changed, write: "_No recorded changes today._"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

*📋 Task Status*
ONLY write about tasks that appear in Today's Progress or have suggested updates.
*🚨 P0 Tasks (Do Today)*: [If no P0 changes recorded, say "No progress recorded - task remains incomplete"]
*⚡ P1 Tasks (This Week)*: [Only mention tasks with actual evidence. Quote the specific change.]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

*💡 Suggested Task Updates*
Based on the ACTUAL changes above, suggest what to log:

For P0 tasks with NO activity in the data:
• 🔴 *[Task name]*: _No work recorded today. Reschedule to [date] or mark blocked._

For tasks with Jira changes - use the EXACT change from data:
• 🟡 *[Task name]*: _<URL|ticket>: [exact changelog entry]. Log this in the task file._

For tasks with file changes:
• 🟡 *[Task name]*: _File updated: "[quote diff]". Consider changing status._

DO NOT suggest updates for tasks without evidence in the data.

_📊 See thread for detailed activity (Jira & Confluence) →_

TODAY: {datetime.now().strftime('%A, %B %d, %Y')}

═══════════════════════════════════════════
TASK FILE CHANGES ({git_changes['count']} files with actual changes)
═══════════════════════════════════════════
{git_changes['changes'][:1500]}

═══════════════════════════════════════════
CURRENT TASK STATUS
═══════════════════════════════════════════
P0 TASKS (were due TODAY):
Not started: {tasks['p0_not_started'] or '_None_'}
In progress: {tasks['p0_in_progress'] or '_None_'}

P1 TASKS (due this week):
Not started: {tasks['p1_not_started'] or '_None_'}
In progress: {tasks['p1_in_progress'] or '_None_'}

═══════════════════════════════════════════
JIRA ACTIVITY ({jira['count']} issues with actual changes)
═══════════════════════════════════════════
{jira.get('detailed', jira['data'])[:1500]}

═══════════════════════════════════════════
CONFLUENCE ACTIVITY ({confluence['count']} pages)
═══════════════════════════════════════════
{confluence['data'][:500]}

TASK DETAILS:
{tasks['task_details'][:800]}"""

    main_report = get_ai_analysis(config, prompt, max_tokens=1000)
    
    # Build thread message with detailed activity
    thread = f"*📊 Today's Activity Details*\n\n"
    thread += f"*📋 Jira ({jira['count']} issues)*\n"
    thread += jira.get('linked', jira['data']) or "_No Jira changes_"
    thread += "\n\n"
    
    if confluence['count'] > 0:
        thread += f"*📝 Confluence ({confluence['count']} pages)*\n"
        thread += confluence['data']
    
    return main_report, thread


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

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nAvailable commands: briefing, closing, weekly")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    config = load_config()
    
    print(f"\n🚀 Logbook Local - {command.title()}")
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
    else:
        print(f"Unknown command: {command}")
        print("Available commands: briefing, closing, weekly")
        sys.exit(1)
    
    print("\n✅ Done!")


if __name__ == "__main__":
    main()
