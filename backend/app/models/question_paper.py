import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class QuestionPaperStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    REVIEW_REQUIRED = "review_required"
    FAILED = "failed"


class QuestionPaper(Base):
    __tablename__ = "question_papers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[QuestionPaperStatus] = mapped_column(Enum(QuestionPaperStatus, native_enum=False), nullable=False, default=QuestionPaperStatus.UPLOADED)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    parsing_error: Mapped[str | None] = mapped_column(Text)
    parser_model: Mapped[str | None] = mapped_column(String(100))
    parser_provider: Mapped[str | None] = mapped_column(String(50))
    parser_text_model: Mapped[str | None] = mapped_column(String(100))
    parser_vision_model: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(100))
    parse_result: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    exam: Mapped["Exam"] = relationship(back_populates="question_paper")
