import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExamStatus(str, enum.Enum):
    DRAFT = "draft"
    CONFIGURED = "configured"
    PROCESSING = "processing"
    COMPLETED = "completed"


class Exam(Base):
    __tablename__ = "exams"
    __table_args__ = (CheckConstraint("total_marks >= 0", name="ck_exams_total_marks_non_negative"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    class_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    total_marks: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[ExamStatus] = mapped_column(Enum(ExamStatus, native_enum=False), default=ExamStatus.DRAFT)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    created_by: Mapped["User"] = relationship(back_populates="exams")
    questions: Mapped[list["Question"]] = relationship(
        back_populates="exam", cascade="all, delete-orphan", order_by="Question.sequence_order"
    )
    students: Mapped[list["Student"]] = relationship(back_populates="exam", cascade="all, delete-orphan")
    answer_sheets: Mapped[list["AnswerSheet"]] = relationship(back_populates="exam", cascade="all, delete-orphan")
    submissions: Mapped[list["StudentSubmission"]] = relationship(back_populates="exam", cascade="all, delete-orphan")
    question_paper: Mapped["QuestionPaper | None"] = relationship(back_populates="exam", cascade="all, delete-orphan", uselist=False)
