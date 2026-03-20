from __future__ import annotations
from mypi.tools.base import Tool, ToolResult


class SkillTool(Tool):
    name = "skill"
    description = "Load a skill's full content by name. Call this when you want to use a specific skill's instructions."
    input_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Name of the skill to load"},
        },
        "required": ["name"],
    }

    def __init__(self, skill_loader_getter):
        self._get_loader = skill_loader_getter

    async def execute(self, name: str) -> ToolResult:
        loader = self._get_loader()
        if loader is None:
            return ToolResult(error="No skill loader configured")
        skill = loader.load_skill_content(name)
        if skill is None:
            return ToolResult(error=f"Skill not found: {name}")
        return ToolResult(output=skill.body or "")
