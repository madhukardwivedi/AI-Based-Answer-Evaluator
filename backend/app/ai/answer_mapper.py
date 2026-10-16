import json

from app.ai.structured_provider import StructuredAIProvider
from app.core.config import get_settings
from app.schemas.evaluation import AIAnswerMappingResult, AIExtractedAnswer


class AnswerMapper:
    def __init__(self, provider: StructuredAIProvider | None = None) -> None:
        self.provider = provider or StructuredAIProvider()
        settings = get_settings()
        self.provider.text_model = settings.ollama_mapping_model or settings.ollama_text_model

    def map(self, answers: list[AIExtractedAnswer], questions: list[dict[str, str]]) -> AIAnswerMappingResult:
        prompt = """Map only the supplied unresolved student-answer segments to the supplied exam questions. Do not grade, rewrite, or solve anything. Return one mapping for every segment_index. Choose a question only when the answer meaning clearly corresponds to exactly one candidate; otherwise return question_number null and low confidence. Preserve the candidate question number exactly."""
        payload = {"segments": [{"segment_index": index, "answer_text": answer.answer_text} for index, answer in enumerate(answers)], "questions": questions}
        result = self.provider.generate(prompt=prompt + "\n\n" + json.dumps(payload), schema_model=AIAnswerMappingResult)
        return result if isinstance(result, AIAnswerMappingResult) else AIAnswerMappingResult.model_validate(result)
