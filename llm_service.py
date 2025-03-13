import json
import re
import requests
import ollama
import random
from typing import Dict, List, Any, Optional
from datetime import datetime

from config import Config

class LLMService:
    def __init__(self):
        self.config = Config()

    def usePrompt(self, words: List[str], additional_prompt: Optional[str] = None) -> str:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        random_seed = random.randint(1, 1000)
        
        prompt = (
            f"Antworte nur auf deutsch. Baue aus diesen Wörtern einen Satz mit maximal 10 Wörtern: {', '.join(words)}. Es können noch wörter bei den zusätzlichen Anweisungen hinzukommen aber sonst benutze KEINE weiteren Wörter außer den gegebenen. "
            "Die benutzten Wörter können sich auch nur so anhören wie die gegebenen Wörter. (so etwas wie weil und teil hört sich nicht gleich an und darf deswegen nicht einfach getauscht werden!)"
            "Die Sätze/Wortzusammensetzungen sollen lustig, unhinged, eventuell beleidigend und kurz sein und nicht einfach nur zufällig die ersten paar Wörter aus der Liste sein. "
        )
        
        if additional_prompt:
            prompt += f"\nZusätzliche Anweisungen: {additional_prompt}\n"
            
        prompt += (
            f"Aktueller Zeitpunkt: {current_time}. "
            f"Zufälliger Seed für Variation: {random_seed}. "
            "WICHTIG: Deine Antwort MUSS ein valides JSON-Objekt sein, ohne Erklärungen drumherum. "
            "In sentence schreibe den generierten Satz und in used_words die benutzten Wörter des generierten Satzes(wichtig vergiss nicht auch Konjunktionswörter oder ähnliches zu markieren):"
            "{"
            '  "sentence": "<der generierte Satz>",'
            '  "used_words": ["<Wort1>", "<Wort2>", ...]'
            "}"
        )
        return prompt

    
    def generate_sentence(self, words: list, additional_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Generate a sentence using the configured LLM provider"""
        provider = self.config.get_current_provider()
        
        if not words or len(words) == 0:
            return {"sentence": "Keine Wörter gefunden", "used_words": []}
        
        if provider == "openrouter":
            return self._generate_with_openrouter(words, additional_prompt)
        elif provider == "ollama":
            return self._generate_with_ollama(words, additional_prompt)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def _generate_with_openrouter(self, words: list, additional_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Generate text using OpenRouter API"""
        config = self.config.get_provider_config()
        api_key = config.get("api_key", "")
        model = config.get("model", "qwen/qwq-32b:free")
        
        if not api_key:
            return {"sentence": "API-Schlüssel fehlt", "used_words": words}
        
        prompt = self.usePrompt(words, additional_prompt)
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": config.get("temperature", 0.7)
        }
        
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            response_data = response.json()
            print(response_data)
            raw_response = response_data["choices"][0]["message"]["content"]
            print(f"Raw OpenRouter response: {raw_response}")
            return self._parse_llm_response(raw_response, words)
        except Exception as e:
            print(f"Error with OpenRouter API: {str(e)}")
            return {"sentence": f"API-Fehler: {str(e)}", "used_words": words}
    
    def _generate_with_ollama(self, words: list, additional_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Generate text using local Ollama instance"""
        config = self.config.get_provider_config()
        model = config.get("model", "thirdeyeai/DeepSeek-R1-Distill-Qwen-7B-uncensored")
        
        prompt = self.usePrompt(words, additional_prompt)
        
        try:
               
            response = ollama.generate(
                model=model,
                prompt=prompt,
                options={
                    "temperature": config.get("temperature", 0.7),
                    "top_p": config.get("top_p", 0.9)
                }
            )
            
            raw_response = response["response"]
            print(f"Raw Ollama response: {raw_response}")
            return self._parse_llm_response(raw_response, words)
        except Exception as e:
            print(f"Error with Ollama: {str(e)}")
            return {"sentence": f"Ollama-Fehler: {str(e)}", "used_words": words}
    
    def _parse_llm_response(self, raw_response: str, words: list) -> Dict[str, Any]:
        """Parse the LLM response to extract the generated sentence and used words"""
        try:
            # First attempt: direct JSON parsing
            try:
                result = json.loads(raw_response.strip())
                if "sentence" in result and "used_words" in result:
                    return result
            except json.JSONDecodeError:
                pass
            
            # Second attempt: find JSON-like content using regex
            json_match = re.search(r'({[\s\S]*?})', raw_response)
            if json_match:
                json_str = json_match.group(1)
                try:
                    result = json.loads(json_str)
                    if "sentence" in result and "used_words" in result:
                        return result
                except json.JSONDecodeError:
                    pass
            
            # Third attempt: construct JSON from parts
            sentence_match = re.search(r'"sentence"\s*:\s*"([^"]+)"', raw_response)
            words_match = re.search(r'"used_words"\s*:\s*\[(.*?)\]', raw_response, re.DOTALL)
            
            if sentence_match and words_match:
                sentence = sentence_match.group(1)
                words_text = words_match.group(1)
                used_words = [w.strip(' "\'') for w in re.findall(r'"([^"]+)"', words_text)]
                
                return {
                    "sentence": sentence,
                    "used_words": used_words
                }
            
            # If all parsing attempts failed, fallback to simple response
            fallback_sentence = " ".join(words[:5]) + "..."
            return {
                "sentence": fallback_sentence,
                "used_words": words
            }
            
        except Exception as e:
            print(f"Error parsing LLM response: {str(e)}")
            # Fallback response
            return {
                "sentence": f"Lustiger Satz mit: {', '.join(words[:3])}...",
                "used_words": words
            }
