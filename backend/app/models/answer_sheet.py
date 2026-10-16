import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AnswerSheetStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    EXTRACTED = "extracted"
    EVALUATED = "evaluated"
    REVIEW_REQUIRED = "review_required"
    COMPLETED = "completed"
    FAILED = "failed"


class AnswerSheet(Base):
    __tablename__ = "answer_sheets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    # Optional legacy/intake hint only. Authoritative assignment lives on StudentSubmission.
    student_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[AnswerSheetStatus] = mapped_column(Enum(AnswerSheetStatus, native_enum=False), default=AnswerSheetStatus.UPLOADED)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_error: Mapped[str | None] = mapped_column(Text)

    exam: Mapped["Exam"] = relationship(back_populates="answer_sheets")
    student: Mapped["Student | None"] = relationship(back_populates="answer_sheets")
    submission_files: Mapped[list["SubmissionFile"]] = relationship(back_populates="answer_sheet", cascade="all, delete-orphan")
    pages: Mapped[list["AnswerSheetPage"]] = relationship(back_populates="answer_sheet", cascade="all, delete-orphan", order_by="AnswerSheetPage.page_number")
