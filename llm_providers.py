from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import json
import requests
from anthropic import Anthropic
from llm_config import LLMConfig, LLMProvider

class BaseLLMProvider(ABC):
    """Base class for all LLM providers."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        
    @abstractmethod
    def generate_response(self, messages: List[Dict[str, str]], system_prompt: str = "") -> str:
        """Generate a response using the LLM."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and properly configured."""
        pass

class AnthropicProvider(BaseLLMProvider):
    """Provider for Anthropic Claude models."""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = None
        if config.api_key:
            try:
                self.client = Anthropic(api_key=config.api_key)
            except Exception as e:
                print(f"Error initializing Anthropic client: {e}")
    
    def generate_response(self, messages: List[Dict[str, str]], system_prompt: str = "") -> str:
        """Generate response using Anthropic Claude."""
        if not self.client:
            return "Error: Anthropic client not properly configured"
        
        try:
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt,
                messages=messages
            )
            return response.content[0].text
        except Exception as e:
            return f"Error generating Anthropic response: {str(e)}"
    
    def is_available(self) -> bool:
        """Check if Anthropic is available."""
        return self.client is not None and bool(self.config.api_key)

class OllamaProvider(BaseLLMProvider):
    """Provider for Ollama models."""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:11434"
    
    def generate_response(self, messages: List[Dict[str, str]], system_prompt: str = "") -> str:
        """Generate response using Ollama."""
        try:
            # Convert messages to Ollama format
            ollama_messages = []
            
            if system_prompt:
                ollama_messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            for msg in messages:
                ollama_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Make request to Ollama API
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.config.model,
                    "messages": ollama_messages,
                    "stream": False,
                    "options": {
                        "temperature": self.config.temperature,
                        "num_predict": self.config.max_tokens
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("message", {}).get("content", "No response content")
            else:
                return f"Ollama API error: {response.status_code} - {response.text}"
                
        except requests.exceptions.RequestException as e:
            return f"Error connecting to Ollama: {str(e)}"
        except Exception as e:
            return f"Error generating Ollama response: {str(e)}"
    
    def is_available(self) -> bool:
        """Check if Ollama is available."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False

class VLLMProvider(BaseLLMProvider):
    """Provider for vLLM models."""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:8000"
    
    def generate_response(self, messages: List[Dict[str, str]], system_prompt: str = "") -> str:
        """Generate response using vLLM."""
        try:
            # Convert messages to OpenAI-compatible format (vLLM uses OpenAI API format)
            vllm_messages = []
            
            if system_prompt:
                vllm_messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            for msg in messages:
                vllm_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Make request to vLLM API (OpenAI-compatible)
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "model": self.config.model,
                    "messages": vllm_messages,
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                choices = result.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "No response content")
                return "No response choices returned"
            else:
                return f"vLLM API error: {response.status_code} - {response.text}"
                
        except requests.exceptions.RequestException as e:
            return f"Error connecting to vLLM: {str(e)}"
        except Exception as e:
            return f"Error generating vLLM response: {str(e)}"
    
    def is_available(self) -> bool:
        """Check if vLLM is available."""
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=5)
            return response.status_code == 200
        except:
            return False

class LLMProviderFactory:
    """Factory for creating LLM providers."""
    
    @staticmethod
    def create_provider(config: LLMConfig) -> BaseLLMProvider:
        """Create a provider based on the configuration."""
        if config.provider == LLMProvider.ANTHROPIC:
            return AnthropicProvider(config)
        elif config.provider == LLMProvider.OLLAMA:
            return OllamaProvider(config)
        elif config.provider == LLMProvider.VLLM:
            return VLLMProvider(config)
        else:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")

class LLMManager:
    """Manager for handling LLM provider switching and requests."""
    
    def __init__(self):
        from llm_config import llm_config_manager
        self.config_manager = llm_config_manager
        self._current_provider = None
        self._initialize_current_provider()
    
    def _initialize_current_provider(self):
        """Initialize the current provider based on configuration."""
        config = self.config_manager.get_current_config()
        self._current_provider = LLMProviderFactory.create_provider(config)
    
    def generate_response(self, messages: List[Dict[str, str]], system_prompt: str = "") -> str:
        """Generate response using the current LLM provider."""
        if not self._current_provider:
            self._initialize_current_provider()
        
        if not self._current_provider.is_available():
            return f"Error: Current LLM provider ({self._current_provider.config.display_name}) is not available"
        
        return self._current_provider.generate_response(messages, system_prompt)
    
    def switch_provider(self, config_id: str) -> bool:
        """Switch to a different LLM provider."""
        if self.config_manager.set_current_config(config_id):
            self._initialize_current_provider()
            return True
        return False
    
    def get_current_provider_info(self) -> Dict[str, Any]:
        """Get information about the current provider."""
        if not self._current_provider:
            return {}
        
        config = self._current_provider.config
        return {
            'provider': config.provider.value,
            'model': config.model,
            'display_name': config.display_name,
            'size': config.size,
            'is_available': self._current_provider.is_available(),
            'max_tokens': config.max_tokens,
            'temperature': config.temperature
        }
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers."""
        status = {}
        configs = self.config_manager.get_available_configs()
        
        for config_id, config_data in configs.items():
            if config_data['is_active']:
                config = self.config_manager.configs[config_id]
                provider = LLMProviderFactory.create_provider(config)
                status[config_id] = {
                    'display_name': config_data['display_name'],
                    'provider': config_data['provider'],
                    'model': config_data['model'],
                    'size': config_data['size'],
                    'is_available': provider.is_available(),
                    'is_current': config_data['is_current']
                }
        
        return status

# Global instance
llm_manager = LLMManager()