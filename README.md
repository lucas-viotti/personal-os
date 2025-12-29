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
2. Add Bot Token Scopes: `chat:write`, `im:write`
3. Install to your workspace and copy the Bot Token
4. Add GitHub Secrets:
   - `SLACK_BOT_TOKEN`: Your bot token (starts with `xoxb-`)
   - `SLACK_CHANNEL_ID`: Target channel/DM ID

#### AI-Powered Analysis
Works with any OpenAI-compatible API (OpenAI, Azure OpenAI, Anthropic via proxy, local LLMs like Ollama):
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

## 📬 Automated Slack Reports

### ☀️ Daily Briefing (Morning)

Start your day with focus recommendations:

```
☀️ Daily Briefing — January 15, 2025

📊 Today's Focus
• 🚨 P0 (Do Today): 2
• ⚡ P1 (This Week): 5
• 🟠 Blocked: 1

🚨 P0 Tasks (Do Today)
• 🟡 Complete quarterly report
• 🔴 Review PR feedback

💡 AI Focus Recommendation
Based on your priorities and recent activity, focus on completing
the quarterly report first—it's been in progress for 3 days. 
The PR feedback review can be done in the afternoon after 
your 2pm meeting.
```

### 🌆 Daily Closing (End of Day)

Log what you accomplished:

```
🌆 Daily Closing — January 15, 2025

📊 Today's Activity
• 📋 Jira tickets: 4
• 📝 Confluence pages: 2

📋 Jira Activity
• PROJ-123: Updated sprint planning docs [Done]
• PROJ-124: Fixed login bug [In Review]

💡 Suggested Task Updates
1. Task "Sprint planning" — You edited the planning doc today.
   Consider updating status from 🔴 to 🟡 in progress.
2. Task "Bug fixes" — PROJ-124 is in review. Log progress?
```

### 📋 Weekly Review (Fridays)

Reflect on your week with AI insights:

```
📋 Weekly Review — Week of January 15, 2025

📊 This Week's Activity
• 📋 Jira: 12 touched, 5 resolved
• 📝 Confluence: 8 pages edited
• 📁 Task commits: 15

📈 Task Overview
• 🚨 P0 (Critical): 2
• ⚡ P1 (This Week): 5
• 🟠 Blocked: 1
• ✅ Done: 3

💡 AI Weekly Insights
Great progress this week! You resolved 5 Jira tickets and made
significant documentation updates. Consider archiving the 3 
completed tasks. The blocked "API integration" task has been 
stuck for 5 days—schedule time to unblock it next week.
```

---

## ⏰ Schedule Customization

Edit the cron schedules in `.github/workflows/`:

| Workflow | Default Schedule | File |
|----------|------------------|------|
| Daily Briefing | 8:30 AM UTC | `daily-briefing.yml` |
| Daily Closing | 5:50 PM UTC | `daily-closing.yml` |
| Weekly Review | Friday 3:00 PM UTC | `weekly-review.yml` |

### Common Timezone Conversions

| Your Timezone | Briefing (8:30 AM local) | Closing (5:50 PM local) |
|---------------|--------------------------|-------------------------|
| **EST (UTC-5)** | `30 13 * * 1-5` | `50 22 * * 1-5` |
| **PST (UTC-8)** | `30 16 * * 1-5` | `50 1 * * 2-6` |
| **BRT (UTC-3)** | `30 11 * * 1-5` | `50 20 * * 1-5` |
| **CET (UTC+1)** | `30 7 * * 1-5` | `50 16 * * 1-5` |
| **JST (UTC+9)** | `30 23 * * 0-4` | `50 8 * * 1-5` |

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
| `SLACK_CHANNEL_ID` | For Slack | Target channel or DM ID |
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
├── Tasks/                       # Active tasks
├── Archive/                     # Completed tasks by month
├── Knowledge/                   # Reference docs & notes
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
- Include documentation
- Follow existing patterns

---

## 📫 Contact

- **Fork Author**: [Lucas Viotti](https://github.com/lucas-viotti)
- **Original Author**: [Aman Khan](https://github.com/amanaiproduct)
