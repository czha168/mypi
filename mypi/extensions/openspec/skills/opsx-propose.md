---
name: opsx-propose
description: Propose a new change - create it and generate all artifacts in one step
category: Workflow
tags: [openspec, change, workflow]
workflow: opsx-propose
command_id: opsx-propose
---

Propose a new change - create the change and generate all artifacts in one step.

I'll create a change with artifacts:
- `proposal.md` — what & why
- `specs/<capability>/spec.md` — requirements and scenarios (one per capability)
- `design.md` — how
- `tasks.md` — implementation steps

When ready to implement, run `/opsx:apply`.

---

**Input**: The argument after `/opsx:propose` is the change name (kebab-case) OR a description of what you want to build.

---

## Step 1: Parse or Derive the Change Name

**If the input is already kebab-case** (e.g., `add-dark-mode`):
Use it directly as the change name.

**If the input is natural language** (e.g., "add a dark mode toggle"):
Derive a kebab-case name. Common patterns:
- "add X" → `add-x`
- "fix X" → `fix-x`
- "implement X" → `implement-x`
- "improve X" → `improve-x`

**If no input is provided**:
Ask the user: "What change do you want to work on? Describe what you want to build or fix."

---

## Step 2: Create the Change Directory

Use the **Write tool** to create the metadata file:

```
openspec/changes/<name>/.openspec.yaml
```

Content:
```yaml
schema: spec-driven
created: YYYY-MM-DD
```

This file marks the change as an OpenSpec change and records the schema.

---

## Step 3: Create the Change Directory Structure

Use the **Bash tool** to create the directory:

```bash
mkdir -p "openspec/changes/<name>/specs"
```

The directory `openspec/changes/<name>/` is now the change root.

---

## Step 4: Create `proposal.md`

Ask the user about the change if their input was vague. Then create `openspec/changes/<name>/proposal.md` using the proposal template structure:

- **Why** — motivation, problem, why now
- **What Changes** — specific new capabilities, modifications, or removals
- **Capabilities** — list each new or modified capability (each becomes `specs/<name>/spec.md`)
- **Impact** — affected code, APIs, dependencies

The **Capabilities** section is critical. Each capability listed here will need a spec file. Use kebab-case names (e.g., `user-auth`, `data-export`).

---

## Step 5: Create Spec Files

For each capability in the proposal's **New Capabilities** section, create a spec file at:

```
openspec/changes/<name>/specs/<capability-name>/spec.md
```

Use the spec template:
- **## ADDED Requirements** — define what the system SHALL/MUST do
- Each requirement needs at least one **#### Scenario** with **WHEN** / **THEN**

For each capability in **Modified Capabilities**, create a **## MODIFIED Requirements** section with the full updated requirement (not just the change).

---

## Step 6: Create `design.md`

Create `openspec/changes/<name>/design.md` if the change involves:
- Cross-cutting or architectural decisions
- New external dependencies
- Security, performance, or migration complexity

Use the design template:
- **Context** — background, constraints, stakeholders
- **Goals / Non-Goals** — explicit scope boundaries
- **Decisions** — key technical choices with rationale
- **Risks / Trade-offs** — known risks and mitigations
- **Migration Plan** — deployment and rollback steps

---

## Step 7: Create `tasks.md`

Create `openspec/changes/<name>/tasks.md` by breaking down the implementation:

- Group related tasks under numbered headings (## 1. Setup, ## 2. Core Implementation, etc.)
- Each task is a checkbox: `- [ ] 1.1 Task description`
- Order by dependency — what must be done first
- Keep tasks small — one session each

---

## Step 8: Verify and Summarize

After creating all artifacts, verify they exist and summarize:

```
## Change Created: <name>

Location: openspec/changes/<name>/

Artifacts:
- proposal.md ✓
- specs/<capability>/spec.md ✓ (N capabilities)
- design.md ✓
- tasks.md ✓ (N tasks)

Ready for implementation. Run /opsx:apply to start working.
```

---

## Guardrails

- If a change with that name already exists, warn the user and ask whether to continue or create a new name
- Always read the proposal before creating specs, specs before creating tasks
- Ask the user if context is unclear — prefer reasonable decisions over stalling
- Verify each artifact file exists after writing before proceeding
- The artifact order is: proposal → specs → design → tasks
