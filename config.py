import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

class Config:
    def __init__(self):
        self.config_file = Path(os.environ.get("CONFIG_PATH", "config.json"))
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment variables"""
        default_config = {
            "llm_provider": "ollama",  # "openrouter" or "ollama"
            "openrouter": {
                "api_key": os.environ.get("OPENROUTER_API_KEY", ""),
                "model": "qwen/qwq-32b:free",
                "temperature": 0.7,
                "max_tokens": 300
            },
            "ollama": {
                "model": "thirdeyeai/DeepSeek-R1-Distill-Qwen-7B-uncensored",
                "temperature": 0.7,
                "max_tokens": 300,
                "top_p": 0.9
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return {**default_config, **json.load(f)}
            except Exception as e:
                print(f"Error loading config file: {e}")
                return default_config
        else:
            return default_config
    
    def save_config(self) -> None:
        """Save current configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get_provider_config(self) -> Dict[str, Any]:
        """Get the configuration for the active provider"""
        provider = self.config.get("llm_provider", "ollama")
        return self.config.get(provider, {})
    
    def get_current_provider(self) -> str:
        """Get the current LLM provider name"""
        return self.config.get("llm_provider", "ollama")
    
    def set_provider(self, provider: str) -> None:
        """Set the LLM provider"""
        if provider not in ["openrouter", "ollama"]:
            raise ValueError(f"Unsupported provider: {provider}")
        self.config["llm_provider"] = provider