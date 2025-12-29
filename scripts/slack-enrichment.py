#!/usr/bin/env python3
"""
Slack Thread Enrichment Script

Runs after GitHub Actions to add Slack context to the same thread.
This script finds the most recent Logbook message and replies with Slack activity.

Usage:
    python slack-enrichment.py --mode briefing|closing|weekly

The script will:
1. Find the most recent Logbook bot message
2. Reply to that thread with Slack activity summary
3. Either fetch via Slack MCP (if configured) or post a prompt to engage

Requirements:
- SLACK_BOT_TOKEN: Bot token for posting (same as GitHub Actions)
- SLACK_CHANNEL_ID: Your DM channel ID (same as GitHub Actions)
- SLACK_USER_TOKEN (optional): User token for reading messages
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

try:
    import requests
except ImportError:
    print("Installing requests...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests


def load_env():
    """Load environment from .env file if present."""
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())


def find_logbook_thread(bot_token: str, channel_id: str, mode: str) -> Optional[str]:
    """
    Find the most recent Logbook message thread_ts.
    
    Args:
        bot_token: Slack bot token
        channel_id: DM channel ID
        mode: briefing, closing, or weekly
        
    Returns:
        thread_ts if found, None otherwise
    """
    headers = {
        "Authorization": f"Bearer {bot_token}",
        "Content-Type": "application/json"
    }
    
    # Get recent messages from the channel
    response = requests.get(
        "https://slack.com/api/conversations.history",
        headers=headers,
        params={
            "channel": channel_id,
            "limit": 20  # Check last 20 messages
        }
    )
    
    if not response.ok:
        print(f"Error fetching messages: {response.status_code}")
        return None
    
    data = response.json()
    if not data.get("ok"):
        print(f"Slack API error: {data.get('error')}")
        return None
    
    # Look for Logbook messages based on mode
    mode_keywords = {
        "briefing": ["Daily Briefing", "☀️"],
        "closing": ["Daily Closing", "📊"],
        "weekly": ["Weekly Review", "📅"]
    }
    
    keywords = mode_keywords.get(mode, ["Daily Briefing"])
    
    # Find today's date for matching
    today = datetime.now().strftime("%B %d, %Y")
    
    for message in data.get("messages", []):
        text = message.get("text", "")
        
        # Check if this is a Logbook message
        if any(kw in text for kw in keywords):
            # Prefer messages from today
            if today in text:
                return message.get("ts")
    
    # If no today match, return most recent matching message
    for message in data.get("messages", []):
        text = message.get("text", "")
        if any(kw in text for kw in keywords):
            return message.get("ts")
    
    return None


def fetch_slack_activity_via_mcp() -> Optional[str]:
    """
    Try to fetch Slack activity via MCP or user token.
    
    Returns:
        Formatted Slack activity or None if not available
    """
    # Check for user token (allows reading messages)
    user_token = os.getenv("SLACK_USER_TOKEN")
    
    if not user_token:
        return None
    
    headers = {
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json"
    }
    
    # Search for messages from/to user in last 24h
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    response = requests.get(
        "https://slack.com/api/search.messages",
        headers=headers,
        params={
            "query": f"from:me after:{yesterday}",
            "count": 20,
            "sort": "timestamp"
        }
    )
    
    if not response.ok or not response.json().get("ok"):
        return None
    
    messages = response.json().get("messages", {}).get("matches", [])
    
    if not messages:
        return "_No significant Slack activity found_"
    
    # Format the results
    activity = []
    channels_mentioned = set()
    
    for msg in messages[:10]:  # Limit to 10
        channel = msg.get("channel", {}).get("name", "DM")
        channels_mentioned.add(channel)
    
    if channels_mentioned:
        return f"Active in {len(channels_mentioned)} channels: {', '.join(list(channels_mentioned)[:5])}"
    
    return "_No significant Slack activity found_"


def post_thread_reply(bot_token: str, channel_id: str, thread_ts: str, message: str) -> bool:
    """
    Post a reply to the Logbook thread.
    
    Args:
        bot_token: Slack bot token
        channel_id: DM channel ID
        thread_ts: Thread timestamp to reply to
        message: Message to post
        
    Returns:
        True if successful
    """
    headers = {
        "Authorization": f"Bearer {bot_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "channel": channel_id,
        "thread_ts": thread_ts,
        "text": message,
        "unfurl_links": False
    }
    
    response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers=headers,
        json=payload
    )
    
    if not response.ok:
        print(f"Error posting message: {response.status_code}")
        return False
    
    data = response.json()
    if not data.get("ok"):
        print(f"Slack API error: {data.get('error')}")
        return False
    
    return True


def build_enrichment_message(mode: str, slack_activity: Optional[str]) -> str:
    """
    Build the thread enrichment message.
    
    Args:
        mode: briefing, closing, or weekly
        slack_activity: Fetched Slack activity or None
        
    Returns:
        Formatted message
    """
    if slack_activity:
        # We have Slack data!
        message = f"*💬 Slack Activity Summary*\n\n{slack_activity}\n\n"
        message += "_Reply @Cursor for deeper analysis or to update tasks_"
    else:
        # Prompt user to engage with Cursor for Slack context
        mode_prompts = {
            "briefing": "What Slack threads should I follow up on today?",
            "closing": "What Slack conversations did I have today that need logging?",
            "weekly": "Summarize my key Slack interactions this week"
        }
        
        prompt = mode_prompts.get(mode, "Analyze my recent Slack activity")
        
        message = "*💬 Slack Context*\n\n"
        message += f"_Reply @Cursor to fetch your Slack activity:_\n"
        message += f"> {prompt}"
    
    return message


def main():
    parser = argparse.ArgumentParser(description="Slack Thread Enrichment")
    parser.add_argument(
        "--mode",
        choices=["briefing", "closing", "weekly"],
        default="briefing",
        help="Which report type to enrich"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without posting"
    )
    
    args = parser.parse_args()
    
    # Load environment
    load_env()
    
    # Required config
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    channel_id = os.getenv("SLACK_CHANNEL_ID")
    
    if not bot_token or not channel_id:
        print("Error: SLACK_BOT_TOKEN and SLACK_CHANNEL_ID are required")
        print("Set them in .env file or environment variables")
        sys.exit(1)
    
    print(f"🔍 Finding most recent {args.mode} thread...")
    
    # Find the Logbook thread
    thread_ts = find_logbook_thread(bot_token, channel_id, args.mode)
    
    if not thread_ts:
        print(f"⚠️ Could not find a recent {args.mode} message from Logbook")
        print("The GitHub Action may not have run yet, or the message format changed")
        sys.exit(0)  # Exit gracefully - maybe GH Action hasn't run yet
    
    print(f"✅ Found thread: {thread_ts}")
    
    # Try to fetch Slack activity
    print("📊 Checking for Slack activity data...")
    slack_activity = fetch_slack_activity_via_mcp()
    
    if slack_activity:
        print("✅ Slack activity fetched via user token")
    else:
        print("ℹ️ No user token - will prompt for @Cursor engagement")
    
    # Build the message
    message = build_enrichment_message(args.mode, slack_activity)
    
    if args.dry_run:
        print("\n--- DRY RUN ---")
        print(f"Would post to thread {thread_ts}:")
        print(message)
        return
    
    # Post the reply
    print("📤 Posting thread reply...")
    
    if post_thread_reply(bot_token, channel_id, thread_ts, message):
        print("✅ Slack enrichment posted successfully!")
    else:
        print("❌ Failed to post enrichment message")
        sys.exit(1)


if __name__ == "__main__":
    main()

