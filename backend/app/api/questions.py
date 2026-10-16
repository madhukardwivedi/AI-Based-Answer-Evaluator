from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.question import (
    QuestionCreate,
    QuestionBulkDelete,
    QuestionRead,
    QuestionUpdate,
    RubricCriterionCreate,
    RubricCriterionRead,
    RubricCriterionUpdate,
)
from app.services.question_service import QuestionService

exam_router = APIRouter(prefix="/api/exams/{exam_id}/questions", tags=["questions"])
question_router = APIRouter(prefix="/api/questions", tags=["questions"])
criterion_router = APIRouter(prefix="/api/rubric-criteria", tags=["rubric criteria"])


@exam_router.get("", response_model=list[QuestionRead])
def list_questions(exam_id: UUID, db: DbSession, user: CurrentUser) -> list[QuestionRead]:
    return QuestionService().list(db, exam_id, user)


@exam_router.post("", response_model=QuestionRead, status_code=status.HTTP_201_CREATED)
def create_question(exam_id: UUID, payload: QuestionCreate, db: DbSession, user: CurrentUser) -> QuestionRead:
    return QuestionService().create(db, exam_id, payload, user)


@exam_router.delete("/bulk")
def bulk_delete_questions(exam_id: UUID, payload: QuestionBulkDelete, db: DbSession, user: CurrentUser) -> dict[str, int]:
    return {"deleted_count": QuestionService().bulk_delete(db, exam_id, payload.question_ids, user)}


@question_router.get("/{question_id}", response_model=QuestionRead)
def get_question(question_id: UUID, db: DbSession, user: CurrentUser) -> QuestionRead:
    return QuestionService().get(db, question_id, user)


@question_router.put("/{question_id}", response_model=QuestionRead)
def update_question(question_id: UUID, payload: QuestionUpdate, db: DbSession, user: CurrentUser) -> QuestionRead:
    return QuestionService().update(db, question_id, payload, user)


@question_router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(question_id: UUID, db: DbSession, user: CurrentUser) -> Response:
    QuestionService().delete(db, question_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@question_router.get("/{question_id}/rubric-criteria", response_model=list[RubricCriterionRead])
def list_criteria(question_id: UUID, db: DbSession, user: CurrentUser) -> list[RubricCriterionRead]:
    return QuestionService().list_criteria(db, question_id, user)


@question_router.post("/{question_id}/rubric-criteria", response_model=RubricCriterionRead, status_code=status.HTTP_201_CREATED)
def create_criterion(question_id: UUID, payload: RubricCriterionCreate, db: DbSession, user: CurrentUser) -> RubricCriterionRead:
    return QuestionService().create_criterion(db, question_id, payload, user)


@criterion_router.put("/{criterion_id}", response_model=RubricCriterionRead)
def update_criterion(criterion_id: UUID, payload: RubricCriterionUpdate, db: DbSession, user: CurrentUser) -> RubricCriterionRead:
    return QuestionService().update_criterion(db, criterion_id, payload, user)


@criterion_router.delete("/{criterion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_criterion(criterion_id: UUID, db: DbSession, user: CurrentUser) -> Response:
    QuestionService().delete_criterion(db, criterion_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
