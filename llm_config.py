from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass
import os
import json

class LLMProvider(Enum):
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    VLLM = "vllm"

@dataclass
class LLMConfig:
    provider: LLMProvider
    model: str
    display_name: str
    size: str  # "large" or "small"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.7
    is_default: bool = False
    is_active: bool = True

class LLMConfigManager:
    def __init__(self):
        self.configs: Dict[str, LLMConfig] = {}
        self.current_config_id: Optional[str] = None
        self._initialize_default_configs()
        self._load_user_settings()
        self._auto_configure_providers()
    
    def _initialize_default_configs(self):
        """Initialize default LLM configurations."""
        self.configs = {
            "anthropic_large": LLMConfig(
                provider=LLMProvider.ANTHROPIC,
                model="claude-sonnet-4-20250514",
                display_name="Claude Sonnet 4",
                size="large",
                api_key=os.getenv('ANTHROPIC_API_KEY'),
                max_tokens=4000,
                temperature=0.7,
                is_default=True
            ),
            "anthropic_small": LLMConfig(
                provider=LLMProvider.ANTHROPIC,
                model="claude-3-5-haiku-20241022",
                display_name="Claude 3.5 Haiku",
                size="small",
                api_key=os.getenv('ANTHROPIC_API_KEY'),
                max_tokens=1000,
                temperature=0.7
            ),
            "ollama_large": LLMConfig(
                provider=LLMProvider.OLLAMA,
                model="gpt-oss:latest",
                display_name="GPT OSS",
                size="large",
                base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
                max_tokens=2000,
                temperature=0.7,
                is_active=True  # Enable if Ollama is available
            ),
            "ollama_small": LLMConfig(
                provider=LLMProvider.OLLAMA,
                model="qwen3:0.6b",
                display_name="Qwen 3 0.6B",
                size="small",
                base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
                max_tokens=1000,
                temperature=0.7,
                is_active=True  # Enable if Ollama is available
            ),
            "vllm_default": LLMConfig(
                provider=LLMProvider.VLLM,
                model="default",
                display_name="vLLM Model",
                size="large",
                base_url=os.getenv('VLLM_BASE_URL', 'http://localhost:8000'),
                max_tokens=2000,
                temperature=0.7,
                is_active=False  # Disabled by default, user needs to enable
            )
        }
        
        # Set default current config
        self.current_config_id = "anthropic_large"
        
    
    def _load_user_settings(self):
        """Load user settings from file."""
        settings_file = 'llm_settings.json'
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    
                # Update configs with user settings
                for config_id, config_data in settings.get('configs', {}).items():
                    if config_id in self.configs:
                        config = self.configs[config_id]
                        config.is_active = config_data.get('is_active', config.is_active)
                        config.max_tokens = config_data.get('max_tokens', config.max_tokens)
                        config.temperature = config_data.get('temperature', config.temperature)
                        if config_data.get('api_key'):
                            config.api_key = config_data['api_key']
                        if config_data.get('base_url'):
                            config.base_url = config_data['base_url']
                
                # Set current config
                self.current_config_id = settings.get('current_config_id', self.current_config_id)
                
            except Exception as e:
                print(f"Error loading LLM settings: {e}")
    
    def save_user_settings(self):
        """Save user settings to file."""
        settings = {
            'current_config_id': self.current_config_id,
            'configs': {}
        }
        
        for config_id, config in self.configs.items():
            settings['configs'][config_id] = {
                'is_active': config.is_active,
                'max_tokens': config.max_tokens,
                'temperature': config.temperature,
                'api_key': config.api_key,
                'base_url': config.base_url
            }
        
        try:
            with open('llm_settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Error saving LLM settings: {e}")
    
    def get_current_config(self) -> LLMConfig:
        """Get the currently selected LLM configuration."""
        if self.current_config_id and self.current_config_id in self.configs:
            return self.configs[self.current_config_id]
        
        # Fallback to first active config or first config
        for config in self.configs.values():
            if config.is_active:
                self.current_config_id = next(k for k, v in self.configs.items() if v == config)
                return config
        
        # Last resort - return first config
        first_config_id = next(iter(self.configs.keys()))
        self.current_config_id = first_config_id
        return self.configs[first_config_id]
    
    def set_current_config(self, config_id: str) -> bool:
        """Set the current LLM configuration."""
        if config_id in self.configs and self.configs[config_id].is_active:
            self.current_config_id = config_id
            self.save_user_settings()
            return True
        return False
    
    def get_available_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all available LLM configurations."""
        result = {}
        for config_id, config in self.configs.items():
            result[config_id] = {
                'id': config_id,
                'provider': config.provider.value,
                'model': config.model,
                'display_name': config.display_name,
                'size': config.size,
                'max_tokens': config.max_tokens,
                'temperature': config.temperature,
                'is_active': config.is_active,
                'is_current': config_id == self.current_config_id,
                'has_api_key': bool(config.api_key),
                'base_url': config.base_url
            }
        return result
    
    def update_config(self, config_id: str, updates: Dict[str, Any]) -> bool:
        """Update a specific LLM configuration."""
        if config_id not in self.configs:
            return False
        
        config = self.configs[config_id]
        
        if 'is_active' in updates:
            config.is_active = updates['is_active']
        if 'max_tokens' in updates:
            config.max_tokens = int(updates['max_tokens'])
        if 'temperature' in updates:
            config.temperature = float(updates['temperature'])
        if 'api_key' in updates:
            config.api_key = updates['api_key']
        if 'base_url' in updates:
            config.base_url = updates['base_url']
        
        self.save_user_settings()
        return True
    
    def get_provider_configs(self, provider: LLMProvider) -> List[LLMConfig]:
        """Get all configurations for a specific provider."""
        return [config for config in self.configs.values() if config.provider == provider]
    
    def is_provider_available(self, provider: LLMProvider) -> bool:
        """Check if a provider has at least one active configuration."""
        provider_configs = self.get_provider_configs(provider)
        return any(config.is_active and config.api_key for config in provider_configs)
    
    def _auto_configure_providers(self):
        """Auto-detect and configure available providers."""
        # Check Ollama availability
        try:
            import requests
            response = requests.get('http://localhost:11434/api/tags', timeout=2)
            if response.status_code == 200:
                # Ollama is available, enable configs
                self.configs["ollama_large"].is_active = True
                self.configs["ollama_small"].is_active = True
                print("Ollama detected and enabled")
            else:
                # Ollama not available, disable configs
                self.configs["ollama_large"].is_active = False
                self.configs["ollama_small"].is_active = False
        except Exception as e:
            # Ollama not available, disable configs
            self.configs["ollama_large"].is_active = False
            self.configs["ollama_small"].is_active = False
        
        # Check vLLM availability
        try:
            import requests
            vllm_url = os.getenv('VLLM_BASE_URL', 'http://localhost:8000')
            response = requests.get(f'{vllm_url}/v1/models', timeout=2)
            if response.status_code == 200:
                self.configs["vllm_default"].is_active = True
                print("vLLM detected and enabled")
            else:
                self.configs["vllm_default"].is_active = False
        except Exception as e:
            self.configs["vllm_default"].is_active = False

# Global instance
llm_config_manager = LLMConfigManager()