from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID
from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.ai.prompts.question_parser_v1 import QUESTION_PARSER_PROMPT_VERSION
from app.ai.question_parser import QuestionPaperParser, QuestionPaperParsingError, canonical_question_number, recover_visible_marks
from app.models.question import Question, RubricCriterion
from app.models.question_paper import QuestionPaper, QuestionPaperStatus
from app.models.user import User
from app.schemas.question_paper import QuestionPaperImportRequest, QuestionPaperImportResult, QuestionPaperRead
from app.services.exam_service import ExamService
from app.services.question_paper_document_service import DocumentProcessingError, QuestionPaperDocumentService
from app.services.storage_service import LocalStorageService

ALLOWED_MIME_TYPES = {".pdf":{"application/pdf"}, ".jpg":{"image/jpeg"}, ".jpeg":{"image/jpeg"}, ".png":{"image/png"}}

class QuestionPaperService:
    def __init__(self, storage: LocalStorageService|None=None, documents: QuestionPaperDocumentService|None=None) -> None:
        self.exams=ExamService(); self.storage=storage or LocalStorageService(); self.documents=documents or QuestionPaperDocumentService()
    def _paper(self, db: Session, exam_id: UUID) -> QuestionPaper|None:
        return db.scalar(select(QuestionPaper).where(QuestionPaper.exam_id==exam_id))
    def get(self, db: Session, exam_id: UUID, user: User) -> QuestionPaperRead|None:
        self.exams.get(db, exam_id, user); paper=self._paper(db, exam_id); return self._read(paper) if paper else None
    def upload(self, db: Session, exam_id: UUID, upload: UploadFile, user: User) -> QuestionPaperRead:
        self.exams.get(db,exam_id,user); original=Path(upload.filename or "").name; extension=Path(original).suffix.lower()
        if not original or extension not in ALLOWED_MIME_TYPES: raise HTTPException(422,"Only PDF, JPG, JPEG, and PNG files are supported")
        if upload.content_type not in ALLOWED_MIME_TYPES[extension]: raise HTTPException(422,"File MIME type does not match the permitted format")
        try: stored,path,size=self.storage.save_question_paper(upload,exam_id=exam_id,extension=extension)
        except ValueError as error: raise HTTPException(422,str(error)) from error
        if not size: self.storage.delete(path); raise HTTPException(422,"Uploaded file must not be empty")
        old=self._paper(db,exam_id); paper=QuestionPaper(exam_id=exam_id,original_filename=original,stored_filename=stored,file_path=path,mime_type=upload.content_type,file_size=size,status=QuestionPaperStatus.UPLOADED)
        try:
            if old: db.delete(old)
            db.add(paper); db.commit(); db.refresh(paper)
        except Exception:
            db.rollback(); self.storage.delete(path); raise
        if old: self.storage.delete(old.file_path)
        return self._read(paper)
    def delete(self,db:Session,exam_id:UUID,user:User)->None:
        self.exams.get(db,exam_id,user); paper=self._paper(db,exam_id)
        if not paper: raise HTTPException(404,"Question paper not found")
        path=paper.file_path; db.delete(paper); db.commit(); self.storage.delete(path)
    def parse(self,db:Session,exam_id:UUID,user:User)->QuestionPaperRead:
        exam=self.exams.get(db,exam_id,user); paper=self._paper(db,exam_id)
        if not paper: raise HTTPException(404,"Question paper not found")
        paper.status=QuestionPaperStatus.PARSING; paper.parsing_error=None; db.commit()
        try:
            path=(self.storage.root/paper.file_path).resolve()
            if self.storage.root not in path.parents or not path.is_file(): raise DocumentProcessingError("The stored question paper is missing")
            document=self.documents.extract(path,paper.mime_type); parser=QuestionPaperParser(exam_total=exam.total_marks); parsed=parser.parse(document)
            if document.use_text:
                parsed=recover_visible_marks(parsed, document.text)
            paper.status=QuestionPaperStatus.REVIEW_REQUIRED; paper.parse_result=parsed.model_dump(mode="json"); paper.parsed_at=datetime.now(timezone.utc); paper.parser_model=parser.model; paper.parser_provider=parser.provider; paper.parser_text_model=parser.text_model; paper.parser_vision_model=parser.vision_model; paper.prompt_version=QUESTION_PARSER_PROMPT_VERSION
            db.commit(); db.refresh(paper); return self._read(paper)
        except (DocumentProcessingError,QuestionPaperParsingError) as error:
            paper.status=QuestionPaperStatus.FAILED; paper.parsing_error=str(error); db.commit(); raise HTTPException(422,str(error)) from error
    def import_questions(self,db:Session,exam_id:UUID,data:QuestionPaperImportRequest,user:User)->QuestionPaperImportResult:
        self.exams.get(db,exam_id,user); existing=list(db.scalars(select(Question).where(Question.exam_id==exam_id))); known={canonical_question_number(q.question_number).lower() for q in existing}; skipped=[]; accepted=[]; seen=set()
        for item in data.questions:
            number=canonical_question_number(item.question_number); key=number.lower()
            if item.maximum_marks is None: skipped.append(f"{number}: maximum marks are missing")
            elif key in seen: skipped.append(f"{number}: duplicate candidate")
            elif key in known: skipped.append(number)
            elif sum((criterion.maximum_marks for criterion in item.rubric_criteria), Decimal("0")) > item.maximum_marks:
                skipped.append(f"{number}: rubric criteria marks exceed question maximum")
            else:
                parent=canonical_question_number(item.parent_question_number) if item.parent_question_number else None
                if parent == number: parent=None
                accepted.append(item.model_copy(update={"question_number":number,"parent_question_number":parent})); seen.add(key)
        parents={canonical_question_number(q.question_number):q.id for q in existing}; next_order=max((q.sequence_order for q in existing),default=-1)+1; created=[]
        for item in accepted:
            q=Question(
                exam_id=exam_id,
                question_number=item.question_number,
                question_text=item.question_text,
                model_answer=item.model_answer,
                key_concepts=item.key_concepts,
                acceptable_alternatives=item.acceptable_alternatives,
                reference_solution=item.reference_solution,
                marking_notes=item.marking_notes,
                maximum_marks=item.maximum_marks,
                sequence_order=next_order,
                parent_question_id=parents.get(item.parent_question_number or ""),
            )
            db.add(q); db.flush(); parents[item.question_number]=q.id; created.append(q)
            for criterion_order, criterion in enumerate(item.rubric_criteria):
                db.add(RubricCriterion(
                    question_id=q.id,
                    criterion=criterion.criterion,
                    description=criterion.description,
                    maximum_marks=criterion.maximum_marks,
                    sequence_order=criterion_order,
                ))
            next_order+=1
        db.commit(); return QuestionPaperImportResult(imported=[q.id for q in created],skipped_conflicts=skipped)
    @staticmethod
    def _read(paper:QuestionPaper)->QuestionPaperRead: return QuestionPaperRead.model_validate(paper)
