from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.answer_sheet import AnswerSheet
from app.models.student import Student
from app.models.submission import SubmissionFile, StudentSubmission


class SubmissionService:
    """Domain service for submission ownership and source-file mapping invariants."""

    def create(
        self,
        db: Session,
        *,
        exam_id: UUID,
        student: Student,
        replaces_submission_id: UUID | None = None,
    ) -> StudentSubmission:
        if student.exam_id != exam_id:
            raise HTTPException(status_code=422, detail="Student submission must belong to the student's exam")
        if replaces_submission_id is not None:
            replaced = db.get(StudentSubmission, replaces_submission_id)
            if replaced is None or replaced.exam_id != exam_id or replaced.student_id != student.id:
                raise HTTPException(status_code=422, detail="Replacement submission must belong to the same student and exam")
        submission = StudentSubmission(exam_id=exam_id, student_id=student.id, replaces_submission_id=replaces_submission_id)
        db.add(submission)
        db.flush()
        return submission

    def link_source(
        self,
        db: Session,
        *,
        submission: StudentSubmission,
        source_upload: AnswerSheet,
        sequence_order: int,
        page_start: int | None = None,
        page_end: int | None = None,
        file_role: str | None = None,
    ) -> SubmissionFile:
        if source_upload.exam_id != submission.exam_id:
            raise HTTPException(status_code=422, detail="Source upload must belong to the submission's exam")
        if sequence_order < 1:
            raise HTTPException(status_code=422, detail="Sequence order must be at least 1")
        if page_start is not None and page_start < 1:
            raise HTTPException(status_code=422, detail="Page start must be at least 1")
        if page_end is not None and page_end < 1:
            raise HTTPException(status_code=422, detail="Page end must be at least 1")
        if page_start is not None and page_end is not None and page_end < page_start:
            raise HTTPException(status_code=422, detail="Page end must not be before page start")

        duplicate_conditions = [
            SubmissionFile.submission_id == submission.id,
            SubmissionFile.answer_sheet_id == source_upload.id,
            SubmissionFile.page_start.is_(None) if page_start is None else SubmissionFile.page_start == page_start,
            SubmissionFile.page_end.is_(None) if page_end is None else SubmissionFile.page_end == page_end,
        ]
        duplicate = db.scalar(select(SubmissionFile).where(*duplicate_conditions))
        if duplicate is not None:
            raise HTTPException(status_code=409, detail="Source upload and page range are already linked to this submission")
        link = SubmissionFile(
            submission_id=submission.id,
            answer_sheet_id=source_upload.id,
            sequence_order=sequence_order,
            page_start=page_start,
            page_end=page_end,
            file_role=file_role.strip() if file_role else None,
        )
        db.add(link)
        db.flush()
        return link

    def reassign(self, db: Session, *, submission: StudentSubmission, student: Student) -> StudentSubmission:
        if student.exam_id != submission.exam_id:
            raise HTTPException(status_code=422, detail="Student assignment must belong to the submission's exam")
        submission.student_id = student.id
        db.flush()
        return submission
