from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://answer_evaluator:answer_evaluator@localhost:5432/answer_evaluator"
    secret_key: str = "development-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    cookie_secure: bool = False
    frontend_origin: str = "http://localhost:3000"
    cookie_name: str = "aae_session"
    storage_root: Path = Path(__file__).resolve().parents[3] / "storage"
    max_upload_size_bytes: int = 10 * 1024 * 1024
    # Roster imports are parsed in memory and should remain deliberately small.
    max_student_import_size_bytes: int = 2 * 1024 * 1024
    openai_api_key: str | None = None
    question_parser_model: str = "gpt-4.1-mini"
    ai_provider: str = "auto"
    ollama_base_url: str = "http://localhost:11434"
    ollama_text_model: str = "gemma3:4b"
    ollama_vision_model: str = "gemma3:4b"
    ollama_mapping_model: str | None = "gemma3:4b"
    ollama_evaluation_model: str | None = "gemma3:4b"
    ai_mapping_enabled: bool = True
    ai_mapping_confidence_threshold: float = 0.80
    # Omit by default: forcing a larger context can exhaust local unified memory.
    ollama_num_ctx: int | None = None
    ollama_timeout_seconds: int = 180
    # Local-only troubleshooting switch. Never enable this in production because model output can contain document text.
    question_parser_debug_output: bool = False

    @field_validator("ollama_num_ctx", mode="before")
    @classmethod
    def blank_context_is_unset(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("ollama_mapping_model", "ollama_evaluation_model", mode="before")
    @classmethod
    def blank_specialized_model_is_unset(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
