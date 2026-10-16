import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SubmissionStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    REVIEW_REQUIRED = "review_required"
    COMPLETED = "completed"


class StudentSubmission(Base):
    __tablename__ = "student_submissions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    replaces_submission_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("student_submissions.id", ondelete="SET NULL"))
    status: Mapped[SubmissionStatus] = mapped_column(Enum(SubmissionStatus, native_enum=False), default=SubmissionStatus.SUBMITTED)
    evaluation_status: Mapped[str] = mapped_column(String(30), nullable=False, default="not_started")
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    exam: Mapped["Exam"] = relationship(back_populates="submissions")
    student: Mapped["Student"] = relationship(back_populates="submissions")
    replaces_submission: Mapped["StudentSubmission | None"] = relationship(remote_side="StudentSubmission.id")
    files: Mapped[list["SubmissionFile"]] = relationship(back_populates="submission", cascade="all, delete-orphan", order_by="SubmissionFile.sequence_order")
    student_answers: Mapped[list["StudentAnswer"]] = relationship(back_populates="student_submission", cascade="all, delete-orphan")


class SubmissionFile(Base):
    __tablename__ = "submission_files"
    __table_args__ = (
        UniqueConstraint("submission_id", "answer_sheet_id", "page_start", "page_end", name="uq_submission_files_source_range"),
        CheckConstraint("sequence_order >= 1", name="ck_submission_files_sequence_order_positive"),
        CheckConstraint("page_start IS NULL OR page_start >= 1", name="ck_submission_files_page_start_positive"),
        CheckConstraint("page_end IS NULL OR page_end >= 1", name="ck_submission_files_page_end_positive"),
        CheckConstraint("page_start IS NULL OR page_end IS NULL OR page_end >= page_start", name="ck_submission_files_page_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("student_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    answer_sheet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("answer_sheets.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    file_role: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    submission: Mapped[StudentSubmission] = relationship(back_populates="files")
    answer_sheet: Mapped["AnswerSheet"] = relationship(back_populates="submission_files")
