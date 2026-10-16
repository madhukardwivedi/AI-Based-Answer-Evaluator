import json
from app.ai.prompts.evaluation_v1 import EVALUATION_PROMPT
from app.ai.structured_provider import StructuredAIProvider
from app.core.config import get_settings
from app.schemas.evaluation import AIEvaluationResult


class AnswerEvaluator:
    def __init__(self, provider: StructuredAIProvider | None = None) -> None:
        self.provider = provider or StructuredAIProvider()
        evaluation_model = get_settings().ollama_evaluation_model
        if evaluation_model:
            self.provider.text_model = evaluation_model

    def evaluate(self, payload: dict[str, object]) -> AIEvaluationResult:
        result = self.provider.generate(prompt=EVALUATION_PROMPT + "\n\nEvaluation material:\n" + json.dumps(payload, default=str), schema_model=AIEvaluationResult)
        return result if isinstance(result, AIEvaluationResult) else AIEvaluationResult.model_validate(result)
