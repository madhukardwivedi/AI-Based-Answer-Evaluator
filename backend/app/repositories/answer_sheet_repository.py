from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.answer_sheet import AnswerSheet


class AnswerSheetRepository:
    def list_for_exam(self, db: Session, exam_id: UUID) -> list[AnswerSheet]:
        statement = select(AnswerSheet).where(AnswerSheet.exam_id == exam_id).options(selectinload(AnswerSheet.student)).order_by(AnswerSheet.uploaded_at.desc())
        return list(db.scalars(statement))

    def get(self, db: Session, answer_sheet_id: UUID) -> AnswerSheet | None:
        return db.scalar(select(AnswerSheet).where(AnswerSheet.id == answer_sheet_id).options(selectinload(AnswerSheet.student)))

    def save(self, db: Session, answer_sheet: AnswerSheet) -> AnswerSheet:
        db.add(answer_sheet)
        db.commit()
        db.refresh(answer_sheet)
        return answer_sheet

    def delete(self, db: Session, answer_sheet: AnswerSheet) -> None:
        db.delete(answer_sheet)
        db.commit()
