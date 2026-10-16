import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EvaluationStatus(str, enum.Enum):
    AI_EVALUATED = "ai_evaluated"
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"
    MANUALLY_MODIFIED = "manually_modified"
    FAILED = "failed"
    STALE = "stale"


class AnswerSheetPage(Base):
    __tablename__ = "answer_sheet_pages"
    __table_args__ = (CheckConstraint("page_number >= 1", name="ck_answer_sheet_pages_page_number_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    answer_sheet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("answer_sheets.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number: Mapped[int] = mapped_column(nullable=False)
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    extraction_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    answer_sheet: Mapped["AnswerSheet"] = relationship(back_populates="pages")


class StudentAnswer(Base):
    __tablename__ = "student_answers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_submission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("student_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("questions.id", ondelete="SET NULL"), index=True)
    detected_question_number: Mapped[str | None] = mapped_column(String(100))
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Immutable machine transcription. `answer_text` remains for API compatibility.
    raw_text: Mapped[str | None] = mapped_column(Text)
    edited_text: Mapped[str | None] = mapped_column(Text)
    extraction_status: Mapped[str] = mapped_column(String(30), nullable=False, default="extracted")
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    extraction_method: Mapped[str | None] = mapped_column(String(50))
    provider: Mapped[str | None] = mapped_column(String(50))
    model_name: Mapped[str | None] = mapped_column(String(100))
    page_numbers: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    extraction_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    mapping_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    mapping_status: Mapped[str] = mapped_column(String(30), nullable=False, default="unmapped")
    manually_corrected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    student_submission: Mapped["StudentSubmission"] = relationship(back_populates="student_answers")
    question: Mapped["Question | None"] = relationship(back_populates="student_answers")
    evaluation: Mapped["Evaluation | None"] = relationship(back_populates="student_answer", cascade="all, delete-orphan", uselist=False)

    @property
    def effective_answer_text(self) -> str:
        return self.edited_text or self.raw_text or self.answer_text


class Evaluation(Base):
    __tablename__ = "evaluations"
    __table_args__ = (
        CheckConstraint("ai_marks >= 0", name="ck_evaluations_ai_marks_non_negative"),
        CheckConstraint("manual_marks IS NULL OR manual_marks >= 0", name="ck_evaluations_manual_marks_non_negative"),
        CheckConstraint("final_marks >= 0", name="ck_evaluations_final_marks_non_negative"),
        CheckConstraint("ai_marks <= maximum_marks", name="ck_evaluations_ai_marks_within_maximum"),
        CheckConstraint("manual_marks IS NULL OR manual_marks <= maximum_marks", name="ck_evaluations_manual_marks_within_maximum"),
        CheckConstraint("final_marks <= maximum_marks", name="ck_evaluations_final_marks_within_maximum"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_answer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("student_answers.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    ai_marks: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    manual_marks: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    final_marks: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    maximum_marks: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    strengths: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    missing_points: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    feedback: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reasoning: Mapped[str] = mapped_column(Text, nullable=False, default="")
    faculty_remarks: Mapped[str | None] = mapped_column(Text)
    status: Mapped[EvaluationStatus] = mapped_column(Enum(EvaluationStatus, native_enum=False), nullable=False, default=EvaluationStatus.AI_EVALUATED)
    ai_provider: Mapped[str | None] = mapped_column(String(50))
    ai_model: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(100))
    evaluation_method: Mapped[str] = mapped_column(String(40), nullable=False, default="overall_reference")
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    student_answer: Mapped["StudentAnswer"] = relationship(back_populates="evaluation")
    criteria: Mapped[list["EvaluationCriterion"]] = relationship(back_populates="evaluation", cascade="all, delete-orphan")


class EvaluationCriterion(Base):
    __tablename__ = "evaluation_criteria"
    __table_args__ = (
        CheckConstraint("maximum_marks >= 0", name="ck_evaluation_criteria_maximum_marks_non_negative"),
        CheckConstraint("awarded_marks >= 0", name="ck_evaluation_criteria_awarded_marks_non_negative"),
        CheckConstraint("awarded_marks <= maximum_marks", name="ck_evaluation_criteria_awarded_marks_within_maximum"),
        CheckConstraint("faculty_awarded_marks IS NULL OR faculty_awarded_marks >= 0", name="ck_evaluation_criteria_faculty_marks_non_negative"),
        CheckConstraint("faculty_awarded_marks IS NULL OR faculty_awarded_marks <= maximum_marks", name="ck_evaluation_criteria_faculty_marks_within_maximum"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False, index=True)
    rubric_criterion_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("rubric_criteria.id", ondelete="SET NULL"))
    criterion_text_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    maximum_marks: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    awarded_marks: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    faculty_awarded_marks: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    evidence: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="missing")
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")

    evaluation: Mapped["Evaluation"] = relationship(back_populates="criteria")

    @property
    def final_awarded_marks(self) -> Decimal:
        return self.faculty_awarded_marks if self.faculty_awarded_marks is not None else self.awarded_marks
