from dataclasses import dataclass
import logging

from app.ai.prompts.answer_extractor_v1 import ANSWER_EXTRACTOR_PROMPT
from app.ai.structured_provider import StructuredAIProvider
from app.schemas.evaluation import AIExtractionResult

logger = logging.getLogger(__name__)


@dataclass
class ExtractionDocument:
    images: list[bytes]
    page_numbers: list[int]


class AnswerExtractor:
    def __init__(self, provider: StructuredAIProvider | None = None) -> None:
        self.provider = provider or StructuredAIProvider()

    def extract(self, document: ExtractionDocument, expected_question_labels: list[str] | None = None) -> AIExtractionResult:
        # Keep transcription isolated from academic solution context. The
        # provider receives only the page image and the strict OCR/HTR prompt;
        # question text, model answers, rubrics, reference solutions, marking
        # notes, and key concepts are intentionally excluded from this call.
        answers = []
        for image, page_number in zip(document.images, document.page_numbers, strict=True):
            prompt = ANSWER_EXTRACTOR_PROMPT + "\n\nCurrent page number: " + str(page_number) + "\nRead question labels only from the page image. Do not use labels from examples as answers."
            result = self.provider.generate(prompt=prompt, schema_model=AIExtractionResult, images=[image])
            parsed = result if isinstance(result, AIExtractionResult) else AIExtractionResult.model_validate(result)
            for answer in parsed.answers:
                answer.page_numbers = [page_number]
                answers.append(answer)
            logger.info("EXTRACTION_PAGE page=%s segments=%s", page_number, len(parsed.answers))
        return AIExtractionResult(answers=answers)
