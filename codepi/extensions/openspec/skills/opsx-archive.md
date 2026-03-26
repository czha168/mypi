---
name: opsx-archive
description: Archive a completed change - move it to the archive directory
category: Workflow
tags: [openspec, archive, finalize, workflow]
workflow: opsx-archive
command_id: opsx-archive
---

Archive a completed change. Move it from `openspec/changes/<name>/` to `openspec/changes/archive/YYYY-MM-DD-<name>/`.

**Input**: Optionally specify a change name (e.g., `/opsx:archive add-dark-mode`). If omitted, check if it can be inferred from context.

---

## Step 1: Select the Change

**If a name is provided**, use it.

**If no name is provided**:
- Infer from conversation context if the user mentioned a change
- Auto-select if only one completed change exists
- If ambiguous, list available changes and ask the user to select

**List active changes** with `ls openspec/changes/` (excluding `archive/`).

---

## Step 2: Check Artifact Completion

Check which artifacts exist in `openspec/changes/<name>/`:

- `proposal.md` — should exist
- `specs/` — should exist (even if empty)
- `design.md` — may or may not exist depending on the change
- `tasks.md` — should exist

**If artifacts are missing**, warn the user:
```
Warning: Missing artifacts:
- design.md

Archive anyway?
```

Offer to continue or cancel.

---

## Step 3: Check Task Completion

Read `openspec/changes/<name>/tasks.md` and count:
- **Complete tasks**: lines starting with `- [x]`
- **Pending tasks**: lines starting with `- [ ]`

**If tasks are incomplete**, warn the user:
```
Warning: 3 tasks are not complete:
- [ ] 2.2 Add CSV formatting
- [ ] 2.3 Write tests
- [ ] 3.1 Update documentation

Archive anyway?
```

Offer to continue or cancel.

---

## Step 4: Create the Archive Directory

```bash
mkdir -p openspec/changes/archive
```

---

## Step 5: Archive the Change

Generate the archive name with today's date:

```
YYYY-MM-DD-<name>
```

For example, archiving `add-dark-mode` on 2026-03-20 → `2026-03-20-add-dark-mode`

**Check if the target already exists**:
```bash
ls openspec/changes/archive/
```

If it exists, warn: "Archive `YYYY-MM-DD-<name>` already exists. Choose a different name or rename the existing archive."

---

## Step 6: Move to Archive

Use the **Bash tool**:

```bash
mv "openspec/changes/<name>" "openspec/changes/archive/YYYY-MM-DD-<name>"
```

---

## Step 7: Show Summary

```
## Archive Complete ✓

**Change**: <name>
**Archived to**: openspec/changes/archive/YYYY-MM-DD-<name>/

**Artifacts**: ✓ All present
**Tasks**: ✓ All complete

The change has been archived. The main specs at openspec/specs/ have not been modified.
(To merge delta specs, use /opsx:sync — not yet implemented in v1)
```

---

## Guardrails

- **Always confirm** before archiving — list what's present and what's missing
- **Warn on incomplete** — missing artifacts or tasks should be flagged, not silently ignored
- **Date prefix** — always use `YYYY-MM-DD-` prefix for chronological ordering
- **Unique names** — fail if the archive target already exists
- **Preserve everything** — the entire change directory moves, including `.openspec.yaml`
- **Don't block** — warnings are informational, the user can still archive if they choose
