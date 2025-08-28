from typing import Dict, Any, Optional, List
from .base_agent import BaseAgent
from .basic_agent import BasicAgent
from .verification_agent import VerificationAgent
from .deep_research_agent import DeepResearchAgent

class AgentManager:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the agent manager with available agents."""
        self.api_key = api_key
        self._agents = {}
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize all available agents."""
        self._agents = {
            'basic': BasicAgent(self.api_key),
            'verification': VerificationAgent(self.api_key),
            'deep_research': DeepResearchAgent(self.api_key)
        }
        
        # Set basic agent as default
        self.default_agent = 'basic'
    
    def get_available_agents(self) -> List[Dict[str, str]]:
        """Get list of available agents with their descriptions."""
        agents_info = []
        for agent_name, agent in self._agents.items():
            agents_info.append({
                'name': agent_name,
                'display_name': agent.get_agent_name(),
                'description': self._get_agent_description(agent_name),
                'is_default': agent_name == self.default_agent
            })
        return agents_info
    
    def _get_agent_description(self, agent_name: str) -> str:
        """Get description for each agent."""
        descriptions = {
            'basic': 'Fast single-pass responses without verification',
            'verification': 'Verifies information accuracy using a two-step process',
            'deep_research': 'Performs deep research by searching user data and web sources'
        }
        return descriptions.get(agent_name, 'AI agent')
    
    def get_agent(self, agent_name: Optional[str] = None) -> BaseAgent:
        """Get an agent by name, defaults to basic agent."""
        if not agent_name or agent_name not in self._agents:
            agent_name = self.default_agent
        return self._agents[agent_name]
    
    def process_request(self, user_message: str, agent_name: Optional[str] = None,
                       context: str = "", conversation_history: Optional[List[Dict[str, str]]] = None,
                       progress_callback: Optional[callable] = None,
                       collection_name: Optional[str] = None) -> Dict[str, Any]:
        """Process a request using the specified agent."""
        agent = self.get_agent(agent_name)
        
        # Add agent information to the response
        result = agent.process_request(
            user_message=user_message,
            context=context,
            conversation_history=conversation_history,
            progress_callback=progress_callback,
            collection_name=collection_name
        )
        
        # Add metadata about which agent was used
        result['agent_used'] = agent_name or self.default_agent
        result['agent_display_name'] = agent.get_agent_name()
        
        return result
    
    def detect_agent_from_message(self, user_message: str) -> str:
        """Detect which agent to use based on the user message."""
        message_lower = user_message.lower()
        
        # Check for deep research keywords
        research_keywords = [
            'deep research', 'research', 'search web', 'find articles', 
            'web search', 'latest news', 'current information', 'recent studies'
        ]
        
        if any(keyword in message_lower for keyword in research_keywords):
            return 'deep_research'
        
        # Check for basic/fast response keywords
        basic_keywords = [
            'quick', 'fast', 'simple', 'basic', 'no verification'
        ]
        
        if any(keyword in message_lower for keyword in basic_keywords):
            return 'basic'
        
        # Check for verification keywords
        verification_keywords = [
            'verify', 'check', 'accurate', 'verify this', 'is this correct'
        ]
        
        if any(keyword in message_lower for keyword in verification_keywords):
            return 'verification'
        
        # Default to basic agent for faster responses
        return 'basic'