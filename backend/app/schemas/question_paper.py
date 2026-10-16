from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.models.question_paper import QuestionPaperStatus
from app.schemas.common import ORMModel


class ParsedQuestion(ORMModel):
    model_config = ConfigDict(extra="forbid")
    question_number: str = Field(min_length=1, max_length=100)
    question_text: str = Field(min_length=1)
    maximum_marks: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    parent_question_number: str | None = Field(default=None, max_length=100)
    sequence_order: int = Field(ge=0)
    confidence: float = Field(ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)
    model_answer: str | None = None
    key_concepts: str | None = None
    acceptable_alternatives: str | None = None
    reference_solution: str | None = None
    marking_notes: str | None = None
    rubric_criteria: list["ParsedRubricCriterion"] = Field(default_factory=list)

    @field_validator("question_number", "question_text")
    @classmethod
    def strip_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("model_answer", "key_concepts", "acceptable_alternatives", "reference_solution", "marking_notes")
    @classmethod
    def blank_optional_text_is_null(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ParsedRubricCriterion(ORMModel):
    model_config = ConfigDict(extra="forbid")
    criterion: str = Field(min_length=1, max_length=255)
    maximum_marks: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    description: str | None = None

    @field_validator("criterion")
    @classmethod
    def strip_criterion(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("description")
    @classmethod
    def blank_description_is_null(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ParsedSection(ORMModel):
    model_config = ConfigDict(extra="forbid")
    section_label: str | None = Field(default=None, max_length=200)
    instructions: str | None = None
    questions: list[ParsedQuestion] = Field(default_factory=list)


class QuestionPaperParseResult(ORMModel):
    model_config = ConfigDict(extra="forbid")
    exam_title: str | None = Field(default=None, max_length=255)
    subject: str | None = Field(default=None, max_length=200)
    sections: list[ParsedSection] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_questions(self) -> "QuestionPaperParseResult":
        if not any(section.questions for section in self.sections):
            raise ValueError("No questions detected")
        return self


class QuestionPaperRead(ORMModel):
    id: UUID
    exam_id: UUID
    original_filename: str
    stored_filename: str
    mime_type: str
    file_size: int
    status: QuestionPaperStatus
    uploaded_at: datetime
    parsed_at: datetime | None
    parsing_error: str | None
    parser_model: str | None
    parser_provider: str | None
    parser_text_model: str | None
    parser_vision_model: str | None
    prompt_version: str | None
    parse_result: QuestionPaperParseResult | None


class QuestionPaperImportRequest(ORMModel):
    questions: list[ParsedQuestion] = Field(min_length=1)


class QuestionPaperImportResult(ORMModel):
    imported: list[UUID]
    skipped_conflicts: list[str]
