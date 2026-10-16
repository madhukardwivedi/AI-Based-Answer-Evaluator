from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.question import Question, RubricCriterion


class QuestionRepository:
    def list_for_exam(self, db: Session, exam_id: UUID) -> list[Question]:
        statement = (
            select(Question)
            .where(Question.exam_id == exam_id)
            .options(selectinload(Question.rubric_criteria))
            .order_by(Question.sequence_order)
        )
        return list(db.scalars(statement))

    def get_for_exam(self, db: Session, question_id: UUID, exam_id: UUID) -> Question | None:
        return db.scalar(select(Question).where(Question.id == question_id, Question.exam_id == exam_id))

    def get(self, db: Session, question_id: UUID) -> Question | None:
        return db.get(Question, question_id)

    def save(self, db: Session, item: Question | RubricCriterion) -> Question | RubricCriterion:
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def delete(self, db: Session, item: Question | RubricCriterion) -> None:
        db.delete(item)
        db.commit()

    def list_criteria(self, db: Session, question_id: UUID) -> list[RubricCriterion]:
        return list(
            db.scalars(
                select(RubricCriterion)
                .where(RubricCriterion.question_id == question_id)
                .order_by(RubricCriterion.sequence_order)
            )
        )

    def get_criterion(self, db: Session, criterion_id: UUID) -> RubricCriterion | None:
        return db.get(RubricCriterion, criterion_id)
