from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, Response, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, DbSession
from app.schemas.answer_sheet import AnswerSheetRead
from app.schemas.evaluation import StudentAnswerRead
from app.services.answer_sheet_service import AnswerSheetService
from app.services.evaluation_service import EvaluationService

exam_router = APIRouter(prefix="/api/exams/{exam_id}/answer-sheets", tags=["answer sheets"])
answer_sheet_router = APIRouter(prefix="/api/answer-sheets", tags=["answer sheets"])


@exam_router.get("", response_model=list[AnswerSheetRead])
def list_answer_sheets(exam_id: UUID, db: DbSession, user: CurrentUser) -> list[AnswerSheetRead]:
    return AnswerSheetService().list(db, exam_id, user)


@exam_router.post("", response_model=AnswerSheetRead, status_code=status.HTTP_201_CREATED)
def upload_answer_sheet(
    exam_id: UUID,
    student_id: Annotated[UUID, Form()],
    file: Annotated[UploadFile, File()],
    db: DbSession,
    user: CurrentUser,
) -> AnswerSheetRead:
    return AnswerSheetService().upload(db, exam_id, student_id, file, user)


@answer_sheet_router.get("/{answer_sheet_id}", response_model=AnswerSheetRead)
def get_answer_sheet(answer_sheet_id: UUID, db: DbSession, user: CurrentUser) -> AnswerSheetRead:
    return AnswerSheetService().get(db, answer_sheet_id, user)


@answer_sheet_router.delete("/{answer_sheet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_answer_sheet(answer_sheet_id: UUID, db: DbSession, user: CurrentUser) -> Response:
    AnswerSheetService().delete(db, answer_sheet_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@answer_sheet_router.post("/{answer_sheet_id}/process", response_model=list[StudentAnswerRead])
def process_answer_sheet(answer_sheet_id: UUID, db: DbSession, user: CurrentUser) -> list[StudentAnswerRead]:
    return EvaluationService().process(db, answer_sheet_id, user)


@answer_sheet_router.get("/{answer_sheet_id}/pages/{page_number}")
def answer_sheet_page_preview(answer_sheet_id: UUID, page_number: int, db: DbSession, user: CurrentUser) -> FileResponse:
    path = EvaluationService().page_preview_path(db, answer_sheet_id, page_number, user)
    return FileResponse(path, media_type="image/png")
