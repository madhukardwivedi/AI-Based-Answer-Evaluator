from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import AliasChoices, Field, model_validator

from app.models.evaluation import EvaluationStatus
from app.schemas.common import ORMModel


class AnswerSheetPageRead(ORMModel):
    id: UUID
    answer_sheet_id: UUID
    page_number: int
    image_path: str
    extracted_text: str | None
    extraction_confidence: Decimal | None
    created_at: datetime


class StudentAnswerRead(ORMModel):
    id: UUID
    student_submission_id: UUID
    question_id: UUID | None
    detected_question_number: str | None
    answer_text: str
    raw_text: str | None
    edited_text: str | None
    extraction_status: str
    warnings: list[str]
    page_numbers: list[int]
    extraction_confidence: Decimal | None
    mapping_confidence: Decimal | None
    mapping_status: str
    manually_corrected: bool
    reviewed: bool
    created_at: datetime
    updated_at: datetime


class StudentAnswerUpdate(ORMModel):
    question_id: UUID | None = None
    answer_text: str = Field(min_length=1)
    reviewed: bool = False


class EvaluationCriterionRead(ORMModel):
    id: UUID
    rubric_criterion_id: UUID | None
    criterion_text_snapshot: str
    maximum_marks: Decimal
    awarded_marks: Decimal
    faculty_awarded_marks: Decimal | None
    final_awarded_marks: Decimal
    evidence: str
    status: str
    reason: str


class EvaluationRead(ORMModel):
    id: UUID
    student_answer_id: UUID
    ai_marks: Decimal
    manual_marks: Decimal | None
    final_marks: Decimal
    maximum_marks: Decimal
    confidence: Decimal
    strengths: list[str]
    missing_points: list[str]
    feedback: str
    reasoning: str
    faculty_remarks: str | None
    status: EvaluationStatus
    ai_provider: str | None
    ai_model: str | None
    prompt_version: str | None
    evaluation_method: str
    warnings: list[str]
    criteria: list[EvaluationCriterionRead] = []
    created_at: datetime
    updated_at: datetime


class EvaluationCriterionUpdate(ORMModel):
    criterion_id: UUID
    faculty_awarded_marks: Decimal = Field(ge=0)


class EvaluationUpdate(ORMModel):
    manual_marks: Decimal | None = Field(default=None, ge=0)
    faculty_remarks: str | None = None
    criterion_marks: list[EvaluationCriterionUpdate] = Field(default_factory=list)


class EvaluationResultRow(ORMModel):
    question_number: str
    question_id: UUID | None
    ai_marks: Decimal | None
    faculty_marks: Decimal | None
    final_marks: Decimal | None
    maximum_marks: Decimal
    status: str


class StudentResultRead(ORMModel):
    submission_id: UUID
    student_id: UUID
    student_name: str
    roll_number: str | None
    total_marks: Decimal
    maximum_marks: Decimal
    percentage: Decimal
    status: str
    questions: list[EvaluationResultRow]


class EvaluationFailure(ORMModel):
    student_answer_id: UUID
    question_number: str | None
    detail: str


class SubmissionEvaluationSummary(ORMModel):
    total: int
    evaluated: int
    failed: int
    evaluations: list[EvaluationRead]
    failures: list[EvaluationFailure]


class SubmissionFinalizeRead(ORMModel):
    submission_id: UUID
    evaluation_status: str
    finalized_at: datetime | None


class AIExtractedAnswer(ORMModel):
    # Required in provider output, while still allowing null for a genuine
    # unlabeled continuation segment on a later page.
    detected_question_number: str | None
    answer_text: str = Field(min_length=1)
    page_numbers: list[int] = Field(
        validation_alias=AliasChoices("source_pages", "page_numbers"),
        serialization_alias="source_pages",
    )
    extraction_confidence: Decimal = Field(
        ge=0,
        le=1,
        validation_alias=AliasChoices("confidence", "extraction_confidence"),
        serialization_alias="confidence",
    )
    warnings: list[str] = Field(default_factory=list)


class AIExtractionResult(ORMModel):
    answers: list[AIExtractedAnswer]


class AIAnswerMapping(ORMModel):
    segment_index: int = Field(ge=0)
    question_number: str | None = None
    confidence: Decimal = Field(ge=0, le=1)
    reason: str = ""


class AIAnswerMappingResult(ORMModel):
    mappings: list[AIAnswerMapping]


class AIEvaluationCriterion(ORMModel):
    rubric_criterion_id: UUID | None = None
    criterion_text: str
    maximum_marks: Decimal = Field(ge=0)
    awarded_marks: Decimal = Field(ge=0)
    evidence: str = ""
    status: Literal["correct", "partial", "incorrect", "missing", "not_applicable"] = "missing"
    reason: str = ""


class AIEvaluationResult(ORMModel):
    marks_awarded: Decimal = Field(ge=0)
    max_marks: Decimal = Field(ge=0)
    confidence: Decimal = Field(ge=0, le=1)
    criteria: list[AIEvaluationCriterion] = []
    strengths: list[str] = []
    missing_points: list[str] = []
    feedback: str = ""
    reasoning: str = ""
    warnings: list[str] = Field(default_factory=list)
