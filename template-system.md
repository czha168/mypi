# OpenSpec Template System Research

## Overview

This document captures findings from researching the OpenSpec template system at [zread.ai/Fission-AI/OpenSpec/23-template-system](https://zread.ai/Fission-AI/OpenSpec/23-template-system) with integration insights from `opsx-propose.md`.

The OpenSpec template system provides a structured mechanism for defining reusable AI skill templates and slash command definitions. It enables consistent AI agent behavior and command generation across multiple AI tools through a unified, tool-agnostic interface.

---

## Architecture

The template system operates on a **dual-layer architecture**:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Template System                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────────────┐    ┌──────────────────────┐         │
│   │   Skill Templates    │    │  Command Templates   │         │
│   │                      │    │                      │         │
│   │  Define AI agent    │    │  Define slash cmd   │         │
│   │  behaviors &         │    │  formatting for     │         │
│   │  instructions        │    │  specific tools     │         │
│   └──────────┬───────────┘    └──────────┬───────────┘         │
│              │                            │                      │
│              └────────────┬────────────────┘                      │
│                           ▼                                       │
│              ┌────────────────────────┐                          │
│              │ Command Generation     │                          │
│              │ Layer                  │                          │
│              │                        │                          │
│              │ Adapts templates for   │                          │
│              │ Claude, Cursor,        │                          │
│              │ Windsurf, etc.         │                          │
│              └────────────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

### Key Insight: Separation of Concerns

- **Skill Templates** = Tool-agnostic AI agent instructions
- **Command Templates** = Tool-specific slash command formatting
- **Command Generation** = Adapter layer that transforms templates for different AI environments

This separation allows the same core instructions to work across 20+ AI development tools without code duplication.

---

## Core Template Types

### SkillTemplate Interface

Defines AI agent behaviors with structured instructions:

```typescript
interface SkillTemplate {
  name: string;
  description: string;
  instructions: string;        // Step-by-step guidance
  license?: string;
  compatibility?: string;
  metadata?: Record<string, string>;
}
```

### CommandTemplate Interface

Defines slash command structures with categorization:

```typescript
interface CommandTemplate {
  name: string;
  description: string;
  category: string;            // e.g., "Workflow", "Navigation"
  tags: string[];             // e.g., ["workflow", "change"]
  content: string;            // Tool-agnostic content
}
```

### CommandContent Interface

Tool-agnostic command data without formatting:

```typescript
interface CommandContent {
  id: string;
  name: string;
  description: string;
  category: string;
  tags: string[];
  body: string;
}
```

### ToolCommandAdapter Interface

Each AI tool implements this interface:

```typescript
interface ToolCommandAdapter {
  toolId: string;
  getFilePath(commandId: string): string;
  formatFile(content: CommandContent): string;
}
```

---

## Workflow Template Modules

Workflow modules organize skill and command templates for specific OpenSpec operations.

### Available Workflows

| Workflow | Skill Template | Command Template | Purpose |
|----------|---------------|------------------|---------|
| `new-change` | `getNewChangeSkillTemplate` | `getOpsxNewCommandTemplate` | Initialize new changes with artifact workflow |
| `apply-change` | `getApplyChangeSkillTemplate` | `getOpsxApplyCommandTemplate` | Apply completed changes to codebase |
| `continue-change` | `getContinueChangeSkillTemplate` | `getOpsxContinueCommandTemplate` | Resume work on active changes |
| `archive-change` | `getArchiveChangeSkillTemplate` | `getOpsxArchiveCommandTemplate` | Archive completed changes |
| `verify-change` | `getVerifyChangeSkillTemplate` | `getOpsxVerifyCommandTemplate` | Validate change implementations |
| `onboard` | `getOnboardSkillTemplate` | `getOpsxOnboardCommandTemplate` | Guided onboarding experience |
| `explore` | `getExploreSkillTemplate` | `getOpsxExploreCommandTemplate` | Explore codebase patterns |
| `sync-specs` | `getSyncSpecsSkillTemplate` | `getOpsxSyncCommandTemplate` | Synchronize specifications |
| `feedback` | `getFeedbackSkillTemplate` | — | Provide system feedback |

### Example: new-change Workflow

The `new-change` workflow demonstrates the structure:

```typescript
export function getNewChangeSkillTemplate(): SkillTemplate {
  return {
    name: 'openspec-new-change',
    description: 'Start a new OpenSpec change using the experimental artifact workflow.',
    instructions: `Start a new change using the experimental artifact-driven approach.
 
**Input**: The user's request should include a change name (kebab-case) OR a description.
 
**Steps**
 
1. **If no clear input provided, ask what they want to build**
   Use the **AskUserQuestion tool** to ask:
   > "What change do you want to work on? Describe what you want to build or fix."
 
2. **Determine the workflow schema**
   Use the default schema unless the user explicitly requests a different workflow.
 
3. **Create the change directory**
   \`\`\`bash
   openspec new change "<name>"
   \`\`\`
 
4. **Show the artifact status**
   \`\`\`bash
   openspec status --change "<name>"
   \`\`\`
   ...`,
  };
}
```

---

## Artifact Templates

Artifact templates provide structured markdown for change artifacts in `schemas/spec-driven/templates/`:

```
schemas/spec-driven/templates/
├── proposal.md    # Proposal template
├── spec.md        # Specification template
├── design.md      # Design document template
└── tasks.md       # Task breakdown template
```

### Proposal Template Structure

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

---

## Command Generation System

The command generation system transforms tool-agnostic templates into AI tool-specific command files.

### Supported Tool Adapters

| Tool | Adapter ID | Scope | Command Path |
|------|-----------|-------|--------------|
| Claude | `claude` | Project | `.claude/commands/opsx/{id}.md` |
| Cursor | `cursor` | Project | `.cursor/rules/opsx-{id}.mdr` |
| Windsurf | `windsurf` | Project | `.windsurfrules/opsx-{id}` |
| Codeium | `auggie` | Project | `.codeium/prompts/opsx_{id}.md` |
| Continue | `continue` | Project | `.continue/opsx_{id}.md` |
| Codex | `codex` | Global | `~/.codex/skills/openspec-{id}.json` |
| GitHub Copilot | `github-copilot` | Project | `.github/copilot-instructions.md` |

### Generation Flow

```
SkillTemplate + CommandTemplate
         │
         ▼
   CommandContent (tool-agnostic)
         │
         ▼
   ToolCommandAdapter.formatFile()
         │
         ▼
   Tool-specific command file
```

---

## Template Registry and Exports

Centralized export facade:

```typescript
// Template exports for OpenSpec
export * from './skill-templates.js';
export type { SkillTemplate, CommandTemplate } from './types.js';

export { getExploreSkillTemplate, getOpsxExploreCommandTemplate } from './workflows/explore.js';
export { getNewChangeSkillTemplate, getOpsxNewCommandTemplate } from './workflows/new-change.js';
// ... additional workflow exports
```

---

## Integration with OpenSpec Systems

### Change System Integration

Templates work with the Change Schema:

```typescript
export const ChangeSchema = z.object({
  name: z.string().min(1),
  why: z.string().min(MIN_WHY_SECTION_LENGTH),
  whatChanges: z.string().min(1),
  deltas: z.array(DeltaSchema).min(1).max(MAX_DELTAS_PER_CHANGE),
  metadata: z.object({
    version: z.string().default('1.0.0'),
    format: z.literal('openspec-change'),
    sourcePath: z.string().optional(),
  }).optional(),
});
```

### Artifact Graph Integration

Templates define structure for artifacts in the Artifact Graph. Each artifact type (proposal, spec, design, tasks) has a corresponding template.

---

## Extension Pattern: `/opsx:propose`

From `opsx-propose.md` research, the interactive prompt pattern is critical:

### OpenSpec Behavior

```
/opsx:propose              → Interactive prompt for change name
/opsx:propose <name>       → Direct change creation
/opsx:propose <description>→ Natural language → kebab-case conversion
```

### Implementation Options

**Option 1: Interactive Name Collection (Recommended)**

```python
async def execute(self, workspace, artifacts, args, agent_prompt_callback=None):
    change_name = self._parse_change_name(args)
    
    # If no name provided, engage in brief dialogue
    if not change_name and agent_prompt_callback:
        prompt_response = await agent_prompt_callback(
            "What would you like to work on? Describe the change in a few words.\n"
            "Example: 'Add dark mode support' or 'Fix the login bug'"
        )
        change_name = self._parse_change_name(prompt_response)
        
        if not change_name:
            return CommandResult(
                success=False,
                message="Could not determine a change name. Please try again with: /opsx:propose <name>"
            )
```

**Option 2: Quick Name Generation**

```
/opsx:propose 
→ Creates: openspec/changes/change-2026-03-20-143052/
→ Prompts user to rename later via /opsx:rename
```

**Option 3: Require Name (Strict)**

Keep current behavior requiring a name, but improve error message with suggestions.

### Edge Cases

| Case | Current | OpenSpec |
|------|---------|----------|
| Empty/whitespace input | Returns error | Prompts again |
| Very long description | Fails validation | Truncates/sanitizes |
| Special characters | Rejected by regex | Sanitizes |
| Duplicate names | Overwrites | Prompts confirmation |

---

## Extending the Template System

### Creating a New Workflow Template

1. Create file in `src/core/templates/workflows/`
2. Export two functions: `get{WorkflowName}SkillTemplate()` and `getOpsx{CommandName}CommandTemplate()`
3. Add exports to `src/core/templates/skill-templates.ts`

```typescript
import type { SkillTemplate, CommandTemplate } from '../types.js';

export function getCustomWorkflowSkillTemplate(): SkillTemplate {
  return {
    name: 'openspec-custom-workflow',
    description: 'Description of your custom workflow',
    instructions: `Step-by-step instructions...`,
  };
}

export function getOpsxCustomCommandTemplate(): CommandTemplate {
  return {
    name: 'OPSX: Custom',
    description: 'Description',
    category: 'Workflow',
    tags: ['workflow', 'custom'],
    content: `Command content...`,
  };
}
```

### Creating a New Tool Adapter

```typescript
import type { ToolCommandAdapter, CommandContent } from '../types.js';

export class NewToolAdapter implements ToolCommandAdapter {
  toolId = 'new-tool';

  getFilePath(commandId: string): string {
    return `.new-tool/commands/${commandId}.md`;
  }

  formatFile(content: CommandContent): string {
    return `---
name: ${content.name}
description: ${content.description}
---
${content.body}`;
  }
}
```

---

## Template Validation

Parity tests ensure consistency between skill and command templates:

```typescript
// test/core/templates/skill-templates-parity.test.ts
// Validates that every skill template has a corresponding command template
// and that content remains consistent across formats
```

---

## Best Practices

1. **Maintain Parity**: Ensure skill templates and command templates remain synchronized
2. **Use Clear Instructions**: Step-by-step guidance without ambiguity
3. **Include Guardrails**: Define what operations should NOT be performed
4. **Leverage Metadata**: Use for versioning and compatibility tracking
5. **Test with Real Tools**: Validate generated commands work in target environments

---

## Relevance to mypi

The mypi project implements a minimalist terminal-based coding assistant inspired by pi-coding-agent. Key integration points:

| OpenSpec Concept | mypi Equivalent |
|-----------------|-----------------|
| Skill Templates | Markdown skills with YAML frontmatter in `~/.mypi/skills/` |
| Command Templates | Slash commands in `mypi/extensions/openspec/commands.py` |
| Tool Adapters | Extension system for multi-tool support |
| Artifact Templates | Could use markdown templates for structured change artifacts |
| Workflow Modules | Command implementations (`ProposeCommand`, `ExploreCommand`, etc.) |

### Recommended mypi Extensions

1. **Template Registry**: Centralize skill/command exports similar to OpenSpec's `index.ts`
2. **Artifact Templates**: Add markdown templates for proposals, specs, designs, tasks
3. **Interactive Prompts**: Implement Option 1 for `/opsx:propose` without name argument
4. **Tool Adapters**: Create adapter pattern for generating Claude Code/Cursor commands from templates

---

## References

- [OpenSpec Template System](https://zread.ai/Fission-AI/OpenSpec/23-template-system)
- [OpenSpec Commands Reference](https://github.com/Fission-AI/OpenSpec/blob/main/docs/commands.md)
- mypi `opsx-propose.md` — Integration research
