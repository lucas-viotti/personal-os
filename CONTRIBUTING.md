# Contributing to PersonalOS

Thank you for your interest in contributing! This document outlines the development patterns and guidelines for this project.

---

## 🏗️ Architecture: Public vs Private

This project is designed to be used in a **two-repo setup**:

| Repository | Purpose | Contains |
|------------|---------|----------|
| **Public** (this repo) | Portfolio, sharing, collaboration | Generic workflows, example files, documentation |
| **Private** (your fork) | Actual daily use | Real tasks, confidential context, organization-specific config |

### Why Two Repos?

1. **Privacy**: Your tasks, goals, and knowledge files may contain sensitive information
2. **Portfolio**: The public repo showcases your productivity system and technical skills
3. **Reusability**: Generic code can be shared; specific config stays private

---

## 📋 Development Workflow: Public First

**All improvements MUST be developed in the public repo first.**

```
┌─────────────────┐    Pull/Merge     ┌─────────────────┐
│   PUBLIC REPO   │ ─────────────────▶│   PRIVATE REPO  │
│ (generic code)  │                   │ (your config)   │
└─────────────────┘                   └─────────────────┘
        │                                      │
        ▼                                      ▼
  ✅ Workflows                         ✅ Same workflows
  ✅ Example tasks                     ✅ Real tasks
  ✅ Documentation                     ✅ Real knowledge
  ✅ Empty config vars                 ✅ Filled config vars
  ❌ No hardcoded domains              ✅ Your org's domains
  ❌ No real API keys                  ✅ Your API keys (secrets)
```

### Step-by-Step

1. **Make changes in PUBLIC repo**
2. **Test with example files** (the `Tasks/example-*.md` files)
3. **Commit and push** to public
4. **Pull into PRIVATE repo**
5. **Configure secrets/env vars** for your organization

---

## ✅ Code Standards for Public Repo

### DO ✅

```yaml
# Use environment variables for configuration
env:
  ATLASSIAN_DOMAIN: ""  # User configures this
  JIRA_PROJECT: ""      # Empty = feature disabled
  
# Use secrets for sensitive data
${{ secrets.ATLASSIAN_API_TOKEN }}
${{ secrets.LLM_API_KEY }}

# Graceful fallbacks for optional features
if: ${{ env.ATLASSIAN_DOMAIN != '' }}

# Include example/sample files for testing
Tasks/example-task-001.md
```

### DON'T ❌

```yaml
# ❌ No hardcoded domains
ATLASSIAN_DOMAIN: "company.atlassian.net"

# ❌ No organization-specific project keys
JIRA_PROJECT: "MYTEAM"

# ❌ No internal API URLs
API_URL: "https://internal-api.company.com"

# ❌ No references to files that only exist in private repo
GOALS.md  # (unless public has example version)
```

---

## 📁 Files That Belong Where

### Public Repo (Generic)
- `.github/workflows/*.yml` — automation (generic config)
- `AGENTS.md` — AI assistant instructions
- `Tasks/example-*.md` — sample tasks for testing
- `Knowledge/README.md` — placeholder
- `examples/` — tutorials, workflow docs

### Private Repo Only (Personal)
- `Tasks/*.md` — your real tasks
- `Knowledge/*.md` — your real knowledge base
- `GOALS.md` — your real goals
- `BACKLOG.md` — your real backlog
- `Archive/` — your archived tasks

---

## 🔧 Configurable Elements

When adding new features, make them configurable via:

### 1. Environment Variables (workflow-level)
```yaml
env:
  FEATURE_ENABLED: ""  # Empty string = disabled
  FEATURE_OPTION: "default"
```

### 2. GitHub Secrets (sensitive)
```yaml
${{ secrets.API_KEY }}
${{ secrets.ORG_DOMAIN }}
```

### 3. Conditionals (feature flags)
```yaml
- name: Optional Feature Step
  if: ${{ env.FEATURE_ENABLED != '' }}
  run: ...
```

---

## 🧪 Testing Changes

Before submitting a PR:

1. **Manually trigger workflows** via `workflow_dispatch`
2. **Check all conditional steps** handle empty config gracefully
3. **Verify example tasks** are processed correctly
4. **Test without secrets** — features should degrade gracefully

---

## 📝 PR Checklist

- [ ] No hardcoded domains or organization-specific values
- [ ] All configuration via env vars or secrets
- [ ] Example files included if workflow depends on file structure
- [ ] README updated if adding new features
- [ ] Graceful fallbacks for optional integrations

---

## 🙏 Attribution

This project is based on [PersonalOS](https://github.com/amanaiproduct/personal-os) by Aman Khan.

Licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).

