from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, File, Response, UploadFile, status
from app.api.deps import CurrentUser, DbSession
from app.schemas.question_paper import QuestionPaperImportRequest,QuestionPaperImportResult,QuestionPaperRead
from app.services.question_paper_service import QuestionPaperService
router=APIRouter(prefix="/api/exams/{exam_id}/question-paper",tags=["question papers"])
@router.get("",response_model=QuestionPaperRead|None)
def get_question_paper(exam_id:UUID,db:DbSession,user:CurrentUser): return QuestionPaperService().get(db,exam_id,user)
@router.post("",response_model=QuestionPaperRead,status_code=status.HTTP_201_CREATED)
def upload_question_paper(exam_id:UUID,file:Annotated[UploadFile,File()],db:DbSession,user:CurrentUser): return QuestionPaperService().upload(db,exam_id,file,user)
@router.delete("",status_code=204)
def delete_question_paper(exam_id:UUID,db:DbSession,user:CurrentUser): QuestionPaperService().delete(db,exam_id,user); return Response(status_code=204)
@router.post("/parse",response_model=QuestionPaperRead)
def parse_question_paper(exam_id:UUID,db:DbSession,user:CurrentUser): return QuestionPaperService().parse(db,exam_id,user)
@router.post("/import",response_model=QuestionPaperImportResult)
def import_questions(exam_id:UUID,payload:QuestionPaperImportRequest,db:DbSession,user:CurrentUser): return QuestionPaperService().import_questions(db,exam_id,payload,user)
