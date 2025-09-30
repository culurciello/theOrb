from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseTool(ABC):
    """Base class for all AI agent tools."""

    @abstractmethod
    def get_name(self) -> str:
        """Return the name of the tool."""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Return a description of what the tool does."""
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Return the parameters schema for the tool in JSON schema format."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given parameters and return the result."""
        pass

    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate parameters against the schema. Override for custom validation."""
        return True

    def to_function_schema(self) -> Dict[str, Any]:
        """Convert tool to OpenAI function calling schema."""
        return {
            "name": self.get_name(),
            "description": self.get_description(),
            "parameters": self.get_parameters()
        }