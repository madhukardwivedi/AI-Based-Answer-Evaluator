from datetime import datetime
from uuid import UUID

from app.models.answer_sheet import AnswerSheetStatus
from app.schemas.common import ORMModel


class AnswerSheetRead(ORMModel):
    id: UUID
    exam_id: UUID
    student_id: UUID | None
    original_filename: str
    stored_filename: str
    mime_type: str
    file_size: int
    status: AnswerSheetStatus
    uploaded_at: datetime
    processing_started_at: datetime | None
    processing_completed_at: datetime | None
    processing_error: str | None
    student_name: str | None = None
    student_roll_number: str | None = None
