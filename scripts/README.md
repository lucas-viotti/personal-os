# 🖥️ Local Scripts for PersonalOS

This folder contains scripts that enhance your PersonalOS experience with **local automation**.

---

## 🎯 Quick Start (5 minutes)

### Option A: Just Want the Slack Reminder? (Easiest)

If you're using GitHub Actions for your reports and just want the **Slack enrichment reminder**:

```bash
# One command setup
chmod +x scripts/setup-enrichment.sh && ./scripts/setup-enrichment.sh
```

That's it! A reminder will pop up after each report asking if you want to add Slack context.

---

### Option B: Full Local Setup

Run everything locally instead of GitHub Actions:

#### 1. Copy the environment template

```bash
cp scripts/env.example scripts/.env
```

#### 2. Fill in your credentials

Open `scripts/.env` in any text editor and fill in:

```bash
# Required for Slack notifications
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_CHANNEL_ID=U1234567890  # Your Slack user ID

# Required for AI analysis
LLM_API_KEY=your-openai-key
LLM_API_URL=https://api.openai.com  # Or your LLM provider

# Optional: Jira/Confluence integration
ATLASSIAN_DOMAIN=your-company.atlassian.net
ATLASSIAN_EMAIL=you@company.com
ATLASSIAN_API_TOKEN=your-token
JIRA_PROJECT=PROJ
CONFLUENCE_SPACES=TEAM,DOCS
```

#### 3. Install the scheduled jobs

```bash
chmod +x scripts/setup-local.sh
./scripts/setup-local.sh install
```

---

## 📱 Slack Enrichment: Add Context with One Click

After your Daily Briefing/Closing posts to Slack, a dialog appears:

```
┌─────────────────────────────────────────┐
│  📓 Logbook Posted!                     │
├─────────────────────────────────────────┤
│                                         │
│  Logbook was just posted to Slack!      │
│                                         │
│  Add Slack context by asking Cursor     │
│  to search your messages.               │
│                                         │
│          [ Close ]  [ Open Cursor ]     │
└─────────────────────────────────────────┘
```

### What happens when you click "Open Cursor":

1. ✅ A prompt is copied to your clipboard
2. ✅ Cursor IDE opens
3. 📋 **Just paste** (Cmd+V) in Cursor's chat
4. 🤖 Cursor automatically:
   - Searches your Slack messages
   - Finds task-related updates
   - Posts a summary to your Logbook thread
   - Cleans up the temp file

**No coding required!** Just click and paste.

---

## 📋 Available Commands

Run these manually anytime:

| Command | What it does |
|---------|--------------|
| `python3 scripts/logbook-local.py briefing` | Generate morning briefing |
| `python3 scripts/logbook-local.py closing` | Generate end-of-day report |
| `python3 scripts/logbook-local.py weekly` | Generate weekly review |
| `python3 scripts/logbook-local.py enrich` | Show Slack enrichment prompt |
| `python3 scripts/logbook-local.py post-context` | Post saved context to thread |

---

## ⏰ Schedule Reference

### Default Schedule (GitHub Actions)

| Report | Time | Days |
|--------|------|------|
| ☀️ Daily Briefing | 8:30 AM | Mon-Fri |
| 🌆 Daily Closing | 5:50 PM | Mon-Fri |
| 📋 Weekly Review | 4:00 PM | Friday |

### Slack Enrichment Reminder

The reminder pops up **2 minutes after** each report:

| Report | Reminder Time |
|--------|---------------|
| ☀️ After Briefing | 8:32 AM |
| 🌆 After Closing | 5:52 PM |
| 📋 After Weekly | 4:02 PM (Fri) |

---

## 🔧 Customization

### Change Reminder Times

Edit `scripts/launchd/com.logbook.enrich.plist`:

```xml
<key>StartCalendarInterval</key>
<array>
    <dict>
        <key>Hour</key>
        <integer>9</integer>  <!-- Change to 9 AM -->
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    ...
</array>
```

Then reinstall:

```bash
./scripts/setup-enrichment.sh
```

### Skip the Reminder

Just close the dialog - nothing happens. The prompt isn't saved anywhere.

---

## 🐛 Troubleshooting

### "Reminder never appears"

Check if it's loaded:
```bash
launchctl list | grep logbook.enrich
```

If not listed, reinstall:
```bash
./scripts/setup-enrichment.sh
```

### "Cursor doesn't have Slack MCP"

The enrichment feature requires Cursor's Slack MCP integration. If your company doesn't have this set up, you can still:

1. Manually search your Slack
2. Write a summary to `scripts/.slack-context.md`
3. Run `python3 scripts/logbook-local.py post-context`

### "Bot can't post to Slack"

Make sure your Slack Bot Token has these scopes:
- `chat:write` - Send messages
- `im:write` - Send DMs
- `im:history` - Read DM history (for finding the thread)

### View logs

```bash
# Check if the reminder ran
cat /tmp/com.logbook.enrich.stdout

# Check for errors
cat /tmp/com.logbook.enrich.stderr
```

---

## 📁 File Structure

```
scripts/
├── logbook-local.py      # Main script for all reports
├── env.example           # Template for credentials
├── .env                  # Your credentials (git-ignored)
├── .slack-context.md     # Temp file for Slack summaries (git-ignored)
├── setup-local.sh        # Full local mode setup
├── setup-enrichment.sh   # Slack reminder setup
├── README.md             # This file
└── launchd/
    ├── com.logbook.briefing.plist   # Schedule for briefing
    ├── com.logbook.closing.plist    # Schedule for closing  
    ├── com.logbook.weekly.plist     # Schedule for weekly
    └── com.logbook.enrich.plist     # Slack enrichment reminder
```

---

## 🤝 Contributing

When adding features, follow the **public-first pattern**:

1. Make changes in the public repo first
2. Keep everything generic (no company-specific values)
3. Use environment variables for configuration
4. Update documentation for non-technical users
