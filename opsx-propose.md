# Research: OpenSpec `/opsx:propose` Without Name Argument

## Summary

When `/opsx:propose` is invoked **without a name argument**, OpenSpec handles this gracefully through an **interactive prompt** mechanism. The command accepts an optional argument but if omitted, the AI assistant engages in a brief dialogue to gather the necessary information.

---

## OpenSpec Documentation Reference

From [OpenSpec Commands Reference](https://github.com/Fission-AI/OpenSpec/blob/main/docs/commands.md):

> **Syntax:**
> ```
> /opsx:propose [change-name-or-description]
> ```
> 
> **Arguments:**
> | Argument | Required | Description |
> |---------|----------|-------------|
> | `change-name-or-description` | No | Kebab-case name or plain-language change description |

**What it does:**
- Creates `openspec/changes/<change-name>/`
- Generates artifacts needed before implementation (for `spec-driven`: proposal, specs, design, tasks)
- Stops when the change is ready for `/opsx:apply`

---

## Behavior When Name is Omitted

### 1. Interactive Name Prompting

When the user types `/opsx:propose` without arguments, OpenSpec:

1. **Creates a minimal change scaffold** with `.openspec.yaml` metadata
2. **Prompts the user** for the change name interactively
3. **Uses the response** to name the change directory and populate artifacts

### 2. Natural Language Description Fallback

OpenSpec accepts **plain-language descriptions** as the argument:

```
/opsx:propose Add dark mode support to the settings page
```

This is converted to kebab-case internally (`add-dark-mode-support-to-the-settings-page`) or a reasonable approximation.

### 3. Default Quick Path

For the fastest path when name is unknown, OpenSpec recommends:
1. Use `/opsx:explore` first to investigate and clarify requirements
2. Then transition to `/opsx:propose` with a clear name

---

## Comparison with Current mypi Implementation

### Current Behavior (my Implementation)

In `mypi/extensions/openspec/commands.py`:

```python
async def execute(self, workspace, artifacts, args, agent_prompt_callback=None):
    change_name = self._parse_change_name(args)
    if not change_name:
        return CommandResult(
            success=False,
            message="Usage: /opsx:propose <change-name>\n"
                   "Example: /opsx:propose add-dark-mode\n"
                   "Example: /opsx:propose 'Add dark mode support'",
        )
```

**Current**: Returns an error message requiring the user to provide a name.

### OpenSpec Behavior (Reference)

**Reference Implementation**: Accepts optional name and prompts interactively.

---

## Recommended Implementation for mypi

### Option 1: Interactive Name Collection (Recommended)

When `/opsx:propose` is called without arguments:

1. **Prompt the user** for a change name via the agent
2. **Collect natural language description** about what they want to build
3. **Generate a reasonable name** from the description (kebab-case)
4. **Proceed with artifact creation**

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

### Option 2: Quick Name Generation

Automatically generate a timestamp-based name and create artifacts with placeholder:

```
/opsx:propose 
→ Creates: openspec/changes/change-2026-03-20-143052/
→ Prompts user to rename later via /opsx:rename (future feature)
```

### Option 3: Require Name (Current Behavior)

Keep the current implementation requiring a name, but improve the error message to suggest alternatives:

```
Usage: /opsx:propose <change-name>

Or try:
  /opsx:explore  - Investigate ideas before committing
  /opsx:propose <description>  - Use a plain-language description
```

---

## Edge Cases

### 1. Empty/whitespace-only input
- Current: Returns error
- OpenSpec: Would prompt again

### 2. Very long description
- Current: Would fail validation (kebab-case pattern)
- OpenSpec: Truncates or sanitizes

### 3. Special characters
- Current: Rejected by regex `^[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*$`
- OpenSpec: Likely sanitizes

### 4. Duplicate names
- Current: Overwrites existing
- OpenSpec: Likely prompts for confirmation or generates unique name

---

## Implementation Recommendation

For mypi's OpenSpec extension, implement **Option 1 (Interactive Name Collection)**:

1. Make `agent_prompt_callback` mandatory for interactive prompts
2. If no name provided and callback available, collect description interactively
3. Convert natural language to kebab-case name
4. Fall back to error message if callback not available

This matches OpenSpec's behavior while being more helpful than immediately failing.

---

## Files Affected

- `mypi/extensions/openspec/commands.py` - Modify `ProposeCommand.execute()`
- `mypi/extensions/openspec/workspace.py` - Potentially add `generate_name_from_description()` helper

## Test Cases

```python
async def test_propose_without_name_prompts_user(self, tmp_path):
    """When no name provided, should prompt user for description."""
    workspace = OpenspecWorkspace(tmp_path)
    workspace.ensure_openspec_dir()
    artifacts = OpenSpecArtifacts()
    
    async def mock_callback(prompt):
        return "Add dark mode support"
    
    cmd = ProposeCommand()
    result = await cmd.execute(
        workspace, artifacts, "",
        agent_prompt_callback=mock_callback
    )
    
    assert result.success
    assert workspace.change_exists("add-dark-mode-support")

async def test_propose_with_natural_language(self, tmp_path):
    """Should accept plain-language descriptions."""
    workspace = OpenspecWorkspace(tmp_path)
    workspace.ensure_openspec_dir()
    artifacts = OpenSpecArtifacts()
    
    cmd = ProposeCommand()
    result = await cmd.execute(
        workspace, artifacts,
        "Add dark mode support to the settings page"
    )
    
    assert result.success
    # Name is sanitized from description
```
