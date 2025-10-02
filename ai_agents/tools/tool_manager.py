from typing import Dict, Any, List, Optional
import json
from .base_tool import BaseTool
from .datetime_tool import DateTimeTool
from .calculator_tool import CalculatorTool
from .search_pubmed_tool import SearchPubmedTool


class ToolManager:
    """Manages tools for AI agents."""

    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """Register the default tools."""
        self.register_tool(DateTimeTool())
        self.register_tool(CalculatorTool())
        self.register_tool(SearchPubmedTool())

    def register_tool(self, tool: BaseTool):
        """Register a tool."""
        self.tools[tool.get_name()] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self.tools.get(name)

    def get_all_tools(self) -> Dict[str, BaseTool]:
        """Get all registered tools."""
        return self.tools.copy()

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get the schema for all tools in OpenAI function calling format."""
        return [tool.to_function_schema() for tool in self.tools.values()]

    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with given parameters."""
        tool = self.get_tool(tool_name)
        if not tool:
            return {"error": f"Tool '{tool_name}' not found"}

        try:
            if not tool.validate_parameters(parameters):
                return {"error": f"Invalid parameters for tool '{tool_name}'"}

            result = tool.execute(**parameters)
            return result
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}

    def get_tools_description(self) -> str:
        """Get a human-readable description of all available tools."""
        descriptions = []
        for tool in self.tools.values():
            descriptions.append(f"- {tool.get_name()}: {tool.get_description()}")
        return "\n".join(descriptions)