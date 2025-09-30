import math
import re
from typing import Dict, Any, Union
from .base_tool import BaseTool


class CalculatorTool(BaseTool):
    """Tool for performing mathematical calculations."""

    def get_name(self) -> str:
        return "calculate"

    def get_description(self) -> str:
        return "Perform mathematical calculations including basic arithmetic, trigonometric functions, logarithms, and other mathematical operations. Supports expressions like '2 + 3 * 4', 'sin(pi/2)', 'sqrt(16)', etc."

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to evaluate. Supports +, -, *, /, **, %, sin, cos, tan, log, ln, sqrt, abs, ceil, floor, pi, e, and parentheses."
                },
                "precision": {
                    "type": "integer",
                    "description": "Number of decimal places to round the result to (default: 10)",
                    "default": 10,
                    "minimum": 0,
                    "maximum": 15
                }
            },
            "required": ["expression"]
        }

    def _safe_eval(self, expression: str) -> Union[float, int]:
        """Safely evaluate a mathematical expression."""
        # Define allowed names for evaluation
        allowed_names = {
            "__builtins__": {},
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "pow": pow,
            # Math functions
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "asin": math.asin,
            "acos": math.acos,
            "atan": math.atan,
            "atan2": math.atan2,
            "sinh": math.sinh,
            "cosh": math.cosh,
            "tanh": math.tanh,
            "log": math.log10,
            "ln": math.log,
            "log10": math.log10,
            "log2": math.log2,
            "sqrt": math.sqrt,
            "exp": math.exp,
            "ceil": math.ceil,
            "floor": math.floor,
            "factorial": math.factorial,
            "degrees": math.degrees,
            "radians": math.radians,
            # Constants
            "pi": math.pi,
            "e": math.e,
            "tau": math.tau,
        }

        # Clean and validate the expression
        expression = expression.strip()

        # Check for dangerous patterns
        dangerous_patterns = [
            r'__\w+__',  # Dunder methods
            r'import\s+',  # Import statements
            r'exec\s*\(',  # Exec calls
            r'eval\s*\(',  # Eval calls
            r'open\s*\(',  # File operations
            r'input\s*\(',  # Input operations
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, expression, re.IGNORECASE):
                raise ValueError(f"Unsafe expression: contains forbidden pattern")

        # Replace common mathematical notation
        expression = expression.replace('^', '**')  # Power operator

        try:
            result = eval(expression, allowed_names)
            return result
        except Exception as e:
            raise ValueError(f"Invalid mathematical expression: {str(e)}")

    def execute(self, **kwargs) -> Dict[str, Any]:
        try:
            expression = kwargs.get("expression")
            precision = kwargs.get("precision", 10)

            if not expression:
                return {"error": "No expression provided"}

            # Validate precision
            if not isinstance(precision, int) or precision < 0 or precision > 15:
                precision = 10

            # Evaluate the expression
            result = self._safe_eval(expression)

            # Handle the result
            if isinstance(result, (int, float)):
                if isinstance(result, float):
                    # Round to specified precision
                    rounded_result = round(result, precision)
                    # Convert to int if it's a whole number
                    if rounded_result == int(rounded_result):
                        final_result = int(rounded_result)
                    else:
                        final_result = rounded_result
                else:
                    final_result = result

                return {
                    "success": True,
                    "expression": expression,
                    "result": final_result,
                    "raw_result": result,
                    "precision": precision
                }
            else:
                return {"error": f"Result is not a number: {type(result).__name__}"}

        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Calculation failed: {str(e)}"}