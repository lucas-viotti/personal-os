#!/bin/bash
#
# 🔔 Setup Slack Enrichment Reminder
#
# This script installs a simple reminder that pops up after your
# Daily Briefing/Closing/Weekly Review is posted to Slack.
#
# The reminder opens Cursor with a pre-copied prompt to search
# your Slack and add context to your Logbook thread.
#
# NO CODING REQUIRED - Just click "Open Cursor" and paste!
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_PATH="$(dirname "$SCRIPT_DIR")"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_NAME="com.logbook.enrich.plist"

echo ""
echo "🔔 Slack Enrichment Reminder Setup"
echo "==================================="
echo ""
echo "This will install a reminder that appears after your Logbook posts."
echo "When it appears, just click 'Open Cursor' and paste the prompt!"
echo ""

# Create LaunchAgents directory if needed
mkdir -p "$LAUNCH_AGENTS_DIR"

# Unload if already installed
launchctl unload "$LAUNCH_AGENTS_DIR/$PLIST_NAME" 2>/dev/null || true

# Copy plist and update paths
sed "s|REPO_PATH|$REPO_PATH|g" "$SCRIPT_DIR/launchd/$PLIST_NAME" > "$LAUNCH_AGENTS_DIR/$PLIST_NAME"

echo "✅ Installed reminder"
echo ""

# Load the agent
launchctl load "$LAUNCH_AGENTS_DIR/$PLIST_NAME"

echo "✅ Activated!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📅 Reminder will appear at these times:"
echo ""
echo "   ☀️  8:32 AM  — After Daily Briefing (Mon-Fri)"
echo "   🌆  5:52 PM  — After Daily Closing (Mon-Fri)"
echo "   📋  4:02 PM  — After Weekly Review (Fridays)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔄 When the reminder appears:"
echo ""
echo "   1. Click 'Open Cursor'"
echo "   2. Press Cmd+V to paste the prompt"
echo "   3. Cursor will search your Slack and post to your thread!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🧪 Test it now:"
echo ""
echo "   launchctl start com.logbook.enrich"
echo ""
echo "🔧 To uninstall:"
echo ""
echo "   launchctl unload ~/Library/LaunchAgents/$PLIST_NAME"
echo "   rm ~/Library/LaunchAgents/$PLIST_NAME"
echo ""
