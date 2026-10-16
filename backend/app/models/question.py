import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        UniqueConstraint("exam_id", "question_number", name="uq_questions_exam_number"),
        UniqueConstraint("exam_id", "sequence_order", name="uq_questions_exam_sequence"),
        CheckConstraint("maximum_marks >= 0", name="ck_questions_maximum_marks_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_question_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("questions.id"), nullable=True)
    question_number: Mapped[str] = mapped_column(String(100), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    model_answer: Mapped[str | None] = mapped_column(Text)
    key_concepts: Mapped[str | None] = mapped_column(Text)
    acceptable_alternatives: Mapped[str | None] = mapped_column(Text)
    reference_solution: Mapped[str | None] = mapped_column(Text)
    marking_notes: Mapped[str | None] = mapped_column(Text)
    maximum_marks: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    exam: Mapped["Exam"] = relationship(back_populates="questions")
    parent_question: Mapped["Question | None"] = relationship(remote_side="Question.id", back_populates="sub_questions")
    sub_questions: Mapped[list["Question"]] = relationship(back_populates="parent_question")
    rubric_criteria: Mapped[list["RubricCriterion"]] = relationship(
        back_populates="question", cascade="all, delete-orphan", order_by="RubricCriterion.sequence_order"
    )
    student_answers: Mapped[list["StudentAnswer"]] = relationship(back_populates="question")


class RubricCriterion(Base):
    __tablename__ = "rubric_criteria"
    __table_args__ = (
        UniqueConstraint("question_id", "sequence_order", name="uq_rubric_criteria_question_sequence"),
        CheckConstraint("maximum_marks >= 0", name="ck_rubric_criteria_maximum_marks_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    criterion: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    maximum_marks: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)

    question: Mapped[Question] = relationship(back_populates="rubric_criteria")
