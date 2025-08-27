from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from anthropic import Anthropic
import os

class BaseAgent(ABC):
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the base agent."""
        self.client = Anthropic(api_key=api_key or os.getenv('ANTHROPIC_API_KEY'))
        self.debug = True

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        pass

    @abstractmethod
    def get_agent_name(self) -> str:
        """Return the name of this agent."""
        pass

    @abstractmethod
    def process_request(self, user_message: str, context: str = "", 
                       conversation_history: Optional[List[Dict[str, str]]] = None,
                       progress_callback: Optional[callable] = None,
                       collection_name: Optional[str] = None) -> Dict[str, Any]:
        """Process a user request and return the response."""
        pass

    def _make_api_call(self, messages: List[Dict[str, str]], system_prompt: str, 
                      max_tokens: int = 1000) -> str:
        """Make an API call to Claude."""
        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages
            )
            return response.content[0].text
        except Exception as e:
            if self.debug:
                print(f"API call error in {self.get_agent_name()}: {str(e)}")
            return f"Error generating response: {str(e)}"

    def _build_messages(self, user_message: str, context: str = "", 
                       conversation_history: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
        """Build messages list for API call."""
        messages = []
        
        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history[-10:]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # Prepare the user message with context
        user_content = user_message
        if context:
            user_content = f"{context}\n\n--- User Question ---\n{user_message}"
        
        messages.append({
            "role": "user",
            "content": user_content
        })
        
        return messages