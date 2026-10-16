from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.exam import Exam


class ExamRepository:
    def list_for_user(self, db: Session, user_id: UUID) -> list[Exam]:
        return list(db.scalars(select(Exam).where(Exam.created_by_id == user_id).order_by(Exam.created_at.desc())))

    def get_for_user(self, db: Session, exam_id: UUID, user_id: UUID) -> Exam | None:
        return db.scalar(select(Exam).where(Exam.id == exam_id, Exam.created_by_id == user_id))

    def create(self, db: Session, exam: Exam) -> Exam:
        db.add(exam)
        db.commit()
        db.refresh(exam)
        return exam

    def save(self, db: Session, exam: Exam) -> Exam:
        db.commit()
        db.refresh(exam)
        return exam

    def delete(self, db: Session, exam: Exam) -> None:
        db.delete(exam)
        db.commit()
