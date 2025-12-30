# PersonalOS (Enhanced Fork)

> AI-powered task management with **automated Slack notifications**, **AI-driven insights**, and **task archiving**

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

This is an enhanced fork of [amanaiproduct/personal-os](https://github.com/amanaiproduct/personal-os) with additional features for **AI-powered daily briefings**, **automated weekly reviews**, and **task lifecycle management**.

---

## ✨ What's New in This Fork

| Feature | Description |
|---------|-------------|
| ☀️ **Daily Briefing** | Morning focus recommendations with AI-powered suggestions |
| 🌆 **Daily Closing** | End-of-day activity summary with smart task update suggestions |
| 📋 **Weekly Reviews** | Comprehensive weekly digest with AI insights and reflection prompts |
| 💬 **Slack Enrichment** | One-click Slack context added to your reports |
| 🗂️ **Task Archiving** | Move completed tasks to organized monthly archives |
| 🤖 **AI Integration** | Works with any OpenAI-compatible LLM API |
| 🔗 **Atlassian Integration** | Optional Jira & Confluence activity tracking |

---

## 🚀 Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/lucas-viotti/personal-os.git
cd personal-os
./setup.sh
```

### 2. Configure Integrations (All Optional)

#### Slack Notifications
1. Create a Slack App at [api.slack.com/apps](https://api.slack.com/apps)
2. Add Bot Token Scopes: `chat:write`, `im:write`, `im:history`
3. Install to your workspace and copy the Bot Token
4. Add GitHub Secrets:
   - `SLACK_BOT_TOKEN`: Your bot token (starts with `xoxb-`)
   - `SLACK_CHANNEL_ID`: Your Slack user ID (starts with `U`)

#### AI-Powered Analysis
Works with any LLM Provider API (OpenAI, Azure OpenAI, Anthropic via proxy, local LLMs like Ollama):
- `LLM_API_KEY`: Your API key
- `LLM_API_URL`: (Optional) API endpoint URL (defaults to OpenAI)

#### Atlassian Integration (Jira & Confluence)
1. Create an API token at [id.atlassian.com](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Add GitHub Secrets:
   - `ATLASSIAN_EMAIL`: Your Atlassian email
   - `ATLASSIAN_API_TOKEN`: Your API token
3. Configure in workflow files:
   - `ATLASSIAN_DOMAIN`: e.g., `your-company.atlassian.net`
   - `JIRA_PROJECT`: e.g., `PROJ`
   - `CONFLUENCE_SPACES`: e.g., `TEAM,DOCS`

### 3. Start Using It

```
# In your AI assistant (Claude, Cursor, etc.)
"Read AGENTS.md and help me get organized"
```

---

## 💬 Slack Enrichment (NEW!)

After each report posts to Slack, you can **add context from your Slack messages** with one click!

### How It Works

```
8:30 AM   GitHub Action posts Daily Briefing to Slack
          ↓
8:32 AM   Dialog appears on your Mac:
          ┌─────────────────────────────────────┐
          │  📓 Logbook Posted!                 │
          │                                     │
          │  [ Close ]  [ Open Cursor ]         │
          └─────────────────────────────────────┘
          ↓
          Click "Open Cursor" → Paste → Done!
          ↓
          Cursor searches your Slack and posts
          a summary to your Logbook thread
```

### Setup (One Command)

```bash
chmod +x scripts/setup-enrichment.sh && ./scripts/setup-enrichment.sh
```

That's it! The reminder will appear automatically after each report.

### What Gets Added

The Slack enrichment finds relevant updates from your messages:
- Task-related discussions
- Action items mentioned
- Important decisions
- Follow-ups needed

All summarized and posted as a thread reply to your Logbook message.

---

## 📬 Automated Slack Reports

### ☀️ Daily Briefing (Morning)

Start your day with focus recommendations:

```
☀️ Daily Briefing — January 15, 2025

🚨 P0 Tasks (Do Today)
🔴 Not started
• Complete quarterly report
🟡 In Progress
• Review PR feedback

⚡ P1 Tasks (This Week)
🔴 Not started
• Update documentation
🟡 In Progress
• Sprint planning

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 AI Focus Recommendation
Based on prioritization rules, your current priorities 
and recent activity, here's what to focus on:

• 🔴 Complete quarterly report
  This has a hard deadline today and is blocking the 
  team's planning session tomorrow.

• 🟡 Review PR feedback
  Quick win - can be done between meetings.
```

### 🌆 Daily Closing (End of Day)

Log what you accomplished:

```
📊 Daily Closing — January 15, 2025

📈 Today's Progress
• 📋 PROJ-123: Status changed Open → In Review
• 📝 Sprint Planning doc: Added acceptance criteria

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Task Status
🚨 P0 Tasks (Do Today): Quarterly report completed!
⚡ P1 Tasks (This Week): Sprint planning on track.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 Suggested Task Updates
• 🟡 Task "Sprint planning" — PROJ-123 moved to review.
  Update task status from 🔴 to 🟡.
```

### 📋 Weekly Review (Fridays)

Reflect on your week with AI insights:

```
📅 Weekly Review — Week of January 15, 2025

📈 This Week's Activity
• 📋 Jira: 12 tickets touched, 5 resolved
• 📝 Confluence: 8 pages edited

📋 Task Overview
• 🚨 P0: 2 | ⚡ P1: 5 | 🟠 Blocked: 1 | ✅ Done: 3

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 Weekly Reflection
Great progress this week! You resolved 5 Jira tickets 
and made significant documentation updates. Consider 
archiving the 3 completed tasks.
```

---

## ⏰ Schedule Customization

Edit the cron schedules in `.github/workflows/`:

| Workflow | Default Schedule | File |
|----------|------------------|------|
| Daily Briefing | 8:30 AM UTC | `daily-briefing.yml` |
| Daily Closing | 5:50 PM UTC | `daily-closing.yml` |
| Weekly Review | Friday 4:00 PM UTC | `weekly-review.yml` |

### Common Timezone Conversions

| Your Timezone | Briefing (8:30 AM local) | Closing (5:50 PM local) |
|---------------|--------------------------|-------------------------|
| **EST (UTC-5)** | `30 13 * * 1-5` | `50 22 * * 1-5` |
| **PST (UTC-8)** | `30 16 * * 1-5` | `50 1 * * 2-6` |
| **BRT (UTC-3)** | `30 11 * * 1-5` | `50 20 * * 1-5` |
| **CET (UTC+1)** | `30 7 * * 1-5` | `50 16 * * 1-5` |
| **JST (UTC+9)** | `30 23 * * 0-4` | `50 8 * * 1-5` |

---

## 🎯 AI Prioritization Rules

The AI uses configurable prioritization rules from `Knowledge/prioritization-rules.md`:

```markdown
## Stack Ranking (Highest to Lowest Priority)

### 1. 🚨 Hard Deadlines
Tasks with explicit due dates today or overdue

### 2. 🔗 Blocking Others
Work that teammates are waiting on

### 3. 🎯 Strategic Goal Alignment
Tasks directly tied to quarterly objectives

### 4. 📈 Momentum & Progress
Continue tasks already in progress

### 5. ⚠️ Risk & Dependencies
Address blockers and dependencies

### 6. 🧠 Cognitive Load Matching
Match task complexity to energy levels
```

Edit this file to customize how the AI prioritizes your work!

---

## 🗂️ Task Archiving

Keep your `Tasks/` folder clean by archiving completed work:

```
"Archive my completed tasks"
```

Tasks are organized by completion month:

```
Archive/
├── 2025-01/
│   └── task-001-feature-launch.md
├── 2025-02/
│   └── task-015-bug-fix.md
```

---

## 🔧 Configuration Reference

### GitHub Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `SLACK_BOT_TOKEN` | For Slack | Bot token from Slack app |
| `SLACK_CHANNEL_ID` | For Slack | Your Slack user ID |
| `LLM_API_KEY` | For AI | API key for LLM provider |
| `LLM_API_URL` | Optional | Custom API endpoint (default: OpenAI) |
| `ATLASSIAN_EMAIL` | For Jira/Confluence | Your Atlassian email |
| `ATLASSIAN_API_TOKEN` | For Jira/Confluence | API token from Atlassian |

### Workflow Environment Variables

Edit in `.github/workflows/*.yml`:

```yaml
env:
  # Atlassian (optional)
  ATLASSIAN_DOMAIN: "your-company.atlassian.net"
  JIRA_PROJECT: "PROJ"
  CONFLUENCE_SPACES: "TEAM,DOCS"
  
  # LLM Model
  LLM_MODEL: "gpt-4"  # or "gpt-3.5-turbo", "claude-3-opus", etc.
```

---

## 📁 Directory Structure

```
personal-os/
├── .github/
│   └── workflows/
│       ├── daily-briefing.yml   # ☀️ Morning focus
│       ├── daily-closing.yml    # 🌆 EOD summary
│       └── weekly-review.yml    # 📋 Weekly reflection
├── scripts/
│   ├── logbook-local.py         # Local script alternative
│   ├── setup-enrichment.sh      # Slack enrichment setup
│   └── README.md                # Local scripts guide
├── Tasks/                       # Active tasks
├── Archive/                     # Completed tasks by month
├── Knowledge/
│   └── prioritization-rules.md  # AI prioritization config
├── examples/
│   └── workflows/               # Workflow documentation
├── BACKLOG.md                   # Quick capture inbox
├── GOALS.md                     # Your goals & priorities
├── AGENTS.md                    # AI assistant instructions
└── README.md
```

---

## 🔄 Upgrade Path

This fork is designed for extensibility:

### Current (Option 1): Context Injection
- Gathers data from configured sources
- Sends to LLM in a single prompt
- Fast, predictable, low-cost (~$0.02/run)

### Future (Option 2): Agentic Mode
The modular architecture supports upgrading to agentic workflows where:
- LLM can request additional data dynamically
- Multi-step reasoning for complex analysis
- Function calling for automated task updates

---

## 📖 Original Features

All original PersonalOS features are preserved:

- ✅ Goal-driven prioritization
- ✅ Smart task deduplication
- ✅ Natural language processing
- ✅ Session evaluations
- ✅ MCP server integration
- ✅ Knowledge base management

See the [original repo](https://github.com/amanaiproduct/personal-os) for full documentation.

---

## 🙏 Attribution

This project is based on [PersonalOS](https://github.com/amanaiproduct/personal-os) by Aman Khan.

Licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).

---

## 🤝 Contributing

Contributions welcome! Please:
- Keep personal information out of commits
- Make features generic and configurable
- Include documentation for non-technical users
- Follow existing patterns

---

## 📫 Contact

- **Fork Author**: [Lucas Viotti](https://github.com/lucas-viotti)
- **Original Author**: [Aman Khan](https://github.com/amanaiproduct)
