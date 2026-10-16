from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.exam import ExamCreate, ExamRead, ExamUpdate
from app.services.exam_service import ExamService

router = APIRouter(prefix="/api/exams", tags=["exams"])


@router.get("", response_model=list[ExamRead])
def list_exams(db: DbSession, user: CurrentUser) -> list[ExamRead]:
    return ExamService().list(db, user)


@router.post("", response_model=ExamRead, status_code=status.HTTP_201_CREATED)
def create_exam(payload: ExamCreate, db: DbSession, user: CurrentUser) -> ExamRead:
    return ExamService().create(db, payload, user)


@router.get("/{exam_id}", response_model=ExamRead)
def get_exam(exam_id: UUID, db: DbSession, user: CurrentUser) -> ExamRead:
    return ExamService().get(db, exam_id, user)


@router.put("/{exam_id}", response_model=ExamRead)
def update_exam(exam_id: UUID, payload: ExamUpdate, db: DbSession, user: CurrentUser) -> ExamRead:
    return ExamService().update(db, exam_id, payload, user)


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(exam_id: UUID, db: DbSession, user: CurrentUser) -> Response:
    ExamService().delete(db, exam_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
