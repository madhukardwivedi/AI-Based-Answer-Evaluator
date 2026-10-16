from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.common import ORMModel


class QuestionBase(ORMModel):
    question_number: str = Field(min_length=1, max_length=100)
    question_text: str = Field(min_length=1)
    model_answer: str | None = None
    key_concepts: str | None = None
    acceptable_alternatives: str | None = None
    reference_solution: str | None = None
    marking_notes: str | None = None
    maximum_marks: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    sequence_order: int = Field(ge=0)
    parent_question_id: UUID | None = None

    @field_validator("question_number", "question_text")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class QuestionCreate(QuestionBase):
    pass


class QuestionUpdate(QuestionBase):
    pass


class QuestionRead(QuestionBase):
    id: UUID
    exam_id: UUID
    created_at: datetime
    updated_at: datetime


class RubricCriterionBase(ORMModel):
    criterion: str = Field(min_length=1, max_length=255)
    description: str | None = None
    maximum_marks: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    sequence_order: int = Field(ge=0)

    @field_validator("criterion")
    @classmethod
    def strip_criterion(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class RubricCriterionCreate(RubricCriterionBase):
    pass


class RubricCriterionUpdate(RubricCriterionBase):
    pass


class QuestionBulkDelete(ORMModel):
    question_ids: list[UUID] = Field(min_length=1)


class RubricCriterionRead(RubricCriterionBase):
    id: UUID
    question_id: UUID
