from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_validator

from app.models.exam import ExamStatus
from app.schemas.common import ORMModel


class ExamBase(ORMModel):
    name: str = Field(min_length=1, max_length=255)
    subject: str = Field(min_length=1, max_length=200)
    class_name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    total_marks: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    status: ExamStatus = ExamStatus.DRAFT

    @field_validator("name", "subject", "class_name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class ExamCreate(ExamBase):
    pass


class ExamUpdate(ExamBase):
    pass


class ExamRead(ExamBase):
    id: UUID
    created_by_id: UUID
    created_at: datetime
    updated_at: datetime
