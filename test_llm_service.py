import sys
import os
import json
from pathlib import Path

# Add the freezer-fun module path to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "freezer-fun"))

from config import Config
from llm_service import LLMService

def setup_test_config():
    """Create a temporary test config if not exists"""
    config_path = Path("config.json")
    
    if not config_path.exists():
        test_config = {
            "llm_provider": "ollama",  # Start with ollama as default
            "openrouter": {
                "api_key": os.environ.get("OPENROUTER_API_KEY", ""),
                "model": "qwen/qwq-32b:free",
                "temperature": 0.7
            },
            "ollama": {
                "host": "http://localhost:11434",
                "model": "thirdeyeai/DeepSeek-R1-Distill-Qwen-7B-uncensored",
                "temperature": 0.7,
                "top_p": 0.9
            }
        }
        
        with open(config_path, 'w') as f:
            json.dump(test_config, f, indent=2)
        
        print(f"Created test config at {config_path}")
    
    # Set the environment variable to use the test config
    os.environ["CONFIG_PATH"] = str(config_path)

def test_ollama_provider():
    """Test the Ollama provider"""
    print("\n=== Testing Ollama Provider ===")
    
    # Override the config to use Ollama
    config = Config()
    config.config["llm_provider"] = "ollama"
    
    llm = LLMService()
    test_words = ["Katze", "Mond", "Pizza", "tanzen"]
    
    print(f"Input words: {test_words}")
    try:
        result = llm.generate_sentence(test_words)
        print("Success! Result:")
        print(f"Sentence: {result['sentence']}")
        print(f"Used words: {result['used_words']}")
        return True
    except Exception as e:
        print(f"Error testing Ollama: {str(e)}")
        return False

def test_openrouter_provider():
    """Test the OpenRouter provider"""
    print("\n=== Testing OpenRouter Provider ===")
    
    # Override the config to use OpenRouter
    config = Config()
    config.config["llm_provider"] = "openrouter"
    
    # Check if API key is set
    api_key = config.config["openrouter"].get("api_key", "")
    if not api_key:
        print("Warning: OpenRouter API key not set. Set OPENROUTER_API_KEY environment variable.")
        return False
    
    llm = LLMService()
    test_words = ["Roboter", "Schokolade", "schwimmen", "Banane"]
    
    print(f"Input words: {test_words}")
    try:
        result = llm.generate_sentence(test_words)
        print("Success! Result:")
        print(f"Sentence: {result['sentence']}")
        print(f"Used words: {result['used_words']}")
        return True
    except Exception as e:
        print(f"Error testing OpenRouter: {str(e)}")
        return False

if __name__ == "__main__":
    # Setup test configuration
    setup_test_config()
    
    # Test both providers
    ollama_success = test_ollama_provider()
    openrouter_success = test_openrouter_provider()
    
    # Summary
    print("\n=== Test Summary ===")
    print(f"Ollama Provider: {'✅ Success' if ollama_success else '❌ Failed'}")
    print(f"OpenRouter Provider: {'✅ Success' if openrouter_success else '❌ Failed'}")
    
    if ollama_success and openrouter_success:
        print("\n✅ All providers working correctly!")
    else:
        print("\n⚠️ Some tests failed. See logs above.")
