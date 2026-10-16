from uuid import UUID

from typing import Annotated

from fastapi import APIRouter, File, Response, UploadFile, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.student import StudentCreate, StudentImportResult, StudentRead, StudentUpdate
from app.services.student_service import StudentService

exam_router = APIRouter(prefix="/api/exams/{exam_id}/students", tags=["students"])
student_router = APIRouter(prefix="/api/students", tags=["students"])


@exam_router.get("", response_model=list[StudentRead])
def list_students(exam_id: UUID, db: DbSession, user: CurrentUser) -> list[StudentRead]:
    return StudentService().list(db, exam_id, user)


@exam_router.post("", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
def create_student(exam_id: UUID, payload: StudentCreate, db: DbSession, user: CurrentUser) -> StudentRead:
    return StudentService().create(db, exam_id, payload, user)


@exam_router.post("/import", response_model=StudentImportResult)
def import_students(
    exam_id: UUID,
    file: Annotated[UploadFile, File()],
    db: DbSession,
    user: CurrentUser,
) -> StudentImportResult:
    return StudentService().import_roster(db, exam_id, file, user)


@student_router.get("/{student_id}", response_model=StudentRead)
def get_student(student_id: UUID, db: DbSession, user: CurrentUser) -> StudentRead:
    return StudentService().get(db, student_id, user)


@student_router.put("/{student_id}", response_model=StudentRead)
def update_student(student_id: UUID, payload: StudentUpdate, db: DbSession, user: CurrentUser) -> StudentRead:
    return StudentService().update(db, student_id, payload, user)


@student_router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: UUID, db: DbSession, user: CurrentUser) -> Response:
    StudentService().delete(db, student_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
