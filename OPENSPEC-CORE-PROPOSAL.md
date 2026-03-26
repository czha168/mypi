# Proposal: OpenSpec Core Profile Integration for mypi

## Status

Proposed — revised after critical review

## Architecture Decision

**This proposal uses a Hybrid Architecture:**

- **State management** → Python code (`ChangeManager`) handles filesystem state, artifact existence, task parsing, archive operations
- **Agent guidance** → Skill files (`opsx-propose.md`, etc.) provide LLM instructions for *what to write* in artifacts
- **Slash command routing** → Agent session detects `/opsx:` prefix and injects skill content into the conversation

This is **not** a pure skill-driven approach (where LLM does everything) and **not** a pure code-driven approach (where Python executes everything). It matches OpenSpec's actual model: the AI follows skill instructions to create artifacts, while Python manages the change lifecycle that the AI reads from.

---

## Motivation

mypi currently has a template system with adapters, registry, and artifact stubs. The next step is to implement the 4 core OpenSpec commands (`/opsx:propose`, `/opsx:explore`, `/opsx:apply`, `/opsx:archive`) as first-class Python workflow skills, generating real slash command files and driving a spec-driven artifact workflow.

This proposal draws from deep research of the [OpenSpec GitHub repository](https://github.com/Fission-AI/OpenSpec) (32.7k stars, TypeScript), specifically:
- `src/core/templates/workflows/propose.ts` — full propose skill + command template
- `src/core/templates/workflows/explore.ts` — full explore skill template
- `src/core/templates/workflows/apply-change.ts` — full apply skill + command template
- `src/core/templates/workflows/archive-change.ts` — full archive skill + command template
- `schemas/spec-driven/schema.yaml` — artifact DAG definition
- `docs/opsx.md`, `docs/commands.md`, `docs/concepts.md`, `docs/customization.md` — workflow documentation

---

## What We Have

The template system is already built:

```
mypi/templates/
├── __init__.py          # Public API exports
├── adapters.py           # ToolAdapter ABC + Claude/Cursor/Windsurf adapters + ADAPTERS dict
├── registry.py           # TemplateRegistry + WorkflowTemplate
├── cli.py                # add_template_parser() + run_template_cmd()
└── artifacts/
    ├── proposal.md       # Minimal stub (3 lines)
    ├── spec.md           # Generic spec template (23 lines)
    ├── design.md         # Minimal stub
    └── tasks.md          # Minimal stub
```

The `Skill.metadata: dict` field was added to `Skill` in `mypi/extensions/skill_loader.py`, enabling frontmatter-driven workflow metadata.

## What Is Missing

1. **Real OpenSpec skill content** — the artifact stubs are empty, the propose/explore/apply/archive skills don't exist as mypi skills
2. **ChangeManager** — the Python equivalent of OpenSpec's CLI (`openspec new`, `openspec status`, `openspec instructions`) for managing the `openspec/changes/` directory structure
3. **Slash command generation** — skills need to produce actual `.claude/commands/opsx-propose.md` etc. files via the template system
4. **Integration with agent session** — the `/opsx:propose` etc. slash commands need to be wired into the agent's turn loop

---

## Proposed Design

### Architecture Overview

```
mypi/
├── extensions/
│   ├── skill_loader.py       # Existing: Skill.metadata added
│   └── openspec/             # NEW: OpenSpec extension module
│       ├── __init__.py
│       ├── change_manager.py  # Change lifecycle, artifact state, file I/O
│       ├── schema.py          # Schema loading, artifact graph, dependency resolution
│       └── skills/            # Skill source files (driving template registry)
│           ├── opsx-propose.md
│           ├── opsx-explore.md
│           ├── opsx-apply.md
│           └── opsx-archive.md
├── templates/
│   ├── adapters.py           # Existing: update for opsx-* command naming
│   ├── registry.py           # Existing: unchanged
│   └── artifacts/            # Replace stubs with real OpenSpec content
│       ├── proposal.md       # Real OpenSpec template
│       ├── spec.md           # Real per-capability spec template
│       ├── design.md         # Real OpenSpec template
│       └── tasks.md          # Real OpenSpec template
└── core/
    └── agent_session.py      # Modified: route /opsx:* to OpenSpec skills
```

### Directory Structure (Generated Changes)

When a change is created, the following structure is generated:

```
openspec/                              # Project root (auto-created by ChangeManager)
├── changes/
│   └── <change-name>/                 # Change directory
│       ├── .openspec.yaml             # Change metadata (schema, created date)
│       ├── proposal.md                # Why + what + capabilities + impact
│       ├── specs/
│       │   └── <capability-name>/     # Per-capability spec files
│       │       └── spec.md
│       ├── design.md                  # How (technical approach, decisions, risks)
│       └── tasks.md                   # Checkboxed implementation checklist
├── specs/                             # Main specs (source of truth)
│   └── <capability-name>/
│       └── spec.md
└── schemas/                           # (Future: custom schemas)
    └── spec-driven/
        └── schema.yaml
```

### The 4 Core Commands

#### `/opsx:propose` — Create change + all artifacts

**Input**: Change name (kebab-case) or natural language description.

**What it does**:
1. Parse/derive change name from input
2. Create `openspec/changes/<name>/` directory with `.openspec.yaml` metadata
3. Create all planning artifacts in dependency order:
   - `proposal.md` — why + what + capabilities + impact
   - `specs/<capability>/spec.md` — per-capability requirements and scenarios
   - `design.md` — how (technical approach, decisions, risks)
   - `tasks.md` — checkboxed implementation checklist
4. Show final status

**Key insight from OpenSpec source** (`propose.ts`):
- The AI loops through artifacts in dependency order
- Uses `openspec status --json` to determine which artifacts are `ready`
- Uses `openspec instructions <artifact-id> --json` to get template + instruction for each
- Writes each artifact file, marks it done, re-queries status
- Stops when all `apply.requires` artifacts are `done`

In Python: `ChangeManager.get_status(change_name)` returns artifact states; `ChangeManager.get_instructions(change_name, artifact_id)` returns template + instruction.

#### `/opsx:explore` — Thinking partner, no code writing

**Input**: Optional topic or nothing.

**What it does**:
- Read existing artifacts if a change name is mentioned
- Think deeply, ask questions, draw ASCII diagrams
- Offer to capture insights in appropriate artifacts
- Never write code — only create OpenSpec artifacts if user asks

**Key insight from OpenSpec source** (`explore.ts`):
- This is a "stance, not a workflow" — no fixed steps
- Use ASCII diagrams liberally
- Check `ChangeManager.list_changes()` to see active changes
- Surface risks, compare options, reframe problems
- Offer to capture decisions: design decision → `design.md`, new requirement → `specs/<cap>/spec.md`

#### `/opsx:apply` — Implement tasks from tasks.md

**Input**: Optional change name (auto-detected if one active change).

**What it does**:
1. Read `tasks.md` for pending tasks (`- [ ]`)
2. Loop through incomplete tasks
3. For each: implement code, mark `- [x]`, continue
4. Pause on blockers or ambiguity
5. Show progress summary

**Key insight from OpenSpec source** (`apply-change.ts`):
- Always read context files first (proposal, specs, design, tasks)
- Keep code changes minimal and scoped to each task
- Update checkbox immediately after completing each task
- Support fluid workflow: can be invoked anytime, not just after all artifacts done
- Handle `blocked` state (missing artifacts) gracefully

#### `/opsx:archive` — Finalize and move to archive

**Input**: Optional change name.

**What it does**:
1. Prompt for change selection if not provided
2. Check artifact completion status (warn if incomplete)
3. Check task completion (warn if incomplete)
4. Offer to sync delta specs to main specs (if applicable)
5. Move to `openspec/changes/archive/YYYY-MM-DD-<name>/`
6. Show summary

**Key insight from OpenSpec source** (`archive-change.ts`):
- Never block on warnings — just inform and confirm
- Delta specs are compared against main specs to show diff summary
- Archive directory format: `YYYY-MM-DD-<name>` for chronological ordering
- Preserve `.openspec.yaml` metadata when moving

### ChangeManager — Core Infrastructure

The `ChangeManager` replaces OpenSpec's CLI commands:

```python
from dataclasses import dataclass
from pathlib import Path
from datetime import date


@dataclass
class ArtifactInfo:
    id: str
    status: str  # "done" | "ready" | "blocked"
    path: str
    missing_deps: list[str]


@dataclass
class ChangeStatus:
    name: str
    schema_name: str
    is_complete: bool
    apply_requires: list[str]
    artifacts: list[ArtifactInfo]


@dataclass
class ArtifactInstructions:
    artifact_id: str
    template: str           # Markdown template content
    instruction: str         # Schema-specific guidance
    output_path: str         # Relative path from change dir
    dependencies: list[str]  # Completed artifact IDs to read


@dataclass
class Task:
    id: str                 # e.g., "1.1", "2.3"
    description: str
    done: bool
    group: str              # e.g., "1. Setup"


class ChangeManager:
    """Manages OpenSpec change lifecycle — create, status, instructions, archive."""
    
    def __init__(self, root: Path | None = None):
        self.root = root or Path.cwd() / "openspec"
        self.changes_dir = self.root / "changes"
        self.specs_dir = self.root / "specs"
        self.archive_dir = self.changes_dir / "archive"
    
    # --- Lifecycle ---
    def new_change(self, name: str, schema: str = "spec-driven") -> Path:
        """Create change directory with .openspec.yaml metadata."""
        change_path = self.changes_dir / name
        change_path.mkdir(parents=True, exist_ok=True)
        metadata = change_path / ".openspec.yaml"
        metadata.write_text(
            f"schema: {schema}\n"
            f"created: {date.today().isoformat()}\n"
        )
        return change_path
    
    def list_changes(self) -> list[str]:
        """Return names of all active (non-archived) changes."""
        if not self.changes_dir.exists():
            return []
        return sorted([
            d.name for d in self.changes_dir.iterdir()
            if d.is_dir() and d.name != "archive"
        ])
    
    def get_change_path(self, name: str) -> Path:
        """Return Path to change directory. Raises FileNotFoundError if not found."""
        path = self.changes_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Change not found: {name}")
        return path
    
    # --- Status & State ---
    def get_status(self, change_name: str) -> ChangeStatus:
        """
        Return artifact states for a change.
        State is determined by filesystem existence:
          - done: file exists
          - ready: all deps are done
          - blocked: missing deps
        """
        change_path = self.get_change_path(change_name)
        schema = self._load_schema("spec-driven")
        
        artifacts: list[ArtifactInfo] = []
        done_ids: set[str] = set()
        
        # Topological sort for dependency order
        sorted_ids = self._topological_sort(schema.artifacts)
        
        for artifact_def in sorted_ids:
            artifact_path = change_path / artifact_def.generates
            exists = artifact_path.exists() or self._glob_exists(change_path, artifact_def.generates)
            
            missing_deps = [
                dep for dep in artifact_def.requires
                if dep not in done_ids
            ]
            
            if exists:
                status = "done"
                done_ids.add(artifact_def.id)
            elif not missing_deps:
                status = "ready"
            else:
                status = "blocked"
            
            artifacts.append(ArtifactInfo(
                id=artifact_def.id,
                status=status,
                path=artifact_def.generates,
                missing_deps=missing_deps,
            ))
        
        apply_requires = [a.id for a in schema.apply.requires]
        is_complete = all(
            next((x for x in artifacts if x.id == req), None) is not None
            and next((x for x in artifacts if x.id == req), None).status == "done"
            for req in apply_requires
        )
        
        return ChangeStatus(
            name=change_name,
            schema_name="spec-driven",
            is_complete=is_complete,
            apply_requires=apply_requires,
            artifacts=artifacts,
        )
    
    def _glob_exists(self, root: Path, pattern: str) -> bool:
        """Check if any file matches glob pattern."""
        import fnmatch
        if "**" in pattern:
            base, glob_part = pattern.split("/**", 1)
            base_path = root / base if base else root
            rest = glob_part.lstrip("/")
            for f in base_path.rglob(rest.split("/")[0]):
                return True
            return False
        return (root / pattern).exists()
    
    # --- Instructions ---
    def get_instructions(self, change_name: str, artifact_id: str) -> ArtifactInstructions:
        """Return template + instruction for creating an artifact."""
        change_path = self.get_change_path(change_name)
        schema = self._load_schema("spec-driven")
        
        artifact_def = next((a for a in schema.artifacts if a.id == artifact_id), None)
        if not artifact_def:
            raise ValueError(f"Unknown artifact: {artifact_id}")
        
        # Read completed dependency artifacts for context
        done_deps = []
        if artifact_def.requires:
            for dep_id in artifact_def.requires:
                dep_def = next((a for a in schema.artifacts if a.id == dep_id), None)
                if dep_def:
                    dep_path = change_path / dep_def.generates
                    if dep_path.exists():
                        done_deps.append(dep_id)
        
        # Load template from bundled artifact templates
        template = self._load_artifact_template(artifact_id)
        
        return ArtifactInstructions(
            artifact_id=artifact_id,
            template=template,
            instruction=artifact_def.instruction or "",
            output_path=artifact_def.generates,
            dependencies=done_deps,
        )
    
    # --- Tasks ---
    def get_tasks(self, change_name: str) -> list[Task]:
        """Parse tasks.md, return list of Task objects."""
        change_path = self.get_change_path(change_name)
        tasks_file = change_path / "tasks.md"
        
        if not tasks_file.exists():
            return []
        
        content = tasks_file.read_text()
        tasks: list[Task] = []
        current_group = ""
        
        for line in content.splitlines():
            stripped = line.strip()
            
            # Group heading: ## 1. Group Name
            if stripped.startswith("## "):
                current_group = stripped[3:].split(".", 1)[-1].strip()
            
            # Task: - [ ] 1.1 Description
            elif stripped.startswith("- ["):
                done = stripped.startswith("- [x]") or stripped.startswith("- [X]")
                # Extract ID and description
                # Format: "- [ ] 1.1 Description" or "- [x] 1.1 Description"
                rest = stripped[4:].lstrip("] ").lstrip("xX] ")
                parts = rest.split(" ", 1)
                task_id = parts[0] if parts else ""
                description = parts[1] if len(parts) > 1 else ""
                
                tasks.append(Task(
                    id=task_id,
                    description=description.strip(),
                    done=done,
                    group=current_group,
                ))
        
        return tasks
    
    def mark_task_done(self, change_name: str, task_id: str) -> None:
        """Update tasks.md: - [ ] → - [x] for given task ID."""
        change_path = self.get_change_path(change_name)
        tasks_file = change_path / "tasks.md"
        
        if not tasks_file.exists():
            return
        
        content = tasks_file.read_text()
        new_lines: list[str] = []
        
        for line in content.splitlines():
            stripped = line.strip()
            # Match: "- [ ] <id> Description"
            if stripped.startswith("- [ ] "):
                rest = stripped[6:]
                if rest.startswith(task_id + " ") or rest.startswith(task_id + "\t"):
                    new_lines.append(line.replace("- [ ]", "- [x]", 1))
                    continue
            new_lines.append(line)
        
        tasks_file.write_text("\n".join(new_lines) + "\n")
    
    # --- Archive ---
    def archive_change(self, change_name: str) -> Path:
        """Move change to archive/YYYY-MM-DD-<name>/"""
        change_path = self.get_change_path(change_name)
        archive_path = self.archive_dir / f"{date.today().isoformat()}-{change_name}"
        
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        change_path.rename(archive_path)
        
        return archive_path
    
    # --- Schema ---
    def _schema_cache: dict = {}
    
    def _load_schema(self, schema_name: str) -> "Schema":
        """Load schema from bundled YAML (hardcoded spec-driven for v1)."""
        if schema_name in self._schema_cache:
            return self._schema_cache[schema_name]
        
        # For v1: hardcoded schema (can be extended to load from YAML files)
        schema = Schema(
            name="spec-driven",
            artifacts=[
                ArtifactDef("proposal", "proposal.md", [], "..."),
                ArtifactDef("specs", "specs/", ["proposal"], "..."),
                ArtifactDef("design", "design.md", ["proposal"], "..."),
                ArtifactDef("tasks", "tasks.md", ["specs", "design"], "..."),
            ],
            apply=ApplyConfig(["tasks"], "tasks.md"),
        )
        self._schema_cache[schema_name] = schema
        return schema
    
    def _load_artifact_template(self, artifact_id: str) -> str:
        """Load artifact template from bundled templates."""
        from codepi.templates.artifacts import TEMPLATES
        return TEMPLATES.get(artifact_id, "")


@dataclass
class Schema:
    name: str
    artifacts: list["ArtifactDef"]
    apply: "ApplyConfig"


@dataclass
class ArtifactDef:
    id: str
    generates: str
    requires: list[str]
    instruction: str


@dataclass
class ApplyConfig:
    requires: list[str]
    tracks: str
```

### Schema — Artifact Dependency Graph

For v1, the schema is hardcoded in `ChangeManager._load_schema()`. For future phases, it can be loaded from bundled YAML:

```yaml
name: spec-driven
version: 1
artifacts:
  - id: proposal
    generates: proposal.md
    requires: []
  - id: specs
    generates: specs/
    requires: [proposal]
  - id: design
    generates: design.md
    requires: [proposal]
  - id: tasks
    generates: tasks.md
    requires: [specs, design]
apply:
  requires: [tasks]
  tracks: tasks.md
```

The topological sort computes artifact creation order respecting dependencies.

### Skill Files — Driving the Template Registry

Each skill is a markdown file with YAML frontmatter. Skills guide the LLM on what to write — they don't execute code themselves.

**`mypi/extensions/openspec/skills/opsx-propose.md`**:

```markdown
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
- proposal.md (what & why)
- specs/<capability>/spec.md (requirements and scenarios)
- design.md (how)
- tasks.md (implementation steps)

When ready to implement, run /opsx:apply

---

**Input**: The user's request should include a change name (kebab-case) OR a description.

**Steps**

1. **If no clear input provided, ask what they want to build**

   Ask the user: "What change do you want to work on? Describe what you want to build or fix."

   Derive a kebab-case name from their description (e.g., "add user auth" → `add-user-auth`).

2. **Create the change directory**

   Use the **Write tool** to create `openspec/changes/<name>/.openspec.yaml`:
   ```yaml
   schema: spec-driven
   created: YYYY-MM-DD
   ```

3. **Query artifact status**

   Use the **Bash tool** to run:
   ```bash
   python -c "
   from codepi.extensions.openspec import ChangeManager
   from pathlib import Path
   cm = ChangeManager(Path.cwd())
   import json
   print(json.dumps(asdict(cm.get_status('<name>'))))
   "
   ```
   Or call `ChangeManager.get_status('<name>')` directly if integrated.

4. **Create artifacts in sequence until apply-ready**

   For each artifact that is `ready` (dependencies satisfied):
   a. Get instructions: `ChangeManager.get_instructions('<name>', '<artifact-id>')`
   b. Read any completed dependency files for context
   c. Create the artifact file using the template as structure
   d. Show: "Created <artifact-id>"

5. **Show final status**

   Report which artifacts were created and prompt: "Ready for implementation. Run /opsx:apply."

**Output**
- Change name and location
- List of artifacts created
- "Ready for implementation. Run /opsx:apply."

**Important**: Read `ChangeManager.get_instructions()` output for the exact template and instruction per artifact. The spec artifact creates `specs/<capability-name>/spec.md` for EACH capability listed in the proposal's Capabilities section.
```

**Key adaptation from OpenSpec**: The original `propose.ts` calls `openspec status --json` and `openspec instructions <id> --json` via bash. In mypi, the skill instructs the LLM to use Python calls instead. For v1, this uses `Bash` with inline Python. In later phases, `ChangeManager` can be integrated directly into the agent toolset.

### Skill Discovery Mechanism

The `SkillLoader` searches `~/.mypi/skills/` and `--skills-dir` directories. To include package-managed OpenSpec skills:

**Option A — Symlink** (recommended for v1):
```python
# In setup.py or pyproject.toml
data_files = [
    ("~/.mypi/skills", ["mypi/extensions/openspec/skills/*.md"]),
]
```

**Option B — Extend SkillLoader search paths**:
```python
# mypi/extensions/skill_loader.py
class SkillLoader:
    def __init__(self, skills_dirs: list[Path]):
        # Add package-managed skills directory
        package_skills = Path(__file__).parent / "openspec" / "skills"
        self.skills_dirs = [package_skills] + [Path(d) for d in skills_dirs]
```

**Option C — Copy on first run**:
```python
# Check if skills exist, copy from package if not
def _ensure_package_skills():
    dest = Path.home() / ".mypi" / "skills"
    src = Path(__file__).parent / "openspec" / "skills"
    if not (dest / "opsx-propose.md").exists():
        for f in src.glob("*.md"):
            shutil.copy(f, dest / f.name)
```

Recommendation: **Option B** — extend `SkillLoader` search paths. It's clean, requires no user action, and is easy to override via `--skills-dir`.

### Template System Integration

The existing template system generates tool-specific command files:

```bash
mypi template generate --tool claude --skills-dir ~/.mypi/skills
```

This reads all skills with `workflow:` frontmatter, creates `WorkflowTemplate` entries, and writes:

```
.claude/commands/opsx-propose.md   # Generated from opsx-propose skill
.claude/commands/opsx-explore.md  # Generated from opsx-explore skill
.claude/commands/opsx-apply.md    # Generated from opsx-apply skill
.claude/commands/opsx-archive.md  # Generated from opsx-archive skill
```

The adapter needs updating to produce `opsx-*` naming:

```python
# mypi/templates/adapters.py — update ClaudeAdapter
class ClaudeAdapter(ToolAdapter):
    tool_id = "claude"
    
    def get_file_path(self, command_id: str) -> str:
        # command_id = "opsx-propose" → .claude/commands/opsx-propose.md
        return f".claude/commands/{command_id}.md"
```

### Agent Session Integration

Modify `AgentSession` to route `/opsx:*` messages to OpenSpec skills:

```python
# mypi/core/agent_session.py

def _is_opsx_command(self, text: str) -> bool:
    """Check if message starts with /opsx: prefix."""
    stripped = text.strip()
    return stripped.startswith("/opsx:") and len(stripped) > 6

async def _handle_opsx_command(self, message: str) -> str:
    """Route /opsx:propose, /opsx:explore, /opsx:apply, /opsx:archive."""
    parts = message.strip()[6:].split(" ", 1)  # Strip "/opsx:" prefix
    command = parts[0]
    args = parts[1] if len(parts) > 1 else ""
    
    # Map command name to skill name
    skill_map = {
        "propose": "opsx-propose",
        "explore": "opsx-explore",
        "apply": "opsx-apply",
        "archive": "opsx-archive",
    }
    
    skill_name = skill_map.get(command)
    if not skill_name:
        return f"Unknown OpenSpec command: /opsx:{command}"
    
    # Load skill content
    skill = self.skill_loader.load_skill_content(skill_name)
    if not skill:
        return f"OpenSpec skill not found: {skill_name}"
    
    # Inject skill content as if user typed it
    # The agent will follow the skill instructions
    return (
        f"Running /opsx:{command} {args}\n\n"
        f"--- Skill: {skill.name} ---\n\n"
        f"{skill.body}\n\n"
        f"User request: {args}"
    )
```

The skill body guides the LLM through the workflow. For `/opsx:propose "add-dark-mode"`, the LLM sees the skill instructions and creates the change directory + artifacts following them.

### Artifact Templates — Real OpenSpec Content

Replace the stubs with real OpenSpec templates. These are loaded by `ChangeManager._load_artifact_template()` and provided as structure in skill instructions.

**`mypi/templates/artifacts/proposal.md`** (already replaced with real content):

```markdown
## Why

<!-- Explain the motivation for this change. What problem does this solve? Why now? -->

## What Changes

<!-- Describe what will change. Be specific about new capabilities, modifications, or removals. -->

## Capabilities

### New Capabilities
<!-- Capabilities being introduced. Each creates specs/<name>/spec.md.
     Use kebab-case names (e.g., user-auth, data-export). -->
- `<name>`: <brief description>

### Modified Capabilities
<!-- Existing capabilities whose REQUIREMENTS are changing.
     Only list if spec-level behavior changes.
     Check openspec/specs/ for existing spec names. -->
- `<existing-name>`: <what requirement is changing>

## Impact

<!-- Affected code, APIs, dependencies, systems -->
```

**`mypi/templates/artifacts/spec.md`** (per-capability spec, ADDED/MODIFIED/REMOVED format):

```markdown
## ADDED Requirements

### Requirement: <!-- capability name -->
<!-- What the system SHALL/MUST do for this capability -->

#### Scenario: <!-- scenario name -->
- **WHEN** <!-- condition -->
- **THEN** <!-- expected outcome -->

## MODIFIED Requirements

### Requirement: <!-- existing requirement name -->
<!-- Updated requirement text -->
(Previously: <original text>)

#### Scenario: <!-- updated scenario -->
- **WHEN** <!-- updated condition -->
- **THEN** <!-- updated outcome -->

## REMOVED Requirements

### Requirement: <!-- requirement name -->
**Reason**: <!-- why this is being removed -->
**Migration**: <!-- how to migrate -->
```

**`mypi/templates/artifacts/design.md`**:

```markdown
## Context

<!-- Background, current state, constraints, stakeholders -->

## Goals / Non-Goals

**Goals:**
<!-- What this design aims to achieve -->

**Non-Goals:**
<!-- What is explicitly out of scope -->

## Decisions

<!-- Key technical choices with rationale. Format:
### Decision: <title>
**Choice**: <what was chosen>
**Rationale**: <why over alternatives>
**Alternatives considered**: <what else was considered>
-->

## Risks / Trade-offs

<!-- Known risks and potential issues. Format:
[Risk] → <description>
[Mitigation] → <how to address>
-->

## Migration Plan

<!-- Steps to deploy. Rollback strategy. -->
```

**`mypi/templates/artifacts/tasks.md`**:

```markdown
## 1. <!-- Task Group Name -->

- [ ] 1.1 <!-- Task description — keep small, one session -->
- [ ] 1.2 <!-- Task description -->

## 2. <!-- Next Group -->

- [ ] 2.1 <!-- Task description -->
- [ ] 2.2 <!-- Task description -->
```

---

## Implementation Phases

### Phase 1: ChangeManager + Schema (Core)

**Effort**: Medium

- [ ] `mypi/extensions/openspec/schema.py` — Schema dataclasses, topological sort
- [ ] `mypi/extensions/openspec/change_manager.py` — Full implementation per API above
- [ ] `mypi/extensions/openspec/__init__.py` — Module exports
- [ ] `tests/extensions/openspec/test_change_manager.py` — Unit tests
- [ ] `tests/extensions/openspec/test_schema.py` — Unit tests for topological sort

### Phase 2: OpenSpec Skills (Content)

**Effort**: Medium

- [ ] `mypi/extensions/openspec/skills/opsx-propose.md` — Based on `propose.ts`, adapted for mypi
- [ ] `mypi/extensions/openspec/skills/opsx-explore.md` — Based on `explore.ts`, adapted for mypi
- [ ] `mypi/extensions/openspec/skills/opsx-apply.md` — Based on `apply-change.ts`, adapted for mypi
- [ ] `mypi/extensions/openspec/skills/opsx-archive.md` — Based on `archive-change.ts`, adapted for mypi
- [ ] Skill discovery: Extend `SkillLoader` to include `mypi/extensions/openspec/skills/`

### Phase 3: Template System Integration (Slash Commands)

**Effort**: Low

- [ ] Update `ClaudeAdapter.get_file_path()` for `opsx-*` naming (not `mypi-*`)
- [ ] Update `CursorAdapter`, `WindsurfAdapter` similarly
- [ ] Verify `mypi template generate --tool claude` produces `opsx-propose.md` etc.
- [ ] Add tests: `tests/templates/test_openspec_generation.py`

### Phase 4: Artifact Templates (Real Content)

**Effort**: Low

- [ ] Replace `mypi/templates/artifacts/proposal.md` with real OpenSpec template
- [ ] Replace `mypi/templates/artifacts/spec.md` with per-capability delta spec format
- [ ] Replace `mypi/templates/artifacts/design.md` with real OpenSpec template
- [ ] Replace `mypi/templates/artifacts/tasks.md` with real OpenSpec template
- [ ] Expose templates via `mypi/templates/artifacts/__init__.py` (`TEMPLATES` dict)

### Phase 5: Agent Integration (Slash Command Routing)

**Effort**: Medium

- [ ] Modify `AgentSession._handle_message()` to detect `/opsx:` prefix
- [ ] Implement `_is_opsx_command()` and `_handle_opsx_command()`
- [ ] Inject skill content into conversation context
- [ ] Add integration tests for the full flow: `/opsx:propose "test-change"` → artifacts created

---

## Key Differences from OpenSpec TypeScript

| Aspect | OpenSpec (TypeScript) | mypi (Python) |
|--------|----------------------|----------------|
| Status queries | CLI: `openspec status --json` | `ChangeManager.get_status()` |
| Instructions | CLI: `openspec instructions <id> --json` | `ChangeManager.get_instructions()` |
| Change creation | CLI: `openspec new change <name>` | `ChangeManager.new_change()` |
| Artifact graph | TypeScript DAG engine | Python topological sort |
| Schema loading | Bundled with npm package | Hardcoded (v1), YAML (future) |
| Tool adapters | `configurators/` per tool | `mypi/templates/adapters.py` |
| Command files | Generated at `openspec init` | Generated via `mypi template generate` |
| Slash commands | Injected by AI tool | Routed through `AgentSession` |
| Skills | In `~/.claude/skills/` | In `~/.mypi/skills/` + package path |

---

## Open Questions (Resolved)

| Question | Resolution |
|----------|------------|
| Schema support | Start with hardcoded `spec-driven` (Phase 1), add YAML loader in future phase |
| CLI parity | Yes, add `mypi openspec status --change <name>` for debugging (Phase 5) |
| Delta specs | Skip spec sync in v1 (Phase 5+), archive moves changes without merging |
| Multiple changes | Auto-select if one active change, prompt if multiple |
| Skills location | Package-managed in `mypi/extensions/openspec/skills/`, discovered via extended `SkillLoader` |

---

## Alternatives Considered

### Option A: Pure Skill-Driven (LLM Does Everything)

No `ChangeManager`. LLM follows skill instructions to create all files, query status by reading the filesystem.

**Pros**: Simplest implementation, closest to Claude Code command model
**Cons**: LLM can't query structured state (artifact status, task progress), no programmatic archive, harder to test

### Option B: Pure Code-Driven (Python Executes)

`ProposeCommand.execute()` creates all artifacts programmatically. No skill content for propose/apply/archive.

**Pros**: Most powerful, fastest, easiest to test
**Cons**: Loses LLM guidance on artifact content quality, diverges from OpenSpec's skill-based model

### Option C: Hybrid (Proposed)

`ChangeManager` handles state, skills guide LLM on content. Best of both worlds.

**Pros**: Matches OpenSpec's architecture, testable state management, LLM-guided content quality
**Cons**: Some duplication of OpenSpec's TypeScript logic in Python

---

## References

- [OpenSpec GitHub](https://github.com/Fission-AI/OpenSpec) — 32.7k stars
- [OpenSpec OPSX Workflow](https://github.com/Fission-AI/OpenSpec/blob/main/docs/opsx.md) — fluid vs phase-locked
- [OpenSpec Commands](https://github.com/Fission-AI/OpenSpec/blob/main/docs/commands.md) — 704-line command reference
- [OpenSpec Concepts](https://github.com/Fission-AI/OpenSpec/blob/main/docs/concepts.md) — specs, changes, artifacts, schemas
- [OpenSpec Customization](https://github.com/Fission-AI/OpenSpec/blob/main/docs/customization.md) — project config, custom schemas
- [OpenSpec propose.ts](https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/src/core/templates/workflows/propose.ts) — canonical skill + command template
- [OpenSpec explore.ts](https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/src/core/templates/workflows/explore.ts) — explore skill
- [OpenSpec apply-change.ts](https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/src/core/templates/workflows/apply-change.ts) — apply skill + command
- [OpenSpec archive-change.ts](https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/src/core/templates/workflows/archive-change.ts) — archive skill + command
- [OpenSpec schema.yaml](https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/schemas/spec-driven/schema.yaml) — artifact DAG
- [OpenSpec types.ts](https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/src/core/templates/types.ts) — SkillTemplate + CommandTemplate interfaces
