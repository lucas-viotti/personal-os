# 🖥️ Logbook Local - Local Script Alternative

This folder contains a **local script alternative** to the GitHub Actions workflows. Use this if you:

- Need **full Slack access** via MCP OAuth (company restrictions on user tokens)
- Want to run reports while connected to **VPN/internal networks**
- Prefer keeping credentials **on your machine** instead of GitHub Secrets
- Have a **Slack MCP** setup (like Nubank's internal slack-mcp-server)

## 📊 Comparison: GitHub Actions vs Local Script

| Feature | GitHub Actions | Local Script |
|---------|---------------|--------------|
| **Runs when laptop is off** | ✅ Yes | ❌ No |
| **Full Slack access** | ❌ Limited | ✅ Yes (via MCP) |
| **VPN/internal access** | ❌ No | ✅ Yes |
| **Secret management** | GitHub Secrets | Local .env |
| **Setup complexity** | Lower | Higher |
| **Portfolio friendly** | ✅ Yes | ⚠️ Local only |

## 🚀 Quick Start

### 1. Configure Environment

```bash
# Copy the example config
cp scripts/env.example .env

# Edit with your credentials
nano .env  # or use your preferred editor
```

### 2. Test the Script

```bash
# Make setup script executable
chmod +x scripts/setup-local.sh

# Run a test
./scripts/setup-local.sh test
```

### 3. Install Scheduled Jobs (macOS)

```bash
# Install launchd jobs for automatic scheduling
./scripts/setup-local.sh install
```

This creates scheduled jobs for:
- **Daily Briefing**: 8:30 AM (Mon-Fri)
- **Daily Closing**: 5:50 PM (Mon-Fri)  
- **Weekly Review**: 3:00 PM (Friday)

### 4. Manual Runs

```bash
# Run any report manually
python3 scripts/logbook-local.py briefing
python3 scripts/logbook-local.py closing
python3 scripts/logbook-local.py weekly
```

## 🔐 Configuration Reference

Create a `.env` file in the repo root with these variables:

```bash
# Atlassian (Jira & Confluence)
ATLASSIAN_DOMAIN=your-company.atlassian.net
ATLASSIAN_EMAIL=your.email@company.com
ATLASSIAN_API_TOKEN=your-token
JIRA_PROJECT=PROJ
CONFLUENCE_SPACES=TEAM,DOCS

# LLM (OpenAI-compatible API)
LLM_API_URL=https://api.openai.com
LLM_API_KEY=your-key
LLM_MODEL=gpt-4o-mini

# Slack
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_CHANNEL_ID=U1234567890

# Optional: For full Slack access
SLACK_USER_TOKEN=xoxp-your-user-token
# OR
SLACK_MCP_TOKEN_PATH=~/.slack-mcp/token.json
```

## 🔗 Slack MCP Integration (Nubank)

If you have access to a Slack MCP server (like Nubank's internal `slack-mcp-server`), you can leverage its OAuth token for full Slack access:

### Option A: Token File Path

If your MCP stores tokens in a file:

```bash
SLACK_MCP_TOKEN_PATH=~/dev/nu/slack-mcp-server/.token.json
```

### Option B: macOS Keychain

The script automatically checks for tokens stored in macOS Keychain under the service name `slack-mcp`.

### Option C: Manual Token Extraction

If you need to manually extract the token:

1. Run your Slack MCP server
2. Complete the OAuth flow
3. Check where tokens are stored (varies by implementation)
4. Either copy the token to `SLACK_USER_TOKEN` or set `SLACK_MCP_TOKEN_PATH`

## 📁 File Structure

```
scripts/
├── logbook-local.py      # Main script
├── env.example           # Configuration template
├── setup-local.sh        # Setup/installation script
├── README.md             # This file
└── launchd/              # macOS scheduler configs
    ├── com.logbook.briefing.plist
    ├── com.logbook.closing.plist
    └── com.logbook.weekly.plist
```

## 🔧 Customization

### Change Schedule Times

Edit the plist files in `scripts/launchd/` before installing:

```xml
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>9</integer>  <!-- Change hour here -->
    <key>Minute</key>
    <integer>0</integer>  <!-- Change minute here -->
</dict>
```

Then reinstall:

```bash
./scripts/setup-local.sh uninstall
./scripts/setup-local.sh install
```

### Linux/Windows

The script itself (`logbook-local.py`) works on any OS. Only the scheduling differs:

- **Linux**: Use cron instead of launchd
  ```bash
  # Add to crontab -e
  30 8 * * 1-5 cd /path/to/repo && python3 scripts/logbook-local.py briefing
  50 17 * * 1-5 cd /path/to/repo && python3 scripts/logbook-local.py closing
  0 15 * * 5 cd /path/to/repo && python3 scripts/logbook-local.py weekly
  ```

- **Windows**: Use Task Scheduler

## 🐛 Troubleshooting

### Check if jobs are running

```bash
./scripts/setup-local.sh status
```

### View logs

```bash
cat logs/briefing.log
cat logs/briefing.error.log
```

### Test without posting to Slack

Remove or comment out `SLACK_BOT_TOKEN` in `.env` - the script will print the message instead of posting.

### "Slack search requires user token"

This means only `SLACK_BOT_TOKEN` is configured. For full Slack access, you need either:
- `SLACK_USER_TOKEN` with `search:read` scope
- `SLACK_MCP_TOKEN_PATH` pointing to your MCP's token
- A working Slack MCP OAuth integration

## 🤝 Contributing

When adding features to the local script, please also update the GitHub Actions workflows to maintain parity where possible. See [CONTRIBUTING.md](../CONTRIBUTING.md) for the public-first development pattern.

