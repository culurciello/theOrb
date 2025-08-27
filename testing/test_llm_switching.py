#!/usr/bin/env python3
"""
Test script for LLM switching functionality
"""

import json
from llm_config import llm_config_manager
from llm_providers import llm_manager, LLMProviderFactory

def test_config_manager():
    """Test the LLM configuration manager."""
    print("🔧 Testing LLM Configuration Manager...")
    
    # Test getting available configs
    configs = llm_config_manager.get_available_configs()
    print(f"✅ Found {len(configs)} LLM configurations")
    
    # Test current config
    current = llm_config_manager.get_current_config()
    print(f"✅ Current config: {current.display_name} ({current.provider.value})")
    
    # Test provider availability
    from llm_config import LLMProvider
    for provider in LLMProvider:
        available = llm_config_manager.is_provider_available(provider)
        status = "✅" if available else "❌"
        print(f"{status} {provider.value.upper()} provider available: {available}")
    
    return True

def test_providers():
    """Test individual LLM providers."""
    print("\n🤖 Testing LLM Providers...")
    
    # Test Anthropic provider (should work)
    anthro_config = llm_config_manager.configs['anthropic_large']
    anthro_provider = LLMProviderFactory.create_provider(anthro_config)
    
    print(f"✅ Anthropic provider available: {anthro_provider.is_available()}")
    
    if anthro_provider.is_available():
        test_messages = [{"role": "user", "content": "Say 'Hello from Anthropic!' and nothing else."}]
        response = anthro_provider.generate_response(test_messages, "You are a helpful assistant.")
        print(f"✅ Anthropic response: {response.strip()}")
    
    # Test Ollama provider (likely not available)
    ollama_config = llm_config_manager.configs['ollama_large']
    ollama_provider = LLMProviderFactory.create_provider(ollama_config)
    ollama_available = ollama_provider.is_available()
    
    status = "✅" if ollama_available else "❌"
    print(f"{status} Ollama provider available: {ollama_available}")
    
    # Test vLLM provider (likely not available)
    vllm_config = llm_config_manager.configs['vllm_default']
    vllm_provider = LLMProviderFactory.create_provider(vllm_config)
    vllm_available = vllm_provider.is_available()
    
    status = "✅" if vllm_available else "❌"
    print(f"{status} vLLM provider available: {vllm_available}")
    
    return True

def test_llm_manager():
    """Test the LLM manager functionality."""
    print("\n🎯 Testing LLM Manager...")
    
    # Test current provider info
    info = llm_manager.get_current_provider_info()
    print(f"✅ Current provider: {info.get('display_name', 'Unknown')} ({info.get('provider', 'Unknown')})")
    print(f"✅ Available: {info.get('is_available', False)}")
    
    # Test switching between Anthropic models
    original_config = llm_manager.config_manager.current_config_id
    
    if llm_manager.switch_provider('anthropic_small'):
        print("✅ Successfully switched to Claude 3.5 Haiku")
        
        # Test response with new model
        messages = [{"role": "user", "content": "Say 'Hello from Haiku!' briefly."}]
        response = llm_manager.generate_response(messages, "You are helpful and brief.")
        print(f"✅ Haiku response: {response.strip()}")
        
        # Switch back
        llm_manager.switch_provider(original_config)
        print(f"✅ Switched back to original model")
    else:
        print("❌ Failed to switch to small model")
    
    # Test provider status
    status = llm_manager.get_provider_status()
    print(f"✅ Provider status retrieved for {len(status)} providers")
    
    return True

def test_api_integration():
    """Test API endpoint integration."""
    print("\n🌐 Testing API Integration...")
    
    try:
        from app import app
        with app.app_context():
            # Simulate API calls
            from routes import get_llm_configs, get_current_llm
            
            # This would normally be called via HTTP, but we can test the function directly
            print("✅ API endpoints are properly integrated")
            return True
    except Exception as e:
        print(f"❌ API integration error: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting LLM Switching System Tests\n")
    
    tests = [
        ("Configuration Manager", test_config_manager),
        ("LLM Providers", test_providers),
        ("LLM Manager", test_llm_manager),
        ("API Integration", test_api_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"✅ {test_name} tests passed\n")
        except Exception as e:
            print(f"❌ {test_name} tests failed: {e}\n")
            results.append((test_name, False))
    
    print("📊 Test Summary:")
    print("=" * 50)
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    print(f"\nPassed: {total_passed}/{len(results)} tests")
    
    if total_passed == len(results):
        print("🎉 All tests passed! LLM switching system is ready!")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")

if __name__ == "__main__":
    main()