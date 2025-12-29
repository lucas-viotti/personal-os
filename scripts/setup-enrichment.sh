#!/bin/bash
#
# Setup Slack Enrichment Local Agents
#
# This script installs launchd agents that run AFTER GitHub Actions
# to add Slack context to the same thread.
#
# The enrichment script will:
# 1. Find the most recent Logbook message
# 2. Reply to that thread with Slack context
# 3. Prompt for @Cursor engagement if user token not available
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"

echo "🔧 Slack Enrichment Setup"
echo "========================="
echo ""
echo "This will install launchd agents that run 5 minutes after each GitHub Action"
echo "to add Slack context to the same Logbook thread."
echo ""

# Check for .env file
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "⚠️  No .env file found. Creating from template..."
    if [ -f "$SCRIPT_DIR/env.example" ]; then
        cp "$SCRIPT_DIR/env.example" "$SCRIPT_DIR/.env"
        echo "   Created .env from env.example"
        echo ""
        echo "📝 Please edit $SCRIPT_DIR/.env with your credentials:"
        echo "   - SLACK_BOT_TOKEN (same as GitHub Actions)"
        echo "   - SLACK_CHANNEL_ID (same as GitHub Actions)"
        echo "   - SLACK_USER_TOKEN (optional, for reading Slack)"
        echo ""
        read -p "Press Enter after editing .env to continue..."
    else
        echo "❌ No env.example found. Please create .env manually."
        exit 1
    fi
fi

# Source .env to validate
source "$SCRIPT_DIR/.env" 2>/dev/null || true

if [ -z "$SLACK_BOT_TOKEN" ] || [ -z "$SLACK_CHANNEL_ID" ]; then
    echo "❌ Error: SLACK_BOT_TOKEN and SLACK_CHANNEL_ID must be set in .env"
    exit 1
fi

echo "✅ .env file validated"
echo ""

# Create LaunchAgents directory if needed
mkdir -p "$LAUNCH_AGENTS_DIR"

# Install enrichment agents
echo "📦 Installing launchd agents..."

for plist in "$SCRIPT_DIR/launchd/com.logbook.enrichment."*.plist; do
    [ -f "$plist" ] || continue
    
    filename=$(basename "$plist")
    label="${filename%.plist}"
    
    # Unload if already loaded
    launchctl unload "$LAUNCH_AGENTS_DIR/$filename" 2>/dev/null || true
    
    # Update paths in plist
    sed "s|SCRIPT_PATH|$SCRIPT_DIR|g" "$plist" > "$LAUNCH_AGENTS_DIR/$filename"
    
    echo "   ✅ Installed $label"
done

echo ""

# Load agents
echo "🚀 Loading agents..."

for plist in "$LAUNCH_AGENTS_DIR/com.logbook.enrichment."*.plist; do
    [ -f "$plist" ] || continue
    
    filename=$(basename "$plist")
    label="${filename%.plist}"
    
    launchctl load "$plist"
    echo "   ✅ Loaded $label"
done

echo ""
echo "✨ Setup complete!"
echo ""
echo "📅 Enrichment schedule:"
echo "   • Daily Briefing: 8:35 AM Mon-Fri (5 min after GitHub Action)"
echo "   • Daily Closing:  5:55 PM Mon-Fri (5 min after GitHub Action)"
echo "   • Weekly Review:  3:05 PM Fridays (5 min after GitHub Action)"
echo ""
echo "🧪 To test manually:"
echo "   python3 $SCRIPT_DIR/slack-enrichment.py --mode briefing --dry-run"
echo ""
echo "📋 View logs:"
echo "   tail -f /tmp/logbook-enrichment-*.log"
echo ""
echo "🔍 Check status:"
echo "   launchctl list | grep logbook.enrichment"

