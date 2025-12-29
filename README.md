# PersonalOS (Enhanced Fork)

> AI-powered task management with **automated Slack notifications** and **task archiving**

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

This is an enhanced fork of [amanaiproduct/personal-os](https://github.com/amanaiproduct/personal-os) with additional features for **automated daily/weekly reviews** and **task lifecycle management**.

---

## ✨ What's New in This Fork

| Feature | Description |
|---------|-------------|
| 📬 **Daily Slack Reports** | Automated task summaries sent to Slack every workday |
| 📋 **Weekly Reviews** | Comprehensive weekly digest with reflection prompts |
| 🗂️ **Task Archiving** | Move completed tasks to organized monthly archives |
| 🔄 **GitHub Actions** | Fully automated, no manual triggers needed |

---

## 🚀 Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/lucas-viotti/personal-os.git
cd personal-os
./setup.sh
```

### 2. Configure Slack Integration (Optional)

To receive automated reports in Slack:

1. **Create a Slack App** at [api.slack.com/apps](https://api.slack.com/apps)
2. Add Bot Token Scopes: `chat:write`, `chat:write.public`
3. Install to your workspace and copy the Bot Token
4. Add GitHub Secrets:
   - `SLACK_BOT_TOKEN`: Your bot token (starts with `xoxb-`)
   - `SLACK_CHANNEL_ID`: Target channel ID (e.g., `C01ABCD1234`)

### 3. Start Using It

```
# In your AI assistant (Claude, Cursor, etc.)
"Read AGENTS.md and help me get organized"
```

---

## 📬 Automated Slack Reports

### Daily Check (Monday-Friday)

Receive a daily summary at end of workday:

```
🌅 Daily Task Check — January 15, 2025

📊 Task Summary
| Status | Count |
|--------|-------|
| 🔴 Not Started | 3 |
| 🟡 In Progress | 5 |
| 🟠 Blocked | 1 |

🚨 P0 Tasks (Do Today)
- 🟡 Complete quarterly report
- 🔴 Review PR feedback

⚡ P1 Tasks (This Week)
- 🟡 Update documentation
- 🔴 Schedule team sync
```

### Weekly Review (Fridays)

Comprehensive weekly digest with:
- Task status overview
- Activity metrics (commits, files modified)
- Blocked tasks requiring attention
- Tasks ready to archive
- Reflection prompts

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

## 📁 Directory Structure

```
personal-os/
├── .github/
│   └── workflows/
│       ├── daily-check.yml      # 🆕 Daily Slack reports
│       └── weekly-review.yml    # 🆕 Weekly Slack digest
├── Tasks/                       # Active tasks
├── Archive/                     # 🆕 Completed tasks by month
├── Knowledge/                   # Reference docs & notes
├── examples/
│   └── workflows/
│       └── archive-tasks.md     # 🆕 Archive workflow docs
├── BACKLOG.md                   # Quick capture inbox
├── GOALS.md                     # Your goals & priorities
├── AGENTS.md                    # AI assistant instructions
└── README.md
```

---

## 🔧 Customization

### Adjust Notification Schedule

Edit `.github/workflows/daily-check.yml`:

```yaml
schedule:
  # 6:00 PM EST = 23:00 UTC
  - cron: '0 23 * * 1-5'
```

### Common Timezones

| Timezone | Cron (6 PM) |
|----------|-------------|
| EST | `0 23 * * 1-5` |
| PST | `0 2 * * 2-6` |
| BRT | `0 21 * * 1-5` |
| UTC | `0 18 * * 1-5` |

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
