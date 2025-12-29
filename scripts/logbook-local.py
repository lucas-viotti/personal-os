#!/usr/bin/env python3
"""
Logbook Local - Personal OS Daily/Weekly Reports with Full Slack Access

This script provides the same functionality as the GitHub Actions workflows,
but runs locally on your machine. This enables:
- Full Slack access via MCP OAuth tokens (no company restrictions)
- VPN/internal network access for Atlassian APIs
- Integration with local tools and credentials

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
import glob
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
    """
    Get Slack token with fallback chain:
    1. SLACK_USER_TOKEN (preferred for full access)
    2. Read from Slack MCP OAuth storage
    3. SLACK_BOT_TOKEN (limited access)
    """
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
                    # Adjust based on your MCP's token storage format
                    return token_data.get("access_token") or token_data.get("token")
            except Exception as e:
                print(f"Could not read MCP token: {e}")
    
    # Option 3: Try macOS keychain (common for MCP OAuth)
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
    """Fetch Jira activity for the specified time period."""
    domain = config.get("ATLASSIAN_DOMAIN")
    email = config.get("ATLASSIAN_EMAIL")
    token = config.get("ATLASSIAN_API_TOKEN")
    project = config.get("JIRA_PROJECT")
    
    if not all([domain, email, token, project]):
        return {"count": 0, "data": "_Jira not configured_", "issues": []}
    
    since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    jql = f"project = {project} AND updated >= '{since_date}' ORDER BY updated DESC"
    
    url = f"https://{domain}/rest/api/3/search?jql={urllib.parse.quote(jql)}&maxResults=30&fields=key,summary,status,resolution,updated"
    
    import base64
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
    
    response = api_request(url, headers)
    
    if not response or "issues" not in response:
        return {"count": 0, "data": "_Could not fetch Jira data_", "issues": []}
    
    issues = response.get("issues", [])
    count = len(issues)
    resolved = sum(1 for i in issues if i.get("fields", {}).get("resolution"))
    
    if count == 0:
        data = f"_No Jira activity in the last {days} day(s)_"
    else:
        data = "\n".join([
            f"• {i['key']}: {i['fields']['summary']} [{i['fields']['status']['name']}]"
            for i in issues[:10]
        ])
    
    return {"count": count, "resolved": resolved, "data": data, "issues": issues}


def fetch_confluence_activity(config: Dict[str, str], days: int = 1) -> Dict[str, Any]:
    """Fetch Confluence activity for the specified time period."""
    domain = config.get("ATLASSIAN_DOMAIN")
    email = config.get("ATLASSIAN_EMAIL")
    token = config.get("ATLASSIAN_API_TOKEN")
    spaces = config.get("CONFLUENCE_SPACES", "").split(",")
    
    if not all([domain, email, token]) or not spaces[0]:
        return {"count": 0, "data": "_Confluence not configured_", "pages": []}
    
    import base64
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
                    all_pages.append(page["title"])
    
    count = len(all_pages)
    if count == 0:
        data = f"_No Confluence edits in the last {days} day(s)_"
    else:
        data = "\n".join([f"• {title}" for title in all_pages[:10]])
    
    return {"count": count, "data": data, "pages": all_pages}


def fetch_slack_activity(config: Dict[str, str], days: int = 1) -> Dict[str, Any]:
    """
    Fetch Slack activity using Search API (requires user token with search:read).
    Falls back to counting messages if only bot token available.
    """
    token = get_slack_token(config)
    
    if not token:
        return {"count": 0, "data": "_Slack not configured_", "messages": []}
    
    # Try search API first (requires user token)
    since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    query = f"from:me after:{since_date}"
    
    url = f"https://slack.com/api/search.messages?query={urllib.parse.quote(query)}&count=20"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = api_request(url, headers)
    
    if response and response.get("ok"):
        messages = response.get("messages", {}).get("matches", [])
        count = response.get("messages", {}).get("total", 0)
        
        if count == 0:
            data = f"_No Slack messages in the last {days} day(s)_"
        else:
            # Summarize by channel
            channels = {}
            for msg in messages[:20]:
                ch = msg.get("channel", {}).get("name", "DM")
                channels[ch] = channels.get(ch, 0) + 1
            
            data = f"*{count} messages* across {len(channels)} conversations"
            if channels:
                top_channels = sorted(channels.items(), key=lambda x: -x[1])[:5]
                data += "\n" + "\n".join([f"• #{ch}: {n} messages" for ch, n in top_channels])
        
        return {"count": count, "data": data, "messages": messages}
    
    # Fallback: Just report that Slack access is limited
    if response and not response.get("ok"):
        error = response.get("error", "unknown")
        if error == "missing_scope":
            return {"count": 0, "data": "_Slack search requires user token with search:read scope_", "messages": []}
    
    return {"count": 0, "data": "_Could not fetch Slack data_", "messages": []}


def read_tasks(config: Dict[str, str]) -> Dict[str, Any]:
    """Read tasks from the Tasks directory."""
    tasks_dir = Path(config.get("TASKS_DIR", "Tasks"))
    
    if not tasks_dir.exists():
        return {
            "p0_count": 0, "p1_count": 0, "blocked_count": 0, "done_count": 0,
            "total": 0, "p0_tasks": "", "p1_tasks": "", "blocked_tasks": "",
            "task_details": "", "backlog_items": "✅ Clear!"
        }
    
    tasks = {"P0": [], "P1": [], "P2": [], "P3": [], "blocked": [], "done": [], "all": []}
    
    for filepath in tasks_dir.glob("*.md"):
        with open(filepath) as f:
            content = f.read()
        
        # Parse frontmatter
        title = priority = status = ""
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
            except:
                pass
        
        if not title:
            title = filepath.stem.replace("-", " ").title()
        
        status_emoji = {"n": "🔴", "s": "🟡", "ip": "🟡", "b": "🟠", "d": "✅"}.get(status, "⚪")
        status_text = {"n": "Not Started", "s": "In Progress", "ip": "In Progress", 
                       "b": "Blocked", "d": "Done"}.get(status, "Unknown")
        
        task_info = {"title": title, "priority": priority, "status": status,
                     "emoji": status_emoji, "status_text": status_text}
        
        tasks["all"].append(task_info)
        if priority in tasks:
            tasks[priority].append(task_info)
        if status == "b":
            tasks["blocked"].append(task_info)
        if status == "d":
            tasks["done"].append(task_info)
    
    def format_tasks(task_list):
        return "\n".join([f"• {t['emoji']} {t['title']}" for t in task_list])
    
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
    
    return {
        "p0_count": len(tasks["P0"]),
        "p1_count": len(tasks["P1"]),
        "blocked_count": len(tasks["blocked"]),
        "done_count": len(tasks["done"]),
        "total": len(tasks["all"]),
        "p0_tasks": format_tasks(tasks["P0"]),
        "p1_tasks": format_tasks(tasks["P1"]),
        "blocked_tasks": format_tasks(tasks["blocked"]),
        "task_details": format_tasks_detailed(tasks["all"]),
        "backlog_items": backlog_items
    }


# ============================================================================
# AI ANALYSIS
# ============================================================================

def get_ai_analysis(config: Dict[str, str], prompt: str) -> str:
    """Call LLM API for AI analysis."""
    api_url = config.get("LLM_API_URL", "https://api.openai.com")
    api_key = config.get("LLM_API_KEY")
    model = config.get("LLM_MODEL", "gpt-4o-mini")
    
    if not api_key:
        return "_AI analysis not configured. Set LLM_API_KEY._"
    
    url = f"{api_url}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 600,
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

def post_to_slack(config: Dict[str, str], message: str, title: str = "Logbook") -> bool:
    """Post a message to Slack."""
    token = config.get("SLACK_BOT_TOKEN")
    channel = config.get("SLACK_CHANNEL_ID")
    
    if not token or not channel:
        print("Slack not configured. Message would be:")
        print("-" * 50)
        print(message)
        print("-" * 50)
        return False
    
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = json.dumps({
        "channel": channel,
        "text": title,
        "blocks": [{
            "type": "section",
            "text": {"type": "mrkdwn", "text": message}
        }]
    }).encode()
    
    response = api_request(url, headers, payload, method="POST")
    
    if response and response.get("ok"):
        print(f"✅ Posted to Slack: {title}")
        return True
    else:
        error = response.get("error", "Unknown error") if response else "No response"
        print(f"❌ Failed to post to Slack: {error}")
        print("Message would be:")
        print("-" * 50)
        print(message)
        print("-" * 50)
        return False


# ============================================================================
# REPORT GENERATORS
# ============================================================================

def generate_daily_briefing(config: Dict[str, str]) -> str:
    """Generate morning briefing report."""
    print("📊 Generating Daily Briefing...")
    
    jira = fetch_jira_activity(config, days=1)
    confluence = fetch_confluence_activity(config, days=1)
    slack = fetch_slack_activity(config, days=1)
    tasks = read_tasks(config)
    
    # AI Prompt
    prompt = f"""You are a productivity assistant helping a Product Manager start their day.

Based on the context below, provide:
1. A brief 2-3 sentence focus recommendation for today
2. Identify any tasks that might need attention based on recent activity
3. Flag any potential blockers or follow-ups needed

Keep it concise. Use Slack mrkdwn formatting (bold with *, bullets with •).

TODAY: {datetime.now().strftime('%A, %B %d, %Y')}

TASK SUMMARY:
- P0 Tasks (Do Today): {tasks['p0_count']}
- P1 Tasks (This Week): {tasks['p1_count']}
- Blocked Tasks: {tasks['blocked_count']}

P0 TASKS:
{tasks['p0_tasks']}

P1 TASKS:
{tasks['p1_tasks']}

RECENT ACTIVITY:
- Jira ({jira['count']} tickets): {jira['data'][:500]}
- Confluence ({confluence['count']} pages): {confluence['data'][:300]}
- Slack: {slack['data'][:300]}"""

    ai_suggestions = get_ai_analysis(config, prompt)
    
    # Build report
    report = f"*☀️ Daily Briefing — {datetime.now().strftime('%A, %B %d, %Y')}*\n\n"
    
    report += "*📊 Recent Activity*\n"
    report += f"• 📋 Jira tickets: *{jira['count']}*\n"
    report += f"• 📝 Confluence pages: *{confluence['count']}*\n"
    report += f"• 💬 Slack: *{slack['data'].split('*')[1] if '*' in slack['data'] else '0'}*\n\n"
    
    report += "*📋 Today's Focus*\n"
    report += f"• 🚨 P0 (Do Today): *{tasks['p0_count']}*\n"
    report += f"• ⚡ P1 (This Week): *{tasks['p1_count']}*\n"
    if tasks['blocked_count'] > 0:
        report += f"• 🟠 Blocked: *{tasks['blocked_count']}*\n"
    report += "\n"
    
    if tasks['p0_count'] > 0:
        report += f"*🚨 P0 Tasks (Do Today)*\n{tasks['p0_tasks']}\n\n"
    
    if tasks['p1_count'] > 0:
        report += f"*⚡ P1 Tasks (This Week)*\n{tasks['p1_tasks']}\n\n"
    
    report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    report += f"*💡 AI Focus Recommendation*\n{ai_suggestions}\n\n"
    report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    report += "_Reply @Cursor to engage with an agent to apply updates_"
    
    return report


def generate_daily_closing(config: Dict[str, str]) -> str:
    """Generate end-of-day closing report."""
    print("📊 Generating Daily Closing...")
    
    jira = fetch_jira_activity(config, days=1)
    confluence = fetch_confluence_activity(config, days=1)
    slack = fetch_slack_activity(config, days=1)
    tasks = read_tasks(config)
    
    # AI Prompt
    prompt = f"""You are a productivity assistant helping a Product Manager log their daily progress.

Based on today's activity, suggest:
1. *Task Updates to Log* - Which tasks should have progress logged?
2. *Status Changes* - Should any task statuses be updated?
3. *Missing Tasks* - Is there activity not connected to existing tasks?

Keep it concise. Use Slack mrkdwn formatting.

TODAY: {datetime.now().strftime('%A, %B %d, %Y')}

TODAY'S ACTIVITY:
- Jira ({jira['count']} tickets): {jira['data'][:500]}
- Confluence ({confluence['count']} pages): {confluence['data'][:300]}
- Slack: {slack['data'][:300]}

CURRENT TASKS:
{tasks['task_details']}"""

    ai_suggestions = get_ai_analysis(config, prompt)
    
    # Build report
    report = f"*📊 Daily Closing — {datetime.now().strftime('%A, %B %d, %Y')}*\n\n"
    
    report += "*📈 Today's Activity*\n"
    report += f"• 📋 Jira tickets: *{jira['count']}*\n"
    report += f"• 📝 Confluence pages: *{confluence['count']}*\n"
    report += f"• 💬 Slack: *{slack['data'].split('*')[1] if '*' in slack['data'] else '0'}*\n\n"
    
    if jira['count'] > 0:
        report += f"*📋 Jira Activity*\n{jira['data'][:500]}\n\n"
    
    if confluence['count'] > 0:
        report += f"*📝 Confluence Activity*\n{confluence['data'][:300]}\n\n"
    
    report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    report += f"*🚨 P0 Tasks* ({tasks['p0_count']})\n"
    report += f"{tasks['p0_tasks'] or '_No P0 tasks_'}\n\n"
    
    report += f"*⚡ P1 Tasks* ({tasks['p1_count']})\n"
    report += f"{tasks['p1_tasks'] or '_No P1 tasks_'}\n\n"
    
    report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    report += f"*💡 Suggested Task Updates*\n{ai_suggestions}\n\n"
    report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    report += "_Reply @Cursor to apply updates, or say \"nothing changed\"_"
    
    return report


def generate_weekly_review(config: Dict[str, str]) -> str:
    """Generate weekly review report."""
    print("📊 Generating Weekly Review...")
    
    jira = fetch_jira_activity(config, days=7)
    confluence = fetch_confluence_activity(config, days=7)
    slack = fetch_slack_activity(config, days=7)
    tasks = read_tasks(config)
    
    # AI Prompt
    prompt = f"""You are a productivity coach helping a Product Manager reflect on their week.

Provide a brief weekly reflection covering:
1. *Key Accomplishments* - What meaningful progress was made?
2. *Attention Needed* - Any blocked tasks or concerning patterns?
3. *Next Week Focus* - Based on P0/P1, what should be priorities?
4. *Housekeeping* - Any tasks to archive or backlog to process?

Keep it concise and motivating. Use Slack mrkdwn formatting.

WEEK ENDING: {datetime.now().strftime('%B %d, %Y')}

WEEKLY ACTIVITY:
- Jira tickets touched: {jira['count']}
- Jira tickets resolved: {jira.get('resolved', 0)}
- Confluence pages edited: {confluence['count']}
- Slack: {slack['data'][:200]}

TASK STATUS:
- P0 (Critical): {tasks['p0_count']}
- P1 (This Week): {tasks['p1_count']}
- Blocked: {tasks['blocked_count']}
- Done (ready to archive): {tasks['done_count']}
- Total Active: {tasks['total']}
- Backlog: {tasks['backlog_items']}

ALL TASKS:
{tasks['task_details']}"""

    ai_suggestions = get_ai_analysis(config, prompt)
    
    # Build report
    report = f"*📅 Weekly Review — Week of {datetime.now().strftime('%B %d, %Y')}*\n\n"
    
    report += "*📈 This Week's Activity*\n"
    report += f"• 📋 Jira: *{jira['count']}* touched, *{jira.get('resolved', 0)}* resolved\n"
    report += f"• 📝 Confluence: *{confluence['count']}* pages edited\n"
    report += f"• 💬 Slack: *{slack['data'].split('*')[1] if '*' in slack['data'] else '0'}*\n\n"
    
    report += "*📋 Task Overview*\n"
    report += f"• 🚨 P0 (Critical): *{tasks['p0_count']}*\n"
    report += f"• ⚡ P1 (This Week): *{tasks['p1_count']}*\n"
    report += f"• 🟠 Blocked: *{tasks['blocked_count']}*\n"
    report += f"• ✅ Done: *{tasks['done_count']}*\n"
    report += f"• 📊 Total Active: *{tasks['total']}*\n\n"
    
    if tasks['p0_count'] > 0:
        report += f"*🚨 P0 Tasks*\n{tasks['p0_tasks']}\n\n"
    
    report += f"*📥 Backlog:* {tasks['backlog_items']}\n\n"
    
    report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    report += f"*💡 AI Weekly Insights*\n{ai_suggestions}\n\n"
    report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    report += "_Reply @Cursor for full interactive weekly reflection_"
    
    return report


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
    
    if command == "briefing":
        report = generate_daily_briefing(config)
        post_to_slack(config, report, "Daily Briefing")
    elif command == "closing":
        report = generate_daily_closing(config)
        post_to_slack(config, report, "Daily Closing")
    elif command == "weekly":
        report = generate_weekly_review(config)
        post_to_slack(config, report, "Weekly Review")
    else:
        print(f"Unknown command: {command}")
        print("Available commands: briefing, closing, weekly")
        sys.exit(1)


if __name__ == "__main__":
    main()

