# Jira Sync Implementation Plan

**Version:** 1.0  
**Created:** 2024-12-30  
**Status:** Planning  
**Priority:** P0 — Core differentiating feature

---

## 1. Problem Statement

The PRD (US-3.2) and SPEC (§3.4) define a **one-click Jira sync** feature:

> "If local progress exists but Jira is stale, AI suggests updates with hyperlinked card name. User can approve, edit, or skip each suggested update. On approval, system auto-posts via MCP (fallback: copy to clipboard)."

**Current State:** ❌ Not implemented  
**Gap:** This is the key feature that closes the loop between local work and public visibility.

---

## 2. Feature Requirements (from PRD/SPEC)

### Must Have

| Requirement | Source |
|-------------|--------|
| Detect when local progress > Jira state | PRD US-3.2 |
| Generate comment suggestions with format: `Update YYYY-MM-DD: [summary]` | SPEC §3.4 |
| Generate due date change suggestions when detected | PRD US-3.2 |
| Generate description update suggestions | SPEC §3.4 |
| Generate status transition suggestions | SPEC §3.4 |
| Present each update with **hyperlinked card name** for verification | PRD US-3.2 |
| User can **Approve / Edit / Skip** each update | SPEC §3.2 |
| On approval, auto-execute via Atlassian MCP | PRD US-3.2 |
| Fallback: copy to clipboard if MCP fails | SPEC §3.4 |
| Log executed actions to task Progress Log | SPEC §3.4 |

### Should Have

| Requirement | Source |
|-------------|--------|
| 30-second undo for approved actions | SPEC §3.4 |
| Track approval patterns for learning | SPEC §6 (Q4) |

---

## 3. Architecture Decision

### User Interaction Model

Given the user's workflow (heavy Cursor usage), we propose a **hybrid model**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         JIRA SYNC FLOW                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                 │
│  │ Daily Closing │────▶│   DETECT &   │────▶│   SAVE TO    │                 │
│  │   Workflow    │     │   GENERATE   │     │   PENDING    │                 │
│  │              │     │              │     │    FILE      │                 │
│  └──────────────┘     └──────────────┘     └──────────────┘                 │
│                                                   │                          │
│                                                   ▼                          │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        SLACK NOTIFICATION                              │   │
│  │                                                                        │   │
│  │  "📝 3 Jira updates suggested based on today's progress:"             │   │
│  │  • MRC-3266: Add comment (test case review completed)                 │   │
│  │  • MRC-3266: Update due date (Jan 9 → Jan 16)                         │   │
│  │  • MRC-1912: Add comment (stakeholder alignment)                      │   │
│  │                                                                        │   │
│  │  Run: `python3 scripts/logbook-local.py jira-sync`                    │   │
│  │  Or in Cursor: "Apply my pending Jira updates"                        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                   │                          │
│                     ┌─────────────────────────────┴─────────────────────┐    │
│                     │                                                    │    │
│                     ▼                                                    ▼    │
│  ┌──────────────────────────────┐              ┌──────────────────────────┐  │
│  │    OPTION A: LOCAL CLI       │              │  OPTION B: CURSOR AI     │  │
│  │                              │              │                          │  │
│  │  $ jira-sync                 │              │  User: "Apply my Jira    │  │
│  │                              │              │         updates"         │  │
│  │  [MRC-3266] Beta Rollout     │              │                          │  │
│  │  Comment: "Update 2024-12-30:│              │  AI reads pending file,  │  │
│  │  Completed test case review" │              │  presents each update,   │  │
│  │                              │              │  user approves in chat   │  │
│  │  [A]pprove / [E]dit / [S]kip │              │                          │  │
│  └──────────────────────────────┘              └──────────────────────────┘  │
│                     │                                    │                    │
│                     └─────────────────┬──────────────────┘                    │
│                                       │                                       │
│                                       ▼                                       │
│                        ┌──────────────────────────────┐                      │
│                        │        EXECUTE VIA MCP       │                      │
│                        │                              │                      │
│                        │  • addCommentToJiraIssue     │                      │
│                        │  • editJiraIssue (due date)  │                      │
│                        │  • transitionJiraIssue       │                      │
│                        │                              │                      │
│                        │  Fallback: pbcopy + instruct │                      │
│                        └──────────────────────────────┘                      │
│                                       │                                       │
│                                       ▼                                       │
│                        ┌──────────────────────────────┐                      │
│                        │          LOG & CLEANUP       │                      │
│                        │                              │                      │
│                        │  • Update task Progress Log  │                      │
│                        │  • Save to agent-feedback    │                      │
│                        │  • Clear pending file        │                      │
│                        └──────────────────────────────┘                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Implementation Phases

### Phase 1: Detection Infrastructure ⏱️ ~2 hours

**Goal:** Extract Jira links from tasks, fetch current state, identify gaps.

**Tasks:**

1. **Parse `resource_refs` for Jira links**
   ```python
   def extract_jira_keys(task_file: Path) -> List[str]:
       """Extract Jira keys from resource_refs (e.g., MRC-3266)."""
       # Match URLs like: https://domain.atlassian.net/browse/MRC-3266
       # Also match inline mentions: [MRC-3266]
   ```

2. **Fetch current Jira state for each key**
   ```python
   def fetch_jira_state(config: Dict, jira_key: str) -> Dict:
       """Return: status, last_comment_date, last_changelog_date, description."""
   ```

3. **Parse task Progress Log for local updates**
   ```python
   def parse_progress_log(task_file: Path) -> List[Dict]:
       """Return: list of {date, content} from ## Progress Log section."""
   ```

4. **Compare and identify gaps**
   ```python
   def detect_jira_gaps(task: Dict, jira_state: Dict) -> List[Dict]:
       """Return: list of suggested updates with type and content."""
       # If local_last_update > jira_last_comment: suggest comment
       # If task.due_date != jira.duedate: suggest due_date update
       # If task.status == 'd' and jira.status != 'Done': suggest transition
   ```

**Files to modify:**
- `scripts/logbook-local.py` — Add detection functions
- `scripts/agent_orchestrator.py` — Optionally integrate with Analyzer

---

### Phase 2: Suggestion Generation ⏱️ ~2 hours

**Goal:** Generate smart, formatted suggestions using AI.

**Tasks:**

1. **Enhance Daily Closing to generate Jira suggestions**
   - After summarizing day's progress, check linked Jira cards
   - Use LLM to generate comment text in standard format
   - Detect implicit due date changes from Slack context

2. **Create suggestion schema**
   ```yaml
   # scripts/.jira-sync-pending.yaml
   generated: "2024-12-30T17:30:00Z"
   suggestions:
     - jira_key: "MRC-3266"
       jira_title: "Beta Rollout Scope Document"
       jira_url: "https://nubank.atlassian.net/browse/MRC-3266"
       task_file: "Tasks/001-beta-rollout-scope-document.md"
       updates:
         - type: "comment"
           content: |
             Update 2024-12-30: Completed review of jira-test-cases.md.
             10 BA Initiatives, 148 stories validated.
             Next: Resolve open questions with stakeholders by Jan 6.
           confidence: "high"
         - type: "due_date"
           current: "2025-01-09"
           suggested: "2025-01-16"
           reason: "Slack discussion on Dec 28 moved timeline"
           confidence: "medium"
   ```

3. **Update Daily Closing Slack message**
   - Add summary: "📝 X Jira updates suggested"
   - Include hyperlinked card names
   - Show instruction to run `jira-sync`

**Files to modify:**
- `scripts/logbook-local.py` — `generate_daily_closing()` enhanced
- `.github/workflows/daily-closing.yml` — Add suggestion section to Slack message

---

### Phase 3: User Review Flow ⏱️ ~4 hours

**Goal:** Allow user to approve/edit/skip each suggestion with full edit capabilities.

**Tasks:**

1. **Add `jira-sync` command to logbook-local.py**
   ```python
   def jira_sync(config: Dict[str, str]):
       """Interactive review and approval of pending Jira updates."""
       pending_file = Path(__file__).parent / ".jira-sync-pending.yaml"
       
       if not pending_file.exists():
           print("No pending Jira updates. Run Daily Closing first.")
           return
       
       suggestions = load_yaml(pending_file)
       
       for suggestion in suggestions['suggestions']:
           print(f"\n{'='*60}")
           print(f"📋 [{suggestion['jira_key']}]: {suggestion['jira_title']}")
           print(f"🔗 {suggestion['jira_url']}")
           print(f"{'='*60}")
           
           for update in suggestion['updates']:
               print(f"\n{update['type'].upper()}:")
               print(format_update_preview(update))
               
               choice = input("\n[A]pprove / [E]dit / [S]kip: ").lower()
               
               if choice == 'a':
                   execute_jira_update(config, suggestion['jira_key'], update)
                   log_to_progress(suggestion['task_file'], update)
               elif choice == 'e':
                   edited = edit_update(update)
                   if edited:
                       execute_jira_update(config, suggestion['jira_key'], edited)
                       log_to_progress(suggestion['task_file'], edited)
               # 's' = skip, do nothing
       
       # Cleanup
       pending_file.unlink()
       print("\n✅ Jira sync complete!")
   ```

2. **Add preview formatting**
   ```python
   def format_update_preview(update: Dict) -> str:
       """Format update for terminal display."""
       if update['type'] == 'comment':
           return f"---\n{update['content']}\n---"
       elif update['type'] == 'due_date':
           return f"{update['current']} → {update['suggested']}\nReason: {update['reason']}"
       # etc.
   ```

3. **Add edit flow with $EDITOR support** ✅ MUST HAVE
   ```python
   def edit_update(update: Dict) -> Optional[Dict]:
       """Open update in user's preferred editor for modification."""
       import tempfile
       
       # Determine content to edit based on update type
       if update['type'] == 'comment':
           content = update['content']
           header = f"# Edit Jira Comment for {update.get('jira_key', 'issue')}\n"
           header += "# Lines starting with # are ignored\n"
           header += "# Save and close to apply changes\n\n"
       elif update['type'] == 'due_date':
           content = f"Current: {update['current']}\nSuggested: {update['suggested']}\nReason: {update['reason']}"
           header = "# Edit the 'Suggested:' line to change the date (YYYY-MM-DD)\n\n"
       elif update['type'] == 'description':
           content = update['content']
           header = "# Edit Jira Description\n# Save and close to apply\n\n"
       else:
           content = str(update)
           header = ""
       
       # Write to temp file
       with tempfile.NamedTemporaryFile(
           mode='w', 
           suffix='.md',  # .md for syntax highlighting
           delete=False,
           prefix='jira-edit-'
       ) as f:
           f.write(header + content)
           temp_path = f.name
       
       # Get user's preferred editor
       editor = os.environ.get('EDITOR', os.environ.get('VISUAL', 'nano'))
       
       # Open in editor and wait for user to finish
       print(f"Opening in {editor}...")
       result = subprocess.run([editor, temp_path])
       
       if result.returncode != 0:
           print("❌ Editor exited with error. Skipping this update.")
           os.unlink(temp_path)
           return None
       
       # Read back edited content
       with open(temp_path) as f:
           edited_lines = f.readlines()
       
       os.unlink(temp_path)
       
       # Filter out comment lines and reconstruct
       edited_content = ''.join(
           line for line in edited_lines 
           if not line.strip().startswith('#')
       ).strip()
       
       if not edited_content:
           print("❌ Empty content after editing. Skipping.")
           return None
       
       # Show diff preview
       print("\n📝 Your changes:")
       print(f"   Before: {content[:50]}...")
       print(f"   After:  {edited_content[:50]}...")
       
       confirm = input("\nApply these changes? [Y/n]: ").lower()
       if confirm in ['', 'y', 'yes']:
           update['content'] = edited_content
           return update
       else:
           print("Changes discarded.")
           return None
   ```

4. **Add diff preview for edited content**
   ```python
   def show_edit_diff(original: str, edited: str):
       """Show a simple diff between original and edited content."""
       import difflib
       diff = difflib.unified_diff(
           original.splitlines(keepends=True),
           edited.splitlines(keepends=True),
           fromfile='original',
           tofile='edited'
       )
       print(''.join(diff))
   ```

**Files to modify:**
- `scripts/logbook-local.py` — Add `jira-sync` command with full edit support

---

### Phase 4: Execution ⏱️ ~3 hours

**Goal:** Execute approved updates via Atlassian MCP or API.

**Tasks:**

1. **Implement Jira update execution**
   ```python
   def execute_jira_update(config: Dict, jira_key: str, update: Dict) -> bool:
       """Execute a single Jira update. Returns True on success."""
       
       try:
           if update['type'] == 'comment':
               return add_jira_comment(config, jira_key, update['content'])
           elif update['type'] == 'due_date':
               return update_jira_field(config, jira_key, 'duedate', update['suggested'])
           elif update['type'] == 'description':
               return update_jira_field(config, jira_key, 'description', update['content'])
           elif update['type'] == 'transition':
               return transition_jira_issue(config, jira_key, update['to_status'])
       except Exception as e:
           print(f"❌ MCP/API failed: {e}")
           fallback_to_clipboard(update)
           return False
   ```

2. **API implementations (using REST API for reliability)**
   ```python
   def add_jira_comment(config: Dict, jira_key: str, comment: str) -> bool:
       """Add comment to Jira issue via REST API."""
       url = f"https://{config['ATLASSIAN_DOMAIN']}/rest/api/3/issue/{jira_key}/comment"
       # POST with ADF format
   
   def update_jira_field(config: Dict, jira_key: str, field: str, value: str) -> bool:
       """Update a Jira field via REST API."""
       url = f"https://{config['ATLASSIAN_DOMAIN']}/rest/api/3/issue/{jira_key}"
       # PUT with fields object
   
   def transition_jira_issue(config: Dict, jira_key: str, target_status: str) -> bool:
       """Transition Jira issue to new status."""
       # First: GET available transitions
       # Then: POST transition
   ```

3. **Fallback to clipboard**
   ```python
   def fallback_to_clipboard(update: Dict):
       """Copy update content to clipboard with instructions."""
       content = format_for_clipboard(update)
       subprocess.run(['pbcopy'], input=content.encode(), check=True)
       print(f"📋 Copied to clipboard! Paste into Jira manually.")
       print(f"   Open: {update.get('jira_url', 'Jira')}")
   ```

**Files to modify:**
- `scripts/logbook-local.py` — Add execution functions

---

### Phase 5: Logging & Feedback ⏱️ ~1 hour

**Goal:** Log actions and track patterns.

**Tasks:**

1. **Log to task Progress Log**
   ```python
   def log_to_progress(task_file: Path, update: Dict):
       """Append entry to task's Progress Log."""
       today = datetime.now().strftime('%Y-%m-%d')
       entry = f"- {today}: [Jira Sync] {update['type']}: {update.get('content', '')[:100]}"
       # Append to ## Progress Log section
   ```

2. **Save to agent-feedback.yaml**
   ```python
   def log_feedback(action: str, update_type: str, workflow: str):
       """Track approval/rejection patterns."""
       # Append to Knowledge/agent-feedback.yaml
   ```

3. **Cleanup pending file after completion**

**Files to modify:**
- `scripts/logbook-local.py` — Add logging functions
- `Knowledge/agent-feedback.yaml` — Create if not exists

---

### Phase 6: Integration & Polish ⏱️ ~2 hours

**Goal:** Connect everything, update documentation.

**Tasks:**

1. **Update Daily Closing workflow**
   - Integrate detection after AI summary
   - Post suggestion summary to Slack thread
   - Include "Run jira-sync" CTA

2. **Update AGENTS.md** 
   - Document `jira-sync` command
   - Add workflow to "Helpful Prompts"

3. **Add to setup-enrichment.sh**
   - Optional notification after Daily Closing
   - Remind user about pending Jira updates

4. **Write tests**
   - Test detection logic with sample tasks
   - Test suggestion generation
   - Test API calls (mocked)

**Files to modify:**
- `.github/workflows/daily-closing.yml`
- `AGENTS.md`
- `scripts/setup-enrichment.sh`
- `scripts/test_jira_sync.py` (new)

---

## 5. Spec Alignment Check

| SPEC Requirement | Implementation | Status |
|------------------|----------------|--------|
| `jira_comment` action type | `add_jira_comment()` via REST API | ✅ Planned |
| `jira_description` action type | `update_jira_field('description')` via REST API | ✅ Planned |
| `jira_due_date` action type | `update_jira_field('duedate')` via REST API | ✅ Planned |
| `jira_transition` action type | `transition_jira_issue()` via REST API | ✅ Planned |
| Comment format: "Update YYYY-MM-DD: [summary]" | Enforced in generation | ✅ Planned |
| Hyperlinked card name for verification | `jira_url` in pending file | ✅ Planned |
| Approve/Edit/Skip flow | Interactive CLI with $EDITOR | ✅ Planned |
| Auto-execute via API | REST API (per SPEC update) | ✅ Aligned |
| Fallback to clipboard | `pbcopy` on macOS | ✅ Planned |
| Log to Progress Log | `log_to_progress()` | ✅ Planned |
| Track approval patterns | `agent-feedback.yaml` | ✅ Planned |
| Edit with diff preview | `edit_update()` + `show_edit_diff()` | ✅ Planned |
| 30-second undo | — | ❌ Deferred to v2 |

**SPEC Updated:** Changed from MCP to REST API for reliability (2024-12-30).

---

## 6. Risk Assessment

| Risk | Mitigation |
|------|------------|
| API auth issues | Use existing ATLASSIAN_* env vars from Daily Closing |
| Rate limiting | Batch updates, add delays if needed |
| Wrong card updated | Hyperlink + preview before approval |
| Stale pending file | Timestamp + warn if >24h old |
| Edit flow complexity | Start with simple replace, enhance later |

---

## 7. Success Criteria

| Metric | Target | Validation |
|--------|--------|------------|
| Time from closing to Jira updated | <2 minutes | Stopwatch test |
| User can verify card before posting | 100% | Hyperlink always shown |
| Fallback works when API fails | 100% | Test with bad credentials |
| Progress Log updated | 100% | After each approved update |

---

## 8. Timeline

| Phase | Estimated Time | Dependencies |
|-------|---------------|--------------|
| Phase 1: Detection | 2 hours | — |
| Phase 2: Generation | 2 hours | Phase 1 |
| Phase 3: User Review + Edit | 4 hours | Phase 2 |
| Phase 4: Execution | 3 hours | Phase 3 |
| Phase 5: Logging | 1 hour | Phase 4 |
| Phase 6: Integration | 2 hours | Phase 5 |
| **Total** | **~14 hours** | |

---

## 9. Next Steps

1. ✅ Approve this implementation plan
2. ⏳ Start Phase 1: Detection Infrastructure
3. ⏳ Test with real task files (MRC-3266, etc.)
4. ⏳ Iterate based on feedback

---

*Last updated: 2024-12-30*

