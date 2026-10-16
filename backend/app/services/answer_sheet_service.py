from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models.answer_sheet import AnswerSheet, AnswerSheetStatus
from app.models.user import User
from app.repositories.answer_sheet_repository import AnswerSheetRepository
from app.schemas.answer_sheet import AnswerSheetRead
from app.services.exam_service import ExamService
from app.services.storage_service import LocalStorageService
from app.services.student_service import StudentService
from app.services.submission_service import SubmissionService

ALLOWED_MIME_TYPES: dict[str, set[str]] = {
    ".pdf": {"application/pdf"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
}


class AnswerSheetService:
    def __init__(
        self,
        answer_sheets: AnswerSheetRepository | None = None,
        exams: ExamService | None = None,
        students: StudentService | None = None,
        storage: LocalStorageService | None = None,
        submissions: SubmissionService | None = None,
    ) -> None:
        self.answer_sheets = answer_sheets or AnswerSheetRepository()
        self.exams = exams or ExamService()
        self.students = students or StudentService()
        self.storage = storage or LocalStorageService()
        self.submissions = submissions or SubmissionService()

    def list(self, db: Session, exam_id: UUID, user: User) -> list[AnswerSheetRead]:
        self.exams.get(db, exam_id, user)
        return [self._read(item) for item in self.answer_sheets.list_for_exam(db, exam_id)]

    def get(self, db: Session, answer_sheet_id: UUID, user: User) -> AnswerSheetRead:
        return self._read(self._owned_sheet(db, answer_sheet_id, user))

    def upload(self, db: Session, exam_id: UUID, student_id: UUID, upload: UploadFile, user: User) -> AnswerSheetRead:
        self.exams.get(db, exam_id, user)
        student = self.students.get(db, student_id, user)
        if student.exam_id != exam_id:
            raise HTTPException(status_code=422, detail="Student must belong to this exam")

        original_filename = Path(upload.filename or "").name
        extension = Path(original_filename).suffix.lower()
        permitted_mimes = ALLOWED_MIME_TYPES.get(extension)
        if not original_filename or permitted_mimes is None:
            raise HTTPException(status_code=422, detail="Only PDF, JPG, JPEG, and PNG files are supported")
        if upload.content_type not in permitted_mimes:
            raise HTTPException(status_code=422, detail="File MIME type does not match the permitted format")

        try:
            stored_filename, file_path, file_size = self.storage.save_upload(
                upload, exam_id=exam_id, student_id=student_id, extension=extension
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        if file_size == 0:
            self.storage.delete(file_path)
            raise HTTPException(status_code=422, detail="Uploaded file must not be empty")

        answer_sheet = AnswerSheet(
            exam_id=exam_id,
            student_id=student_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=file_path,
            mime_type=upload.content_type,
            file_size=file_size,
            status=AnswerSheetStatus.UPLOADED,
        )
        try:
            db.add(answer_sheet)
            db.flush()
            submission = self.submissions.create(db, exam_id=exam_id, student=student)
            self.submissions.link_source(db, submission=submission, source_upload=answer_sheet, sequence_order=1, file_role="main")
            db.commit()
            db.refresh(answer_sheet)
            return self._read(answer_sheet)
        except Exception:
            db.rollback()
            self.storage.delete(file_path)
            raise

    def delete(self, db: Session, answer_sheet_id: UUID, user: User) -> None:
        answer_sheet = self._owned_sheet(db, answer_sheet_id, user)
        links = list(answer_sheet.submission_files)
        affected_submissions = {link.submission_id: link.submission for link in links}
        if len(affected_submissions) > 1:
            raise HTTPException(status_code=409, detail="This source upload is shared by multiple submissions and cannot be deleted directly")
        generated_page_paths = [page.image_path for page in answer_sheet.pages]
        try:
            for submission in affected_submissions.values():
                for extracted_answer in list(submission.student_answers):
                    db.delete(extracted_answer)
                remaining_files = [item for item in submission.files if item.answer_sheet_id != answer_sheet.id]
                if not remaining_files:
                    db.delete(submission)
            db.delete(answer_sheet)
            db.commit()
        except Exception:
            db.rollback()
            raise
        self.storage.delete(answer_sheet.file_path)
        for path in generated_page_paths:
            self.storage.delete(path)

    def _owned_sheet(self, db: Session, answer_sheet_id: UUID, user: User) -> AnswerSheet:
        answer_sheet = self.answer_sheets.get(db, answer_sheet_id)
        if answer_sheet is None:
            raise HTTPException(status_code=404, detail="Answer sheet not found")
        self.exams.get(db, answer_sheet.exam_id, user)
        return answer_sheet

    @staticmethod
    def _read(answer_sheet: AnswerSheet) -> AnswerSheetRead:
        return AnswerSheetRead(
            **{field: getattr(answer_sheet, field) for field in AnswerSheetRead.model_fields if field not in {"student_name", "student_roll_number"}},
            student_name=answer_sheet.student.name if answer_sheet.student else None,
            student_roll_number=answer_sheet.student.roll_number if answer_sheet.student else None,
        )
