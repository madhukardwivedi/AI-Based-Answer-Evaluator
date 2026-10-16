from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.common import ORMModel


class StudentBase(ORMModel):
    name: str = Field(min_length=1, max_length=200)
    roll_number: str | None = Field(default=None, max_length=100)
    external_id: str | None = Field(default=None, max_length=200)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("roll_number", "external_id", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class StudentCreate(StudentBase):
    pass


class StudentUpdate(StudentBase):
    pass


class StudentRead(StudentBase):
    id: UUID
    exam_id: UUID
    created_at: datetime
    updated_at: datetime


class StudentImportError(ORMModel):
    row: int = Field(ge=2)
    field: str
    message: str


class StudentImportResult(ORMModel):
    total_rows: int = Field(ge=0)
    imported_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    errors: list[StudentImportError]
