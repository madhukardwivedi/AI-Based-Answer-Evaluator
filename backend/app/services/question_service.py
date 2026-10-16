from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.evaluation import EvaluationStatus
from app.models.question import Question, RubricCriterion
from app.models.submission import SubmissionStatus
from app.models.user import User
from app.repositories.question_repository import QuestionRepository
from app.schemas.question import (
    QuestionCreate,
    QuestionUpdate,
    RubricCriterionCreate,
    RubricCriterionUpdate,
)
from app.services.exam_service import ExamService


class QuestionService:
    def __init__(self, questions: QuestionRepository | None = None, exams: ExamService | None = None) -> None:
        self.questions = questions or QuestionRepository()
        self.exams = exams or ExamService()

    def list(self, db: Session, exam_id: UUID, user: User) -> list[Question]:
        self.exams.get(db, exam_id, user)
        return self.questions.list_for_exam(db, exam_id)

    def get(self, db: Session, question_id: UUID, user: User) -> Question:
        question = self.questions.get(db, question_id)
        if question is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        self.exams.get(db, question.exam_id, user)
        return question

    def create(self, db: Session, exam_id: UUID, data: QuestionCreate, user: User) -> Question:
        self.exams.get(db, exam_id, user)
        if data.parent_question_id and self.questions.get_for_exam(db, data.parent_question_id, exam_id) is None:
            raise HTTPException(status_code=422, detail="Parent question must belong to this exam")
        return self._save(db, Question(exam_id=exam_id, **data.model_dump()))

    def update(self, db: Session, question_id: UUID, data: QuestionUpdate, user: User) -> Question:
        question = self.get(db, question_id, user)
        if data.parent_question_id and self.questions.get_for_exam(db, data.parent_question_id, question.exam_id) is None:
            raise HTTPException(status_code=422, detail="Parent question must belong to this exam")
        rubric_total = sum((criterion.maximum_marks for criterion in self.questions.list_criteria(db, question.id)), Decimal("0"))
        if rubric_total > data.maximum_marks:
            raise HTTPException(
                status_code=422,
                detail="Question maximum marks cannot be lower than its rubric criteria total",
            )
        grading_fields = {"question_text", "model_answer", "key_concepts", "acceptable_alternatives", "reference_solution", "marking_notes", "maximum_marks"}
        grading_changed = any(getattr(question, field) != value for field, value in data.model_dump().items() if field in grading_fields)
        for field, value in data.model_dump().items():
            setattr(question, field, value)
        if grading_changed:
            self._invalidate_evaluations(question)
        return self._save(db, question)

    def delete(self, db: Session, question_id: UUID, user: User) -> None:
        self.questions.delete(db, self.get(db, question_id, user))

    def bulk_delete(self, db: Session, exam_id: UUID, question_ids: list[UUID], user: User) -> int:
        self.exams.get(db, exam_id, user)
        ids = list(dict.fromkeys(question_ids))
        owned = [self.questions.get_for_exam(db, question_id, exam_id) for question_id in ids]
        if any(item is None for item in owned):
            raise HTTPException(status_code=422, detail="Every selected question must belong to this exam")
        try:
            for item in owned:
                db.delete(item)
            db.commit()
        except Exception:
            db.rollback()
            raise
        return len(ids)

    def list_criteria(self, db: Session, question_id: UUID, user: User) -> list[RubricCriterion]:
        self.get(db, question_id, user)
        return self.questions.list_criteria(db, question_id)

    def create_criterion(self, db: Session, question_id: UUID, data: RubricCriterionCreate, user: User) -> RubricCriterion:
        question = self.get(db, question_id, user)
        self._validate_rubric_total(db, question, data.maximum_marks)
        self._invalidate_evaluations(question)
        return self._save(db, RubricCriterion(question_id=question.id, **data.model_dump()))

    def update_criterion(self, db: Session, criterion_id: UUID, data: RubricCriterionUpdate, user: User) -> RubricCriterion:
        criterion = self.questions.get_criterion(db, criterion_id)
        if criterion is None:
            raise HTTPException(status_code=404, detail="Rubric criterion not found")
        question = self.get(db, criterion.question_id, user)
        self._validate_rubric_total(db, question, data.maximum_marks, exclude_criterion_id=criterion.id)
        self._invalidate_evaluations(question)
        for field, value in data.model_dump().items():
            setattr(criterion, field, value)
        return self._save(db, criterion)

    def delete_criterion(self, db: Session, criterion_id: UUID, user: User) -> None:
        criterion = self.questions.get_criterion(db, criterion_id)
        if criterion is None:
            raise HTTPException(status_code=404, detail="Rubric criterion not found")
        question = self.get(db, criterion.question_id, user)
        self._invalidate_evaluations(question)
        self.questions.delete(db, criterion)

    @staticmethod
    def _invalidate_evaluations(question: Question) -> None:
        for answer in question.student_answers:
            if answer.evaluation is None:
                continue
            answer.evaluation.status = EvaluationStatus.STALE
            answer.student_submission.evaluation_status = "in_progress"
            answer.student_submission.finalized_at = None
            answer.student_submission.status = SubmissionStatus.REVIEW_REQUIRED

    def _save(self, db: Session, item: Question | RubricCriterion) -> Question | RubricCriterion:
        try:
            return self.questions.save(db, item)
        except IntegrityError as error:
            db.rollback()
            raise HTTPException(status_code=409, detail="Question numbering or sequence order already exists") from error

    def _validate_rubric_total(
        self,
        db: Session,
        question: Question,
        proposed_marks: Decimal,
        exclude_criterion_id: UUID | None = None,
    ) -> None:
        existing_total = sum(
            (
                criterion.maximum_marks
                for criterion in self.questions.list_criteria(db, question.id)
                if criterion.id != exclude_criterion_id
            ),
            Decimal("0"),
        )
        if existing_total + proposed_marks > question.maximum_marks:
            raise HTTPException(
                status_code=422,
                detail="Rubric criteria marks cannot exceed the question maximum marks",
            )
