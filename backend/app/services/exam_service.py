from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.exam import Exam
from app.models.user import User
from app.repositories.exam_repository import ExamRepository
from app.schemas.exam import ExamCreate, ExamUpdate


class ExamService:
    def __init__(self, exams: ExamRepository | None = None) -> None:
        self.exams = exams or ExamRepository()

    def list(self, db: Session, user: User) -> list[Exam]:
        return self.exams.list_for_user(db, user.id)

    def get(self, db: Session, exam_id: UUID, user: User) -> Exam:
        exam = self.exams.get_for_user(db, exam_id, user.id)
        if exam is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
        return exam

    def create(self, db: Session, data: ExamCreate, user: User) -> Exam:
        return self.exams.create(db, Exam(created_by_id=user.id, **data.model_dump()))

    def update(self, db: Session, exam_id: UUID, data: ExamUpdate, user: User) -> Exam:
        exam = self.get(db, exam_id, user)
        for field, value in data.model_dump().items():
            setattr(exam, field, value)
        return self.exams.save(db, exam)

    def delete(self, db: Session, exam_id: UUID, user: User) -> None:
        self.exams.delete(db, self.get(db, exam_id, user))
