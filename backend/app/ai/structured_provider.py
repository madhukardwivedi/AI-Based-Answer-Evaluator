import base64
import json
from typing import Any

import httpx
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from app.ai.question_parser import _json_object_from_model_output, strict_schema
from app.core.config import get_settings


class AIProviderError(RuntimeError):
    pass


class StructuredAIProvider:
    """Small backend-only provider bridge; both providers return a Pydantic contract."""
    def __init__(self) -> None:
        settings = get_settings()
        configured = settings.ai_provider
        self.provider = ("openai" if (settings.openai_api_key or "").strip() else "ollama") if configured == "auto" else configured
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.text_model = settings.ollama_text_model
        self.vision_model = settings.ollama_vision_model
        self.openai_model = settings.question_parser_model
        if self.provider not in {"openai", "ollama"}:
            raise AIProviderError("AI_PROVIDER must be auto, openai, or ollama")

    def generate(self, *, prompt: str, schema_model: type[BaseModel], images: list[bytes] | None = None) -> BaseModel:
        if self.provider == "openai":
            return self._openai(prompt, schema_model, images or [])
        return self._ollama(prompt, schema_model, images or [])

    @property
    def model(self) -> str:
        return self.openai_model if self.provider == "openai" else self.text_model

    def _openai(self, prompt: str, schema_model: type[BaseModel], images: list[bytes]) -> BaseModel:
        settings = get_settings()
        content: list[dict[str, str]] = [{"type": "input_text", "text": prompt}]
        content.extend({"type": "input_image", "image_url": "data:image/png;base64," + base64.b64encode(image).decode("ascii"), "detail": "high"} for image in images)
        try:
            response = OpenAI(api_key=settings.openai_api_key).responses.create(model=self.openai_model, input=[{"role": "user", "content": content}], text={"format": {"type": "json_schema", "name": "evaluation_result", "schema": strict_schema(schema_model.model_json_schema()), "strict": True}}, store=False)
            return schema_model.model_validate_json(response.output_text)
        except (ValidationError, ValueError) as error:
            raise AIProviderError("OpenAI returned an invalid structured result") from error
        except Exception as error:
            raise AIProviderError("OpenAI request failed") from error

    def _ollama(self, prompt: str, schema_model: type[BaseModel], images: list[bytes]) -> BaseModel:
        model = self.vision_model if images else self.text_model
        payload: dict[str, Any] = {"model": model, "prompt": prompt, "stream": False, "format": schema_model.model_json_schema(), "options": {"temperature": 0}}
        if images:
            payload["images"] = [base64.b64encode(image).decode("ascii") for image in images]
        try:
            response = httpx.post(self.base_url + "/api/generate", json=payload, timeout=180)
            response.raise_for_status()
            raw = response.json().get("response")
            if not isinstance(raw, str): raise AIProviderError("Ollama returned no structured response")
            return schema_model.model_validate(_json_object_from_model_output(raw))
        except AIProviderError: raise
        except httpx.ConnectError as error: raise AIProviderError("Ollama is unavailable. Start it and verify http://localhost:11434.") from error
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404: raise AIProviderError(f"Ollama model '{model}' is unavailable. Run: ollama pull {model}") from error
            raise AIProviderError("Ollama request failed") from error
        except (ValidationError, ValueError, json.JSONDecodeError) as error: raise AIProviderError("Ollama returned an invalid structured result") from error
