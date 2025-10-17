# AI Agent Tools

This directory contains tools that extend the capabilities of AI agents in the TheOrb system.

## Available Tools

### DateTimeTool (`get_datetime`)
Provides current date and time information with various formatting options.

**Parameters:**
- `format` (string): Output format - "human", "iso", "date", "time", "timestamp", or custom strftime format
- `timezone` (string): Timezone - "UTC" or "local" (default: local)
- `component` (string): Get specific component - "year", "month", "day", "hour", "minute", "second", "weekday"

**Examples:**
```json
{"format": "human"}          // Returns: "2025-09-29 11:45:06"
{"format": "date"}           // Returns: "2025-09-29"
{"component": "weekday"}     // Returns: "Monday"
```

### CalculatorTool (`calculate`)
Performs mathematical calculations with support for various operations.

**Parameters:**
- `expression` (string, required): Mathematical expression to evaluate
- `precision` (integer): Number of decimal places (default: 10, max: 15)

**Supported Operations:**
- Basic arithmetic: `+`, `-`, `*`, `/`, `**`, `%`
- Functions: `sin`, `cos`, `tan`, `sqrt`, `log`, `ln`, `abs`, `ceil`, `floor`
- Constants: `pi`, `e`, `tau`

**Examples:**
```json
{"expression": "2 + 3 * 4"}        // Returns: 14
{"expression": "sqrt(16)"}         // Returns: 4
{"expression": "sin(pi/2)"}        // Returns: 1
```

## Using Tools in Agents

Tools are integrated into the BasicAgent through the ToolManager. When an agent needs to use a tool, it should respond with a tool call in this format:

```
TOOL_CALL: tool_name(parameters)
```

Examples:
- `TOOL_CALL: get_datetime({"format": "human"})`
- `TOOL_CALL: calculate({"expression": "15 * 23"})`

The agent will automatically detect these tool calls, execute them, and replace them with the results.

## Adding New Tools

To add a new tool:

1. Create a new file in this directory that extends `BaseTool`
2. Implement the required methods: `get_name()`, `get_description()`, `get_parameters()`, `execute()`
3. Register the tool in `ToolManager.__init__()`
4. Add it to the `__init__.py` imports

Example:
```python
from .base_tool import BaseTool

class MyTool(BaseTool):
    def get_name(self) -> str:
        return "my_tool"

    def get_description(self) -> str:
        return "Description of what my tool does"

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "Parameter description"}
            },
            "required": ["param1"]
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        # Tool implementation
        return {"success": True, "result": "tool output"}
```

## Architecture

- **BaseTool**: Abstract base class that all tools must inherit from
- **ToolManager**: Manages tool registration and execution
- **Integration**: Tools are integrated into agents through the `_process_tool_calls()` method

The system uses a simple text-based protocol for tool calls, making it easy for LLMs to generate and for the system to parse and execute.