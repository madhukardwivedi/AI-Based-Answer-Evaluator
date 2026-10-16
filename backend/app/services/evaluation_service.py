from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import logging
import re
from uuid import UUID

import fitz
from fastapi import HTTPException
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai.answer_extractor import AnswerExtractor, ExtractionDocument
from app.ai.answer_mapper import AnswerMapper
from app.ai.evaluator import AnswerEvaluator
from app.ai.structured_provider import AIProviderError
from app.core.config import get_settings
from app.models.answer_sheet import AnswerSheet, AnswerSheetStatus
from app.models.evaluation import AnswerSheetPage, Evaluation, EvaluationCriterion, EvaluationStatus, StudentAnswer
from app.models.question import Question
from app.models.submission import StudentSubmission, SubmissionStatus
from app.models.user import User
from app.schemas.evaluation import EvaluationUpdate
from app.services.answer_sheet_service import AnswerSheetService
from app.services.exam_service import ExamService
from app.services.storage_service import LocalStorageService

REVIEW_THRESHOLD = Decimal("0.65")
logger = logging.getLogger(__name__)


class EvaluationService:
    def __init__(self, storage: LocalStorageService | None = None) -> None:
        self.storage = storage or LocalStorageService()
        self.exams = ExamService()

    def process(self, db: Session, answer_sheet_id: UUID, user: User) -> list[StudentAnswer]:
        source = AnswerSheetService()._owned_sheet(db, answer_sheet_id, user)
        if source.status in {AnswerSheetStatus.PROCESSING}:
            raise HTTPException(status_code=409, detail="Answer sheet is already processing")
        links = list(source.submission_files)
        if not links:
            raise HTTPException(status_code=422, detail="Answer sheet is not linked to a student submission")
        existing = db.scalars(select(StudentAnswer).join(StudentSubmission).where(StudentSubmission.id.in_([link.submission_id for link in links]))).first()
        if existing:
            return list(db.scalars(select(StudentAnswer).where(StudentAnswer.student_submission_id.in_([link.submission_id for link in links]))))
        source.status = AnswerSheetStatus.PROCESSING
        source.processing_started_at = datetime.now(timezone.utc)
        db.commit()
        try:
            page_images = self._render_pages(source)
            for existing_page in list(source.pages):
                db.delete(existing_page)
            db.flush()
            pages: list[AnswerSheetPage] = []
            for page_number, image in enumerate(page_images, 1):
                path = self.storage.save_generated(image, relative_path=__import__('pathlib').Path("answer-sheet-pages") / str(source.id) / f"{page_number}.png")
                page = AnswerSheetPage(answer_sheet_id=source.id, page_number=page_number, image_path=path)
                db.add(page); pages.append(page)
            questions = list(db.scalars(select(Question).where(Question.exam_id == source.exam_id).order_by(Question.sequence_order)))
            if not questions: raise HTTPException(status_code=422, detail="Configure exam questions before extracting answers")
            extractor = AnswerExtractor()
            extracted = extractor.extract(ExtractionDocument(page_images, list(range(1, len(page_images) + 1))), [q.question_number for q in questions])
            by_number: dict[str, list[Question]] = {}
            for question in questions:
                by_number.setdefault(self._normal(question.question_number), []).append(question)
            resolved: list[tuple[Question | None, Decimal, str]] = []
            unresolved_indexes: list[int] = []
            threshold = Decimal(str(get_settings().ai_mapping_confidence_threshold))
            for item_index, item in enumerate(extracted.answers):
                matches = by_number.get(self._normal(item.detected_question_number or ""), [])
                # A unique canonical label is deterministic evidence of the mapping.
                # Extraction confidence measures transcription quality, not whether
                # the visible question identifier matches an exam question.
                if len(matches) == 1:
                    resolved.append((matches[0], Decimal("1"), "auto_mapped"))
                else:
                    resolved.append((None, Decimal("0"), "unmapped"))
                    unresolved_indexes.append(item_index)
            if unresolved_indexes and get_settings().ai_mapping_enabled:
                mapper = AnswerMapper()
                claimed_numbers = {
                    self._normal(question.question_number)
                    for question, _, _ in resolved
                    if question is not None
                }

                def apply_mapping(original_index: int, question_number: str | None, confidence: Decimal) -> bool:
                    if not question_number or confidence < threshold:
                        return False
                    matches = by_number.get(self._normal(question_number), [])
                    if len(matches) != 1:
                        return False
                    resolved[original_index] = (matches[0], confidence, "auto_mapped")
                    return True

                try:
                    # Map unresolved segments independently. Gemma's batch mapper can
                    # omit indexes or cross-assign visually similar mathematics. Do
                    # not offer questions already claimed by an explicit label, and
                    # remove each accepted semantic candidate from subsequent calls.
                    for original_index in unresolved_indexes:
                        candidates = [
                            {"question_number": q.question_number, "question_text": q.question_text}
                            for q in questions
                            if self._normal(q.question_number) not in claimed_numbers
                        ]
                        if not candidates:
                            continue
                        single_result = mapper.map([extracted.answers[original_index]], candidates)
                        single_mapping = next((item for item in single_result.mappings if item.segment_index == 0), None)
                        candidate_numbers = {self._normal(item["question_number"]) for item in candidates}
                        if (
                            single_mapping
                            and self._normal(single_mapping.question_number or "") in candidate_numbers
                            and apply_mapping(original_index, single_mapping.question_number, single_mapping.confidence)
                        ):
                            mapped_question = resolved[original_index][0]
                            if mapped_question is not None:
                                claimed_numbers.add(self._normal(mapped_question.question_number))
                except AIProviderError:
                    # Extraction remains usable; unresolved segments retain the manual
                    # mapping fallback instead of losing a successful transcription.
                    for original_index in unresolved_indexes:
                        if resolved[original_index][0] is None:
                            extracted.answers[original_index].warnings.append("Automatic question mapping failed; faculty review is required.")
            answers: list[StudentAnswer] = []
            for link in links:
                allowed_pages = set(range(link.page_start or 1, (link.page_end or len(page_images)) + 1))
                submission_answers = [(item_index, item) for item_index, item in enumerate(extracted.answers) if set(item.page_numbers or [1]) & allowed_pages]
                merged: dict[str, StudentAnswer] = {}
                for item_index, item in submission_answers:
                    key = self._normal(item.detected_question_number or "")
                    question, mapping_confidence, mapping_status = resolved[item_index]
                    merge_key = self._normal(question.question_number) if question else f"unmapped:{item.detected_question_number or len(merged)}"
                    if merge_key in merged:
                        answer = merged[merge_key]
                        answer.answer_text += "\n\n" + item.answer_text
                        answer.raw_text = (answer.raw_text or "") + "\n\n" + item.answer_text
                        answer.page_numbers = sorted(set(answer.page_numbers + (item.page_numbers or [1])))
                        answer.warnings = list(dict.fromkeys(answer.warnings + item.warnings))
                        answer.extraction_confidence = min(answer.extraction_confidence or Decimal("0"), item.extraction_confidence)
                        continue
                    status = "review_required" if item.extraction_confidence < REVIEW_THRESHOLD or question is None else "extracted"
                    answer = StudentAnswer(student_submission_id=link.submission_id, question_id=question.id if question else None, detected_question_number=item.detected_question_number, answer_text=item.answer_text, raw_text=item.answer_text, page_numbers=item.page_numbers or [1], extraction_confidence=item.extraction_confidence, mapping_confidence=mapping_confidence, mapping_status=mapping_status, extraction_status=status, warnings=item.warnings, extraction_method="vision", provider=extractor.provider.provider, model_name=extractor.provider.vision_model)
                    merged[merge_key] = answer
                    db.add(answer); answers.append(answer)
                    logger.info(
                        "EXTRACTION_SEGMENT detected=%s canonical=%s confidence=%s",
                        item.detected_question_number,
                        key,
                        item.extraction_confidence,
                    )
            if not answers: raise HTTPException(status_code=422, detail="No student answers were detected. Review the scanned document and try again.")
            source.status = AnswerSheetStatus.REVIEW_REQUIRED if any((a.extraction_confidence or 0) < REVIEW_THRESHOLD or a.question_id is None for a in answers) else AnswerSheetStatus.EXTRACTED
            source.processing_completed_at = datetime.now(timezone.utc); source.processing_error = None
            db.commit()
            for page in pages: db.refresh(page)
            for answer in answers: db.refresh(answer)
            return answers
        except Exception as error:
            db.rollback(); source = db.get(AnswerSheet, answer_sheet_id)
            if source:
                source.status = AnswerSheetStatus.FAILED; source.processing_error = str(error) if isinstance(error, HTTPException) else "Answer extraction failed"; source.processing_completed_at = datetime.now(timezone.utc); db.commit()
            if isinstance(error, HTTPException): raise
            if isinstance(error, AIProviderError): raise HTTPException(status_code=502, detail=str(error)) from error
            raise HTTPException(status_code=422, detail="Answer extraction failed") from error

    def list_answers(self, db: Session, submission_id: UUID, user: User) -> list[StudentAnswer]:
        submission = self._submission(db, submission_id, user)
        return list(db.scalars(select(StudentAnswer).where(StudentAnswer.student_submission_id == submission.id).options(selectinload(StudentAnswer.question)).order_by(StudentAnswer.created_at)))

    def delete_answer(self, db: Session, answer_id: UUID, user: User) -> None:
        answer = self._answer(db, answer_id, user)
        submission = answer.student_submission
        try:
            db.delete(answer)
            db.flush()
            remaining = db.scalar(select(StudentAnswer.id).where(StudentAnswer.student_submission_id == submission.id).limit(1))
            submission.status = SubmissionStatus.REVIEW_REQUIRED if remaining else SubmissionStatus.SUBMITTED
            db.commit()
        except Exception:
            db.rollback()
            raise

    def reset_extraction(self, db: Session, submission_id: UUID, user: User) -> None:
        submission = self._submission(db, submission_id, user)
        try:
            for answer in list(submission.student_answers):
                db.delete(answer)
            submission.status = SubmissionStatus.SUBMITTED
            submission.evaluation_status = "not_started"
            submission.finalized_at = None
            for link in submission.files:
                source = link.answer_sheet
                source.status = AnswerSheetStatus.UPLOADED
                source.processing_started_at = None
                source.processing_completed_at = None
                source.processing_error = None
            db.commit()
        except Exception:
            db.rollback()
            raise

    def reset_evaluation(self, db: Session, evaluation_id: UUID, user: User) -> None:
        evaluation = self._evaluation(db, evaluation_id, user)
        try:
            submission = evaluation.student_answer.student_submission
            db.delete(evaluation)
            submission.evaluation_status = "in_progress"
            submission.finalized_at = None
            submission.status = SubmissionStatus.REVIEW_REQUIRED
            db.commit()
        except Exception:
            db.rollback()
            raise

    def reset_submission_evaluations(self, db: Session, submission_id: UUID, user: User) -> None:
        submission = self._submission(db, submission_id, user)
        try:
            for answer in submission.student_answers:
                if answer.evaluation is not None:
                    db.delete(answer.evaluation)
            submission.status = SubmissionStatus.REVIEW_REQUIRED
            submission.evaluation_status = "not_started"
            submission.finalized_at = None
            db.commit()
        except Exception:
            db.rollback()
            raise

    def update_answer(self, db: Session, answer_id: UUID, *, question_id: UUID | None, answer_text: str, reviewed: bool, user: User) -> StudentAnswer:
        answer = self._answer(db, answer_id, user)
        if question_id:
            question = db.get(Question, question_id)
            if question is None or question.exam_id != answer.student_submission.exam_id: raise HTTPException(status_code=422, detail="Mapped question must belong to this exam")
            duplicate = db.scalar(select(StudentAnswer.id).where(StudentAnswer.student_submission_id == answer.student_submission_id, StudentAnswer.question_id == question_id, StudentAnswer.id != answer.id))
            if duplicate:
                raise HTTPException(status_code=409, detail="This submission already has an answer mapped to that question")
        changed = answer.question_id != question_id or answer.effective_answer_text != answer_text.strip()
        if changed and answer.evaluation is not None:
            db.delete(answer.evaluation)
        answer.question_id = question_id; answer.edited_text = answer_text.strip(); answer.reviewed = reviewed; answer.manually_corrected = True; answer.mapping_confidence = Decimal("1") if question_id else Decimal("0"); answer.mapping_status = "manual_mapped" if question_id else "unmapped"; answer.extraction_status = "reviewed" if reviewed else "review_required"
        if changed:
            answer.student_submission.evaluation_status = "in_progress"
            answer.student_submission.finalized_at = None
            answer.student_submission.status = SubmissionStatus.REVIEW_REQUIRED
        db.commit(); db.refresh(answer); return answer

    def evaluate(self, db: Session, answer_id: UUID, user: User) -> Evaluation:
        answer = self._answer(db, answer_id, user)
        if answer.question is None:
            raise HTTPException(status_code=422, detail="Map this answer to a question before evaluation")
        if not answer.effective_answer_text.strip():
            raise HTTPException(status_code=422, detail="Student answer text is empty")
        question = answer.question
        rubrics = list(question.rubric_criteria)
        references = {
            "model_answer": question.model_answer,
            "key_concepts": question.key_concepts,
            "acceptable_alternatives": question.acceptable_alternatives,
            "reference_solution": question.reference_solution,
            "marking_notes": question.marking_notes,
        }
        if not rubrics and not any(value and value.strip() for value in references.values()):
            raise HTTPException(status_code=422, detail="Add a model answer or marking criteria before evaluation")
        payload: dict[str, object] = {
            "question_number": question.question_number,
            "question_text": question.question_text,
            "maximum_marks": str(question.maximum_marks),
            "student_answer": answer.effective_answer_text,
            "extraction_confidence": str(answer.extraction_confidence or 0),
        }
        payload.update({key: value for key, value in references.items() if value and value.strip()})
        if rubrics:
            payload["rubric"] = [
                {
                    "id": str(rubric.id),
                    "criterion": rubric.criterion,
                    "description": rubric.description,
                    "maximum_marks": str(rubric.maximum_marks),
                }
                for rubric in rubrics
            ]
        try:
            evaluator = AnswerEvaluator()
            result = evaluator.evaluate(payload)
        except AIProviderError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
        maximum = question.maximum_marks
        warnings = list(dict.fromkeys(result.warnings))
        if result.max_marks != maximum:
            warnings.append("AI maximum marks differed from the configured question maximum; configured marks were used.")
        criteria: list[EvaluationCriterion] = []
        if rubrics:
            result_by_id = {str(item.rubric_criterion_id): item for item in result.criteria if item.rubric_criterion_id}
            total = Decimal("0")
            for rubric in rubrics:
                item = result_by_id.get(str(rubric.id))
                award = min(max(item.awarded_marks, Decimal("0")), rubric.maximum_marks) if item else Decimal("0")
                if total + award > maximum:
                    award = max(Decimal("0"), maximum - total)
                total += award
                if item is None:
                    warnings.append(f"AI omitted rubric criterion: {rubric.criterion}")
                criteria.append(
                    EvaluationCriterion(
                        rubric_criterion_id=rubric.id,
                        criterion_text_snapshot=rubric.criterion,
                        maximum_marks=rubric.maximum_marks,
                        awarded_marks=award,
                        evidence=item.evidence if item else "",
                        status=item.status if item else "missing",
                        reason=item.reason if item else "No criterion assessment was returned.",
                    )
                )
            ai_marks = min(total, maximum)
            if abs(result.marks_awarded - ai_marks) > Decimal("0.01"):
                warnings.append("AI overall marks did not match the rubric total; the deterministic rubric sum was used.")
            method = "rubric"
        else:
            ai_marks = min(max(result.marks_awarded, Decimal("0")), maximum)
            method = "overall_reference"
        review_required = (
            result.confidence < REVIEW_THRESHOLD
            or (answer.extraction_confidence is not None and answer.extraction_confidence < REVIEW_THRESHOLD)
            or bool(warnings)
        )
        current = answer.evaluation
        if current is None:
            current = Evaluation(student_answer_id=answer.id)
            db.add(current)
        else:
            current.criteria.clear()
        current.ai_marks = ai_marks
        current.manual_marks = None
        current.final_marks = ai_marks
        current.maximum_marks = maximum
        current.confidence = result.confidence
        current.strengths = result.strengths
        current.missing_points = result.missing_points
        current.feedback = result.feedback
        current.reasoning = result.reasoning
        current.faculty_remarks = None
        current.status = EvaluationStatus.REVIEW_REQUIRED if review_required else EvaluationStatus.AI_EVALUATED
        current.ai_provider = evaluator.provider.provider
        current.ai_model = evaluator.provider.model
        current.prompt_version = "evaluation_v1"
        current.evaluation_method = method
        current.warnings = list(dict.fromkeys(warnings))
        current.criteria = criteria
        answer.student_submission.evaluation_status = "awaiting_review"
        answer.student_submission.finalized_at = None
        answer.student_submission.status = SubmissionStatus.REVIEW_REQUIRED
        db.commit()
        db.refresh(current)
        return current

    def evaluate_submission(self, db: Session, submission_id: UUID, user: User) -> dict[str, object]:
        answers = self.list_answers(db, submission_id, user)
        mapped = [answer for answer in answers if answer.question_id]
        evaluations: list[Evaluation] = []
        failures: list[dict[str, object]] = []
        for answer in mapped:
            if answer.evaluation is not None:
                evaluations.append(answer.evaluation)
                continue
            try:
                evaluations.append(self.evaluate(db, answer.id, user))
            except HTTPException as error:
                failures.append({"student_answer_id": answer.id, "question_number": answer.question.question_number if answer.question else None, "detail": str(error.detail)})
        return {"total": len(mapped), "evaluated": len(evaluations), "failed": len(failures), "evaluations": evaluations, "failures": failures}

    def get_evaluation(self, db: Session, answer_id: UUID, user: User) -> Evaluation:
        answer = self._answer(db, answer_id, user)
        if not answer.evaluation: raise HTTPException(status_code=404, detail="Evaluation not found")
        return answer.evaluation

    def update_evaluation(self, db: Session, evaluation_id: UUID, payload: EvaluationUpdate, user: User, approve: bool = False) -> Evaluation:
        evaluation = self._evaluation(db, evaluation_id, user)
        criteria_by_id = {item.id: item for item in evaluation.criteria}
        for override in payload.criterion_marks:
            criterion = criteria_by_id.get(override.criterion_id)
            if criterion is None:
                raise HTTPException(status_code=422, detail="Criterion override does not belong to this evaluation")
            if override.faculty_awarded_marks > criterion.maximum_marks:
                raise HTTPException(status_code=422, detail="Faculty criterion marks cannot exceed criterion maximum marks")
            criterion.faculty_awarded_marks = override.faculty_awarded_marks
        manual_marks = payload.manual_marks
        if payload.criterion_marks:
            manual_marks = sum((item.final_awarded_marks for item in evaluation.criteria), Decimal("0"))
        if manual_marks is not None and manual_marks > evaluation.maximum_marks:
            raise HTTPException(status_code=422, detail="Faculty marks cannot exceed maximum marks")
        evaluation.manual_marks = manual_marks
        evaluation.final_marks = manual_marks if manual_marks is not None else evaluation.ai_marks
        evaluation.faculty_remarks = payload.faculty_remarks
        evaluation.status = EvaluationStatus.APPROVED if approve else EvaluationStatus.MANUALLY_MODIFIED
        evaluation.student_answer.student_submission.evaluation_status = "awaiting_review"
        evaluation.student_answer.student_submission.finalized_at = None
        db.commit(); db.refresh(evaluation); return evaluation

    def approve(self, db: Session, evaluation_id: UUID, user: User) -> Evaluation:
        evaluation = self._evaluation(db, evaluation_id, user)
        evaluation.manual_marks = None
        evaluation.final_marks = evaluation.ai_marks
        for criterion in evaluation.criteria:
            criterion.faculty_awarded_marks = None
        evaluation.status = EvaluationStatus.APPROVED
        evaluation.student_answer.student_submission.evaluation_status = "awaiting_review"
        evaluation.student_answer.student_submission.finalized_at = None
        db.commit(); db.refresh(evaluation); return evaluation

    def finalize_submission(self, db: Session, submission_id: UUID, user: User) -> StudentSubmission:
        submission = self._submission(db, submission_id, user)
        questions = list(db.scalars(select(Question).where(Question.exam_id == submission.exam_id).order_by(Question.sequence_order)))
        answers_by_question = {answer.question_id: answer for answer in submission.student_answers if answer.question_id}
        unresolved: list[str] = []
        for question in questions:
            answer = answers_by_question.get(question.id)
            if answer is None or answer.evaluation is None:
                unresolved.append(question.question_number)
            elif answer.evaluation.status not in {EvaluationStatus.APPROVED, EvaluationStatus.MANUALLY_MODIFIED}:
                unresolved.append(question.question_number)
        if unresolved:
            raise HTTPException(status_code=422, detail=f"Review or resolve every question before finalizing: {', '.join(unresolved)}")
        submission.evaluation_status = "finalized"
        submission.finalized_at = datetime.now(timezone.utc)
        submission.status = SubmissionStatus.COMPLETED
        db.commit(); db.refresh(submission); return submission

    def confirm_unanswered(self, db: Session, submission_id: UUID, question_id: UUID, user: User) -> Evaluation:
        submission = self._submission(db, submission_id, user)
        question = db.get(Question, question_id)
        if question is None or question.exam_id != submission.exam_id:
            raise HTTPException(status_code=422, detail="Question must belong to this submission's exam")
        existing = db.scalar(select(StudentAnswer).where(StudentAnswer.student_submission_id == submission.id, StudentAnswer.question_id == question.id))
        if existing is not None:
            raise HTTPException(status_code=409, detail="This submission already has an answer for that question")
        answer = StudentAnswer(
            student_submission_id=submission.id,
            question_id=question.id,
            detected_question_number=None,
            answer_text="",
            raw_text="",
            extraction_status="reviewed",
            warnings=["Faculty confirmed that no answer was detected."],
            extraction_method="faculty_unanswered",
            page_numbers=[],
            extraction_confidence=Decimal("1"),
            mapping_confidence=Decimal("1"),
            mapping_status="manual_mapped",
            manually_corrected=True,
            reviewed=True,
        )
        evaluation = Evaluation(
            student_answer=answer,
            ai_marks=Decimal("0"),
            manual_marks=Decimal("0"),
            final_marks=Decimal("0"),
            maximum_marks=question.maximum_marks,
            confidence=Decimal("1"),
            strengths=[],
            missing_points=["No answer submitted."],
            feedback="No answer detected; faculty confirmed zero marks.",
            reasoning="Deterministic faculty-confirmed unanswered question.",
            faculty_remarks="No answer / zero marks confirmed by faculty.",
            status=EvaluationStatus.MANUALLY_MODIFIED,
            evaluation_method="deterministic_unanswered",
            warnings=[],
            prompt_version="deterministic_unanswered_v1",
        )
        submission.evaluation_status = "awaiting_review"
        submission.finalized_at = None
        submission.status = SubmissionStatus.REVIEW_REQUIRED
        db.add_all([answer, evaluation]); db.commit(); db.refresh(evaluation); return evaluation

    def results(self, db: Session, exam_id: UUID, user: User):
        self.exams.get(db, exam_id, user)
        return list(db.scalars(select(StudentSubmission).where(StudentSubmission.exam_id == exam_id).options(selectinload(StudentSubmission.student), selectinload(StudentSubmission.student_answers).selectinload(StudentAnswer.question), selectinload(StudentSubmission.student_answers).selectinload(StudentAnswer.evaluation))))

    def _render_pages(self, source: AnswerSheet) -> list[bytes]:
        path = self.storage.absolute_path(source.file_path)
        if source.mime_type == "application/pdf":
            try:
                document = fitz.open(path); pages = []
                for page in document: pages.append(page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).tobytes("png"))
                document.close()
                if not pages: raise ValueError("PDF has no pages")
                return pages
            except Exception as error: raise HTTPException(status_code=422, detail="Unable to read the uploaded PDF") from error
        try:
            with Image.open(path) as image:
                from io import BytesIO
                buffer = BytesIO(); image.convert("RGB").save(buffer, format="PNG"); return [buffer.getvalue()]
        except Exception as error: raise HTTPException(status_code=422, detail="Unable to read the uploaded image") from error

    @staticmethod
    def _normal(value: str) -> str:
        value = value.strip().lower().rstrip(".:")
        value = re.sub(r"^question\s*", "", value)
        value = re.sub(r"^q\s*\.?(?=\d)", "", value)
        value = re.sub(r"\s+", "", value)
        match = re.fullmatch(r"(\d+)(?:\(?([a-zivx]+)\)?)?", value)
        if not match:
            return value
        number, child = match.groups()
        return f"q{number}({child})" if child else f"q{number}"
    def _submission(self, db, submission_id, user):
        value = db.get(StudentSubmission, submission_id)
        if not value: raise HTTPException(status_code=404, detail="Student submission not found")
        self.exams.get(db, value.exam_id, user); return value
    def _answer(self, db, answer_id, user):
        value = db.scalar(select(StudentAnswer).where(StudentAnswer.id == answer_id).options(selectinload(StudentAnswer.student_submission), selectinload(StudentAnswer.question).selectinload(Question.rubric_criteria), selectinload(StudentAnswer.evaluation).selectinload(Evaluation.criteria)))
        if not value: raise HTTPException(status_code=404, detail="Student answer not found")
        self.exams.get(db, value.student_submission.exam_id, user); return value
    def _evaluation(self, db, evaluation_id, user):
        value = db.scalar(select(Evaluation).where(Evaluation.id == evaluation_id).options(selectinload(Evaluation.student_answer).selectinload(StudentAnswer.student_submission)))
        if not value: raise HTTPException(status_code=404, detail="Evaluation not found")
        self.exams.get(db, value.student_answer.student_submission.exam_id, user); return value

    def page_preview_path(self, db: Session, answer_sheet_id: UUID, page_number: int, user: User) -> str:
        source = AnswerSheetService()._owned_sheet(db, answer_sheet_id, user)
        page = db.scalar(select(AnswerSheetPage).where(AnswerSheetPage.answer_sheet_id == source.id, AnswerSheetPage.page_number == page_number))
        if page is None:
            raise HTTPException(status_code=404, detail="Rendered answer-sheet page not found")
        return str(self.storage.absolute_path(page.image_path))
