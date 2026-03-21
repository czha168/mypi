---
name: opsx-apply
description: Implement tasks from an OpenSpec change - work through the checklist
category: Workflow
tags: [openspec, apply, implementation, workflow]
workflow: opsx-apply
command_id: opsx-apply
---

Implement tasks from an OpenSpec change. Work through the task checklist, marking each complete as you go.

**Input**: Optionally specify a change name (e.g., `/opsx:apply add-dark-mode`). If omitted, check if it can be inferred from conversation context.

---

## Step 1: Select the Change

**If a name is provided**, use it.

**If no name is provided**:
- Infer from conversation context if the user mentioned a change
- Auto-select if only one active change exists in `openspec/changes/`
- If ambiguous, ask the user to specify

Announce your choice: "Implementing change: `<name>`". Explain how to override: "To use a different change, run `/opsx:apply <other-name>`."

---

## Step 2: Read Context Files

Before implementing anything, read the change's artifacts for context:

1. **`openspec/changes/<name>/proposal.md`** — what and why
2. **`openspec/changes/<name>/tasks.md`** — the checklist to work through
3. **`openspec/changes/<name>/design.md`** — how (if it exists)
4. **`openspec/changes/<name>/specs/**/*.md`** — requirements (if they exist)

Display progress: "N/M tasks complete".

---

## Step 3: Identify Pending Tasks

Parse `tasks.md` for incomplete tasks — lines starting with `- [ ]`:

```
- [ ] 1.1 Create new module structure
- [ ] 1.2 Add dependencies to package.json
- [ ] 2.1 Implement data export function
```

Tasks marked `- [x]` are complete. Skip them.

---

## Step 4: Implement Tasks (Loop)

For each pending task:

1. **Announce** what you're working on: "Working on task: `1.1 Create new module structure`"
2. **Implement** the code change — keep changes minimal and focused on this task
3. **Mark the task complete** — use the **Edit tool** to change `- [ ]` to `- [x]` in `tasks.md`
4. **Continue** to the next task

**Pause if:**
- Task is unclear → ask for clarification before guessing
- Implementation reveals a design issue → suggest updating artifacts
- Error or blocker encountered → report and wait for guidance
- User interrupts

---

## Step 5: Update Tasks File

After completing each task, immediately update `tasks.md`:

```
- [x] 1.1 Create new module structure
```

Use the **Edit tool** with `oldString="- [ ] 1.1"` and `newString="- [x] 1.1"`. Be precise — match the exact text including indentation.

---

## Step 6: Show Progress

After each task or session, show:

```
## Implementation Progress: <name>

Tasks completed: 3/7

### Completed This Session
- [x] 1.1 Create new module structure
- [x] 1.2 Add dependencies
- [x] 2.1 Implement export function

### Remaining
- [ ] 2.2 Add CSV formatting
- [ ] 2.3 Write tests
```

---

## Step 7: On Completion

When all tasks are done:

```
## Implementation Complete ✓

**Change**: <name>
**Tasks**: 7/7 complete

All tasks are complete. Run /opsx:archive when ready to finalize.
```

Offer to archive: "Ready to archive this change? Run `/opsx:archive`."

---

## Guardrails

- **Keep going through tasks** — don't stop after one, work through the list
- **Read context files first** — always understand what you're building before starting
- **Update checkboxes immediately** — mark each task done right after completing it
- **Minimal changes** — each task should be small and focused; if it's too big, note it
- **Pause on blockers** — don't guess, ask the user for guidance
- **Task ambiguity** — if a task is unclear, ask before implementing
- **Don't skip tasks** — work through them in order unless there's a dependency reason
