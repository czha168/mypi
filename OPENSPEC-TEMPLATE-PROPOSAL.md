# Feature Proposal: OpenSpec Template System Integration

## Status

Proposed — awaiting feedback

## Motivation

mypi currently implements a simple skill system inspired by Claude Code's markdown-with-frontmatter format. However, it lacks the structured workflow templates and cross-tool command generation that make OpenSpec powerful. This proposal enhances mypi's skill interface to support:

1. **Workflow Templates** — Structured change workflows (propose, explore, apply, verify)
2. **Slash Command Generation** — Export skills as Claude Code commands, Cursor rules, Windsurf configs
3. **Artifact Templates** — Structured markdown templates for proposals, specs, designs, tasks
4. **Template Registry** — Centralized skill/command exports with parity validation

## Current State

### Existing Skill Format

Skills are markdown files with YAML frontmatter in `~/.mypi/skills/`:

```markdown
---
name: commit-message
description: Write a git commit message after making code changes
---

When writing commits:
1. Use imperative mood, 50 chars max
2. Explain *why*, not *what*
```

### Limitations

| Gap | Impact |
|-----|--------|
| No workflow templates | Each skill is isolated, no orchestration |
| No command generation | Cannot export to Claude Code/Cursor commands |
| No artifact templates | Missing structured change artifacts |
| No type safety | Skills parsed loosely via YAML |
| No registry | No centralized index of available skills |

## Proposed Design

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Enhanced Skill System                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────┐    ┌──────────────────────┐              │
│  │   Skill Files (.md) │    │  Command Templates   │              │
│  │                      │    │  (tool-specific)     │              │
│  │  Extended frontmatter│    │                      │              │
│  │  workflow: <name>    │    │  claude-commands/    │              │
│  │  category: Workflow │    │  cursor-rules/        │              │
│  │  tags: [change]      │    │  windsurf-rules/      │              │
│  └──────────┬───────────┘    └──────────┬───────────┘              │
│             │                           │                            │
│             └────────────┬──────────────┘                            │
│                          ▼                                           │
│             ┌────────────────────────┐                              │
│             │   Template Registry    │                              │
│             │                        │                              │
│             │  - load_skills()      │                              │
│             │  - generate_commands() │                              │
│             │  - validate_parity()   │                              │
│             └────────────────────────┘                              │
└─────────────────────────────────────────────────────────────────────┘
```

### 1. Enhanced Skill Frontmatter

Extend the existing skill format with OpenSpec-style metadata:

```yaml
---
name: openspec-propose
description: Start a new OpenSpec change with structured artifacts
category: Workflow           # New: categorization
tags: [change, workflow]     # New: tagging
workflow: new-change         # New: links to workflow module
compatibility: claude|cursor|windsurf  # New: tool compatibility

# Workflow-specific metadata
workflow_config:
  schema: spec-driven         # Artifact schema
  interactive_prompt: "What change do you want to work on?"
  name_pattern: "^[a-z0-9]+(?:-[a-z0-9]+)*$"
---

# Skill Body (Agent Instructions)

Start a new change using the experimental artifact-driven approach.

**Input**: The user's request should include a change name (kebab-case) OR a description.

**Steps**

1. **If no clear input provided, ask what they want to build**
   Use the **AskUserQuestion tool** to ask:
   > "What change do you want to work on?"

2. **Determine the workflow schema**
   Use the default schema unless the user explicitly requests a different workflow.

3. **Create the change directory**
   ```bash
   mkdir -p openspec/changes/<name>
   ```

4. **Generate artifact files from templates**
   Use the artifact templates for this workflow:
   - proposal.md (always)
   - spec.md (for spec-driven)
   - design.md (optional)
   - tasks.md (optional)
```

### 2. Command Templates

Define tool-specific command formatting:

```yaml
# commands/claude-propose.md
name: OPSX: Propose
description: Start a new OpenSpec change
category: Workflow
tags: [openspec, change]
---

# OPSX: Propose

Start a new change using the experimental artifact-driven approach.

**Input**: The user's request should include a change name (kebab-case) OR a description.

**Steps**

1. **If no clear input provided, ask what they want to build**
   Use the **AskUserQuestion tool** to ask:
   > "What change do you want to work on?"
...
```

### 3. Tool Adapters

Each AI tool gets its own adapter:

```python
# mypi/templates/adapters.py

from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class CommandContent:
    id: str
    name: str
    description: str
    category: str
    tags: list[str]
    body: str


class ToolAdapter(ABC):
    """Base class for tool-specific command generation."""
    
    @property
    @abstractmethod
    def tool_id(self) -> str:
        ...
    
    @abstractmethod
    def get_file_path(self, command_id: str) -> str:
        """Return the path where the command file will be written."""
        ...
    
    @abstractmethod
    def format_file(self, content: CommandContent) -> str:
        """Format command content for this tool's command format."""
        ...


class ClaudeAdapter(ToolAdapter):
    tool_id = "claude"
    
    def get_file_path(self, command_id: str) -> str:
        return f".claude/commands/opsx-{command_id}.md"
    
    def format_file(self, content: CommandContent) -> str:
        return f"""# {content.name}

{content.body}"""


class CursorAdapter(ToolAdapter):
    tool_id = "cursor"
    
    def get_file_path(self, command_id: str) -> str:
        return f".cursor/rules/opsx-{command_id}.mdr"
    
    def format_file(self, content: CommandContent) -> str:
        return f"""---
name: {content.name}
description: {content.description}
tags: {", ".join(content.tags)}
---

{content.body}"""


class WindsurfAdapter(ToolAdapter):
    tool_id = "windsurf"
    
    def get_file_path(self, command_id: str) -> str:
        return f".windsurfrules/opsx-{command_id}"
    
    def format_file(self, content: CommandContent) -> str:
        return f"""{content.name}

{content.description}

---

{content.body}"""
```

### 4. Template Registry

Centralized management of skills and command generation:

```python
# mypi/templates/registry.py

from dataclasses import dataclass
from pathlib import Path
from mypi.extensions.skill_loader import Skill
from mypi.templates.adapters import ToolAdapter, CommandContent


@dataclass
class WorkflowTemplate:
    """Represents a workflow template with skill and optional command template."""
    skill: Skill
    command_id: str | None = None
    command_tags: list[str] | None = None
    command_category: str | None = None


class TemplateRegistry:
    """Central registry for skills and command generation."""
    
    def __init__(self, skills_dirs: list[Path], commands_dir: Path | None = None):
        self.skills_dirs = [Path(d) for d in skills_dirs]
        self.commands_dir = commands_dir or Path.cwd()
        self._adapters: dict[str, ToolAdapter] = {}
        self._workflows: dict[str, WorkflowTemplate] = {}
    
    def register_adapter(self, adapter: ToolAdapter) -> None:
        self._adapters[adapter.tool_id] = adapter
    
    def load_workflows(self, loader) -> dict[str, WorkflowTemplate]:
        """Load all skills and identify workflow templates."""
        skills = loader.load_skills()
        for skill in skills:
            frontmatter = skill.metadata or {}
            workflow_name = frontmatter.get("workflow")
            if workflow_name:
                self._workflows[workflow_name] = WorkflowTemplate(
                    skill=skill,
                    command_id=frontmatter.get("command_id", skill.name),
                    command_tags=frontmatter.get("tags", []),
                    command_category=frontmatter.get("category", "Workflow"),
                )
        return self._workflows
    
    def generate_commands(
        self, 
        tool_id: str, 
        output_dir: Path | None = None
    ) -> list[Path]:
        """Generate command files for a specific tool."""
        adapter = self._adapters.get(tool_id)
        if not adapter:
            raise ValueError(f"Unknown tool adapter: {tool_id}")
        
        output_dir = output_dir or self.commands_dir
        generated = []
        
        for workflow in self._workflows.values():
            content = CommandContent(
                id=workflow.command_id or workflow.skill.name,
                name=f"OPSX: {workflow.skill.name.title().replace('-', ' ')}",
                description=workflow.skill.description,
                category=workflow.command_category or "Workflow",
                tags=workflow.command_tags or [],
                body=workflow.skill.body or "",
            )
            
            file_path = output_dir / adapter.get_file_path(content.id)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(adapter.format_file(content))
            generated.append(file_path)
        
        return generated
    
    def validate_parity(self) -> list[str]:
        """Validate that skill and command templates are in sync."""
        errors = []
        for name, workflow in self._workflows.items():
            if not workflow.skill.body:
                errors.append(f"Workflow '{name}' has empty skill body")
            if workflow.command_id and not workflow.command_category:
                errors.append(f"Workflow '{name}' has command_id but no category")
        return errors
```

### 5. CLI Integration

New `mypi template` command group:

```python
# mypi/templates/cli.py

import argparse
from pathlib import Path
from mypi.templates.registry import TemplateRegistry
from mypi.templates.adapters import ClaudeAdapter, CursorAdapter, WindsurfAdapter


def add_template_commands(parser: argparse._SubParsersAction) -> None:
    template_parser = parser.add_parser("template", help="Template management")
    sub = template_parser.add_subparsers(dest="template_cmd", required=True)
    
    # List available workflows
    list_parser = sub.add_parser("list", help="List available workflows")
    list_parser.set_defaults(func=_list_workflows)
    
    # Generate commands for a tool
    gen_parser = sub.add_parser("generate", help="Generate command files")
    gen_parser.add_argument("--tool", required=True, 
                           choices=["claude", "cursor", "windsurf"],
                           help="Target AI tool")
    gen_parser.add_argument("--output", type=Path,
                           help="Output directory (default: current directory)")
    gen_parser.set_defaults(func=_generate_commands)
    
    # Validate templates
    validate_parser = sub.add_parser("validate", help="Validate template parity")
    validate_parser.set_defaults(func=_validate_templates)


def _list_workflows(args, registry: TemplateRegistry) -> int:
    workflows = registry.load_workflows()
    if not workflows:
        print("No workflow templates found.")
        return 0
    
    print(f"Found {len(workflows)} workflow templates:\n")
    for name, wf in sorted(workflows.items()):
        print(f"  {name}")
        print(f"    Skill: {wf.skill.name}")
        print(f"    Description: {wf.skill.description}")
        print(f"    Category: {wf.command_category}")
        print()
    return 0


def _generate_commands(args, registry: TemplateRegistry) -> int:
    registry.load_workflows()
    
    adapter_map = {
        "claude": ClaudeAdapter(),
        "cursor": CursorAdapter(),
        "windsurf": WindsurfAdapter(),
    }
    adapter = adapter_map[args.tool]
    registry.register_adapter(adapter)
    
    try:
        generated = registry.generate_commands(args.tool, args.output)
        print(f"Generated {len(generated)} command files:")
        for f in generated:
            print(f"  {f}")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1


def _validate_templates(args, registry: TemplateRegistry) -> int:
    registry.load_workflows()
    errors = registry.validate_parity()
    
    if not errors:
        print("All templates are valid.")
        return 0
    
    print(f"Found {len(errors)} validation errors:\n")
    for error in errors:
        print(f"  - {error}")
    return 1
```

### 6. Artifact Templates

Structured markdown templates for change artifacts:

```
~/.mypi/templates/
├── proposal.md
├── spec.md
├── design.md
└── tasks.md
```

**proposal.md template:**

```markdown
## Why

<!-- Explain the motivation for this change. What problem does this solve? Why now? -->

## What Changes

<!-- Describe what will change. Be specific about new capabilities, modifications, or removals. -->

## Capabilities

### New Capabilities
<!-- Capabilities being introduced. Replace <name> with kebab-case identifier -->
- `<name>`: <brief description of what this capability covers>

### Modified Capabilities
<!-- Existing capabilities whose REQUIREMENTS are changing -->
- `<existing-name>`: <what requirement is changing>

## Impact

<!-- Affected code, APIs, dependencies, systems -->
```

### 7. Integration with Extension System

New extension hook for template events:

```python
# mypi/extensions/base.py

@dataclass
class BeforeTemplateGenerateEvent:
    """Fired before generating command files."""
    tool_id: str
    workflows: list[WorkflowTemplate]
    output_dir: Path


@dataclass  
class AfterTemplateGenerateEvent:
    """Fired after generating command files."""
    tool_id: str
    generated_files: list[Path]


class Extension(ABC):
    # ... existing hooks ...
    
    async def on_before_template_generate(
        self, event: BeforeTemplateGenerateEvent
    ) -> BeforeTemplateGenerateEvent | None:
        return None
    
    async def on_after_template_generate(
        self, event: AfterTemplateGenerateEvent
    ) -> AfterTemplateGenerateEvent | None:
        return None
```

## File Structure

```
mypi/templates/
├── __init__.py
├── adapters.py          # Tool-specific adapters
├── registry.py           # Template registry
├── cli.py               # CLI commands
├── artifacts/
│   ├── __init__.py
│   └── templates/
│       ├── proposal.md
│       ├── spec.md
│       ├── design.md
│       └── tasks.md
└── validators/
    ├── __init__.py
    └── parity.py         # Parity validation tests
```

## Usage Examples

### 1. Creating a New Workflow Skill

Create `~/.mypi/skills/openspec-propose.md`:

```markdown
---
name: openspec-propose
description: Start a new OpenSpec change
category: Workflow
tags: [openspec, change]
workflow: new-change
command_id: propose
---

# OPSX: Propose

Start a new change using the artifact-driven approach.

**Steps**
1. Parse the change name or description
2. Create the change directory
3. Generate artifact files
4. Show status
```

### 2. Generating Claude Code Commands

```bash
# List available workflows
mypi template list

# Generate Claude Code commands
mypi template generate --tool claude

# Generate to specific directory
mypi template generate --tool cursor --output ~/projects/myapp
```

### 3. Generated Output

Creates `.claude/commands/opsx-propose.md`:

```markdown
# OPSX: Propose

Start a new change using the artifact-driven approach.

**Steps**
1. Parse the change name or description
2. Create the change directory
3. Generate artifact files
4. Show status
```

## Backward Compatibility

- **Existing skills**: Unchanged. Skills without `workflow` frontmatter continue to work
- **SkillLoader**: Extended, not modified. `load_skills()` behavior unchanged
- **Extension hooks**: New hooks are optional, existing extensions unaffected

## Testing Strategy

```python
# tests/templates/test_parity.py

def test_all_workflows_have_commands():
    """Every workflow skill should have corresponding command metadata."""
    registry = TemplateRegistry([Path("~/.mypi/skills")])
    workflows = registry.load_workflows()
    
    for name, wf in workflows.items():
        assert wf.command_id is not None, f"Workflow '{name}' missing command_id"
        assert wf.skill.body, f"Workflow '{name}' has empty body"


def test_claude_adapter_format():
    """Claude adapter generates valid markdown commands."""
    adapter = ClaudeAdapter()
    content = CommandContent(
        id="propose",
        name="OPSX: Propose",
        description="Start a change",
        category="Workflow",
        tags=["openspec"],
        body="# Steps\n1. Do this",
    )
    
    formatted = adapter.format_file(content)
    assert formatted.startswith("# OPSX: Propose")
    assert "# Steps" in formatted


def test_generate_creates_files():
    """generate_commands creates expected file structure."""
    registry = TemplateRegistry([Path("~/.mypi/skills")])
    registry.register_adapter(ClaudeAdapter())
    registry.load_workflows()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        generated = registry.generate_commands("claude", Path(tmpdir))
        
        assert len(generated) > 0
        assert all(p.suffix == ".md" for p in generated)
        assert all(
            str(p).startswith(str(tmpdir) + "/.claude/commands/")
            for p in generated
        )
```

## Implementation Phases

### Phase 1: Core Types (Low Effort)

- [ ] Define `CommandContent`, `WorkflowTemplate` dataclasses
- [ ] Create base `ToolAdapter` abstract class
- [ ] Implement `ClaudeAdapter`, `CursorAdapter`, `WindsurfAdapter`

### Phase 2: Registry (Medium Effort)

- [ ] Implement `TemplateRegistry` class
- [ ] Extend `SkillLoader` to parse new frontmatter fields
- [ ] Add `generate_commands()` method
- [ ] Add `validate_parity()` method

### Phase 3: CLI Integration (Medium Effort)

- [ ] Add `mypi template` command group
- [ ] Implement `list`, `generate`, `validate` subcommands
- [ ] Add completion for `--tool` argument

### Phase 4: Artifact Templates (Low Effort)

- [ ] Create `~/.mypi/templates/` directory with default templates
- [ ] Add `proposal.md`, `spec.md`, `design.md`, `tasks.md`
- [ ] Document template usage in README

### Phase 5: Extension Integration (Low Effort)

- [ ] Add `BeforeTemplateGenerateEvent`, `AfterTemplateGenerateEvent`
- [ ] Implement hook firing in `TemplateRegistry.generate_commands()`
- [ ] Update `Extension` base class with new hooks

## Alternatives Considered

### Option A: Keep Skills as-is, Add Separate Command System

Pros: Minimal changes to existing system
Cons: Duplication, parity drift between skill and command definitions

### Option B: Full OpenSpec Port

Pros: Complete feature parity with OpenSpec
Cons: Significant effort, TypeScript→Python translation, overkill for mypi's scope

### Option C: Hybrid (Proposed)

Best balance of features and implementation cost. Extends existing skills rather than replacing them, adds command generation as an optional layer.

## Open Questions

1. **Should artifact templates be file-based or inline in skill frontmatter?**
   - File-based: More flexible, supports versioning
   - Inline: Simpler, all in one place

2. **Should generated commands live in project directory or skill directory?**
   - Project directory: Matches Claude Code/Cursor conventions
   - Skill directory: Easier to distribute with skill package

3. **Should we support skill versioning?**
   - OpenSpec uses metadata for versioning; could add `version` to frontmatter

## References

- [OpenSpec Template System](https://zread.ai/Fission-AI/OpenSpec/23-template-system)
- [Claude Code Commands](https://docs.anthropic.com/en/docs/claude-code/commands)
- [Cursor Rules](https://cursor.directory/)
- mypi `template-system.md` — Research findings
