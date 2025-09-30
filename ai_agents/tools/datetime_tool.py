from datetime import datetime, timezone
from typing import Dict, Any, Optional
from .base_tool import BaseTool


class DateTimeTool(BaseTool):
    """Tool for getting current date and time information."""

    def get_name(self) -> str:
        return "get_datetime"

    def get_description(self) -> str:
        return "Get current date and time information. Can return current datetime, format it in different ways, or get specific components like day, month, year, etc."

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "description": "The format for the datetime output. Options: 'iso', 'human', 'date', 'time', 'timestamp', or custom strftime format",
                    "default": "human"
                },
                "timezone": {
                    "type": "string",
                    "description": "Timezone for the datetime (e.g., 'UTC', 'local'). Default is local time",
                    "default": "local"
                },
                "component": {
                    "type": "string",
                    "description": "Get specific component: 'year', 'month', 'day', 'hour', 'minute', 'second', 'weekday'",
                    "enum": ["year", "month", "day", "hour", "minute", "second", "weekday"]
                }
            },
            "required": []
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        try:
            format_type = kwargs.get("format", "human")
            timezone_param = kwargs.get("timezone", "local")
            component = kwargs.get("component")

            # Get current datetime
            if timezone_param.lower() == "utc":
                now = datetime.now(timezone.utc)
            else:
                now = datetime.now()

            # If specific component requested
            if component:
                if component == "year":
                    value = now.year
                elif component == "month":
                    value = now.month
                elif component == "day":
                    value = now.day
                elif component == "hour":
                    value = now.hour
                elif component == "minute":
                    value = now.minute
                elif component == "second":
                    value = now.second
                elif component == "weekday":
                    value = now.strftime("%A")
                else:
                    return {"error": f"Unknown component: {component}"}

                return {
                    "success": True,
                    "component": component,
                    "value": value,
                    "full_datetime": now.isoformat()
                }

            # Format the datetime
            if format_type == "iso":
                formatted_time = now.isoformat()
            elif format_type == "human":
                formatted_time = now.strftime("%Y-%m-%d %H:%M:%S %Z").strip()
            elif format_type == "date":
                formatted_time = now.strftime("%Y-%m-%d")
            elif format_type == "time":
                formatted_time = now.strftime("%H:%M:%S")
            elif format_type == "timestamp":
                formatted_time = str(int(now.timestamp()))
            else:
                # Custom strftime format
                try:
                    formatted_time = now.strftime(format_type)
                except ValueError as e:
                    return {"error": f"Invalid format string: {e}"}

            return {
                "success": True,
                "datetime": formatted_time,
                "timestamp": int(now.timestamp()),
                "timezone": str(now.tzinfo) if now.tzinfo else "local",
                "iso_format": now.isoformat()
            }

        except Exception as e:
            return {"error": f"Failed to get datetime: {str(e)}"}