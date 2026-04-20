"""
Configuration management for the AI Research Teaching Agent
"""
import json
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from pydantic import field_validator
from typing import List
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    """Application settings"""
    
    # API Keys (Mistral only)
    mistral_api_key: str = ""
    openrouter_api_key: str = ""  # Deprecated: ignored
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
    
    # Model Configuration (Mistral only)
    openrouter_model: str = "mistralai/mistral-small-3.1-24b-instruct"  # Deprecated: unused
    mistral_model: str = "mistral-medium-latest"
    embedding_model: str = "text-embedding-3-small"
    
    # System Configuration
    max_search_results: int = 3
    max_search_queries: int = 1
    max_images_per_response: int = 4
    cache_ttl: int = 3600
    search_cache_ttl: int = 1800          # Tavily result cache TTL (seconds)
    search_cache_max_size: int = 256      # Max cached search entries
    max_retries: int = 3
    timeout_seconds: int = 15
    content_extraction_timeout_seconds: int = 30
    extraction_max_sources: int = 3

    # PeCAR / synthesis latency controls
    pecar_enabled: bool = True
    pecar_timeout_seconds: int = 18
    pecar_use_retrieval: bool = False
    pecar_context_chars: int = 5000
    pecar_max_paths: int = 2
    pecar_max_steps: int = 6
    pecar_research_complexity_threshold: float = 0.68
    pecar_general_complexity_threshold: float = 0.50
    pecar_simple_question_chars: int = 70
    synthesis_timeout_seconds: int = 18
    
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

    @field_validator("max_search_results", mode="before")
    @classmethod
    def clamp_max_search_results(cls, v):
        try:
            val = int(v)
        except (TypeError, ValueError):
            return 5
        # Keep search fan-out sane for latency and cost.
        return max(1, min(val, 10))

    @field_validator("max_search_queries", mode="before")
    @classmethod
    def clamp_max_search_queries(cls, v):
        try:
            val = int(v)
        except (TypeError, ValueError):
            return 1
        return max(1, min(val, 4))

    @field_validator("openrouter_api_key", mode="before")
    @classmethod
    def disable_openrouter_key(cls, _v):
        # Enforce Mistral-only provider usage even if OPENROUTER_API_KEY is present.
        return ""

    @field_validator("max_images_per_response", mode="before")
    @classmethod
    def clamp_max_images(cls, v):
        try:
            val = int(v)
        except (TypeError, ValueError):
            return 6
        return max(0, min(val, 12))

    @field_validator("timeout_seconds", mode="before")
    @classmethod
    def clamp_timeout(cls, v):
        try:
            val = int(v)
        except (TypeError, ValueError):
            return 30
        return max(5, min(val, 120))

    @field_validator("content_extraction_timeout_seconds", mode="before")
    @classmethod
    def clamp_content_extraction_timeout(cls, v):
        try:
            val = int(v)
        except (TypeError, ValueError):
            return 30
        return max(10, min(val, 120))

    @field_validator("extraction_max_sources", mode="before")
    @classmethod
    def clamp_extraction_max_sources(cls, v):
        try:
            val = int(v)
        except (TypeError, ValueError):
            return 4
        return max(1, min(val, 8))

    @field_validator("pecar_timeout_seconds", mode="before")
    @classmethod
    def clamp_pecar_timeout(cls, v):
        try:
            val = int(v)
        except (TypeError, ValueError):
            return 35
        return max(10, min(val, 90))

    @field_validator("pecar_context_chars", mode="before")
    @classmethod
    def clamp_pecar_context_chars(cls, v):
        try:
            val = int(v)
        except (TypeError, ValueError):
            return 5000
        return max(1000, min(val, 12000))

    @field_validator("pecar_max_paths", mode="before")
    @classmethod
    def clamp_pecar_max_paths(cls, v):
        try:
            val = int(v)
        except (TypeError, ValueError):
            return 2
        return max(1, min(val, 4))

    @field_validator("pecar_max_steps", mode="before")
    @classmethod
    def clamp_pecar_max_steps(cls, v):
        try:
            val = int(v)
        except (TypeError, ValueError):
            return 6
        return max(2, min(val, 10))

    @field_validator("pecar_research_complexity_threshold", mode="before")
    @classmethod
    def clamp_pecar_research_threshold(cls, v):
        try:
            val = float(v)
        except (TypeError, ValueError):
            return 0.68
        return max(0.3, min(val, 0.95))

    @field_validator("pecar_general_complexity_threshold", mode="before")
    @classmethod
    def clamp_pecar_general_threshold(cls, v):
        try:
            val = float(v)
        except (TypeError, ValueError):
            return 0.50
        return max(0.2, min(val, 0.9))

    @field_validator("pecar_simple_question_chars", mode="before")
    @classmethod
    def clamp_pecar_simple_question_chars(cls, v):
        try:
            val = int(v)
        except (TypeError, ValueError):
            return 70
        return max(20, min(val, 300))

    @field_validator("synthesis_timeout_seconds", mode="before")
    @classmethod
    def clamp_synthesis_timeout(cls, v):
        try:
            val = int(v)
        except (TypeError, ValueError):
            return 35
        return max(10, min(val, 120))
    
    model_config = ConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Export settings instance
settings = get_settings()
