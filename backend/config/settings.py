"""
Configuration management for the AI Research Teaching Agent
"""
import json
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # API Keys (Using Mistral only)
    mistral_api_key: str = ""
    openrouter_api_key: str = ""
    tavily_api_key: str = ""
    elevenlabs_api_key: str = "sk_f6cae34774420dcc91c0db416735fdb73617fab765aebf0b"
    
    # TTS Configuration
    tts_voice_id: str = "MF3mGyEYCl7XYWbV9V6O"  # Elli - soft female voice (free tier)
    tts_model: str = "eleven_multilingual_v2"  # Most natural-sounding model
    
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    
    # Vector DB Configuration
    vector_db_type: str = "faiss"
    vector_db_path: str = "./data/vector_db"
    
    # Model Configuration (OpenRouter Mistral Small primary, Mistral Medium backup)
    openrouter_model: str = "mistralai/mistral-small-3.1-24b-instruct"  # Primary via OpenRouter
    mistral_model: str = "mistral-medium-latest"  # Backup via Mistral API
    embedding_model: str = "text-embedding-3-small"
    
    # System Configuration
    max_search_results: int = 5
    max_images_per_response: int = 6
    cache_ttl: int = 3600
    search_cache_ttl: int = 1800          # Tavily result cache TTL (seconds)
    search_cache_max_size: int = 256      # Max cached search entries
    max_retries: int = 3
    timeout_seconds: int = 30
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
            return [s.strip() for s in v.split(",") if s.strip()]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Export settings instance
settings = get_settings()
