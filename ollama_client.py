"""
Ollama client for local LLM inference.

This module provides a client for interacting with Ollama API to generate
text using the Llama 3.2-3B Instruct model. It serves as the primary backend
for conversational AI when configured, with fallback to Gemini API if needed.
"""

import os
import logging
import time
from typing import Optional, Dict, Any, Tuple
import requests

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for Ollama API to run local LLM inference."""
    
    def __init__(self, base_url: Optional[str] = None, model: str = "llama3.2:3b"):
        """
        Initialize Ollama client.
        
        Args:
            base_url: Base URL for Ollama service (default: from OLLAMA_BASE_URL env var)
            model: Model name to use (default: llama3.2:3b)
        """
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model
        self.generate_url = f"{self.base_url}/api/generate"
        self.tags_url = f"{self.base_url}/api/tags"
        
        # Stats tracking
        self.total_calls = 0
        self.total_errors = 0
        self.total_latency_ms = 0.0
        self.total_tokens_in = 0
        self.total_tokens_out = 0
        
        logger.info(f"🦙 Ollama client initialized: {self.base_url}, model: {self.model}")
    
    def is_available(self) -> bool:
        """
        Check if Ollama service is available.
        
        Returns:
            True if service is reachable and model is available
        """
        try:
            response = requests.get(self.tags_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                # Check if our model is in the list
                for model in models:
                    if model.get("name", "").startswith(self.model.split(":")[0]):
                        logger.debug(f"✅ Model {self.model} is available")
                        return True
                logger.warning(f"⚠️ Model {self.model} not found in Ollama")
                return False
            return False
        except Exception as e:
            logger.debug(f"❌ Ollama not available: {e}")
            return False
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 512,
        stream: bool = False
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Generate text using Ollama API.
        
        Args:
            prompt: The prompt text
            temperature: Sampling temperature (0.0-1.0)
            top_p: Nucleus sampling parameter
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response (not implemented)
        
        Returns:
            Tuple of (generated_text, metadata_dict)
            metadata includes: latency_ms, tokens_in, tokens_out, success
        """
        self.total_calls += 1
        start_time = time.time()
        
        metadata = {
            "success": False,
            "latency_ms": 0.0,
            "tokens_in": 0,
            "tokens_out": 0,
            "model": self.model,
            "error": None
        }
        
        try:
            # Prepare request payload
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,  # Always use non-streaming for simplicity
                "options": {
                    "temperature": temperature,
                    "top_p": top_p,
                    "num_predict": max_tokens
                }
            }
            
            logger.info(f"🦙 Calling Ollama with prompt length: {len(prompt)} chars")
            logger.debug(f"Request payload: temp={temperature}, top_p={top_p}, max_tokens={max_tokens}")
            
            # Make the API call
            response = requests.post(
                self.generate_url,
                json=payload,
                timeout=120  # 2 minutes timeout for generation
            )
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            metadata["latency_ms"] = latency_ms
            self.total_latency_ms += latency_ms
            
            # Check response
            if response.status_code != 200:
                error_msg = f"Ollama API error: {response.status_code} - {response.text}"
                logger.error(f"❌ {error_msg}")
                metadata["error"] = error_msg
                self.total_errors += 1
                return None, metadata
            
            # Parse response
            data = response.json()
            generated_text = data.get("response", "")
            
            # Extract token counts if available
            if "prompt_eval_count" in data:
                metadata["tokens_in"] = data["prompt_eval_count"]
                self.total_tokens_in += metadata["tokens_in"]
            
            if "eval_count" in data:
                metadata["tokens_out"] = data["eval_count"]
                self.total_tokens_out += metadata["tokens_out"]
            
            # Log duration info if available
            if "total_duration" in data:
                total_duration_ms = data["total_duration"] / 1_000_000  # ns to ms
                logger.debug(f"Ollama total duration: {total_duration_ms:.0f}ms")
            
            metadata["success"] = True
            
            logger.info(
                f"✅ Ollama response: {len(generated_text)} chars, "
                f"{metadata['latency_ms']:.0f}ms, "
                f"{metadata['tokens_in']} tokens in, "
                f"{metadata['tokens_out']} tokens out"
            )
            
            return generated_text.strip(), metadata
            
        except requests.exceptions.Timeout:
            error_msg = "Ollama request timeout"
            logger.error(f"⏱️ {error_msg}")
            metadata["error"] = error_msg
            metadata["latency_ms"] = (time.time() - start_time) * 1000
            self.total_errors += 1
            return None, metadata
            
        except Exception as e:
            error_msg = f"Ollama error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            metadata["error"] = error_msg
            metadata["latency_ms"] = (time.time() - start_time) * 1000
            self.total_errors += 1
            return None, metadata
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about Ollama usage.
        
        Returns:
            Dictionary with usage statistics
        """
        avg_latency = self.total_latency_ms / max(1, self.total_calls)
        error_rate = self.total_errors / max(1, self.total_calls)
        
        return {
            "total_calls": self.total_calls,
            "total_errors": self.total_errors,
            "error_rate": error_rate,
            "avg_latency_ms": avg_latency,
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "model": self.model,
            "base_url": self.base_url
        }
    
    def __repr__(self) -> str:
        return f"OllamaClient(base_url={self.base_url}, model={self.model}, calls={self.total_calls})"


# Global instance (lazy-initialized)
_ollama_client: Optional[OllamaClient] = None


def get_ollama_client() -> Optional[OllamaClient]:
    """
    Get or create the global Ollama client instance.
    
    Returns:
        OllamaClient instance if available, None otherwise
    """
    global _ollama_client
    
    if _ollama_client is None:
        try:
            _ollama_client = OllamaClient()
            if not _ollama_client.is_available():
                logger.warning("⚠️ Ollama service not available, client disabled")
                _ollama_client = None
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize Ollama client: {e}")
            _ollama_client = None
    
    return _ollama_client
