from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Response, status
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, DbSession
from app.schemas.evaluation import (
    EvaluationRead,
    EvaluationUpdate,
    StudentAnswerRead,
    StudentAnswerUpdate,
    StudentResultRead,
    SubmissionEvaluationSummary,
    SubmissionFinalizeRead,
)
from app.services.evaluation_service import EvaluationService

answer_router = APIRouter(prefix="/api/student-answers", tags=["student answers"])
evaluation_router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])
submission_router = APIRouter(prefix="/api/student-submissions", tags=["evaluations"])
exam_router = APIRouter(prefix="/api/exams/{exam_id}", tags=["results"])


@answer_router.get("/{answer_id}", response_model=StudentAnswerRead)
def get_answer(answer_id: UUID, db: DbSession, user: CurrentUser):
    return EvaluationService()._answer(db, answer_id, user)

@answer_router.put("/{answer_id}", response_model=StudentAnswerRead)
def update_answer(answer_id: UUID, payload: StudentAnswerUpdate, db: DbSession, user: CurrentUser):
    return EvaluationService().update_answer(db, answer_id, question_id=payload.question_id, answer_text=payload.answer_text, reviewed=payload.reviewed, user=user)

@answer_router.delete("/{answer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_answer(answer_id: UUID, db: DbSession, user: CurrentUser):
    EvaluationService().delete_answer(db, answer_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@answer_router.post("/{answer_id}/evaluate", response_model=EvaluationRead)
def evaluate_answer(answer_id: UUID, db: DbSession, user: CurrentUser):
    return EvaluationService().evaluate(db, answer_id, user)

@answer_router.get("/{answer_id}/evaluation", response_model=EvaluationRead)
def get_evaluation(answer_id: UUID, db: DbSession, user: CurrentUser):
    return EvaluationService().get_evaluation(db, answer_id, user)

@evaluation_router.put("/{evaluation_id}", response_model=EvaluationRead)
def update_evaluation(evaluation_id: UUID, payload: EvaluationUpdate, db: DbSession, user: CurrentUser):
    return EvaluationService().update_evaluation(db, evaluation_id, payload, user)

@evaluation_router.patch("/{evaluation_id}", response_model=EvaluationRead)
def patch_evaluation(evaluation_id: UUID, payload: EvaluationUpdate, db: DbSession, user: CurrentUser):
    return EvaluationService().update_evaluation(db, evaluation_id, payload, user)

@evaluation_router.post("/{evaluation_id}/approve", response_model=EvaluationRead)
def approve_evaluation(evaluation_id: UUID, db: DbSession, user: CurrentUser):
    return EvaluationService().approve(db, evaluation_id, user)

@evaluation_router.post("/{evaluation_id}/reevaluate", response_model=EvaluationRead)
def reevaluate(evaluation_id: UUID, db: DbSession, user: CurrentUser):
    service = EvaluationService(); evaluation = service._evaluation(db, evaluation_id, user); return service.evaluate(db, evaluation.student_answer_id, user)

@evaluation_router.delete("/{evaluation_id}", status_code=status.HTTP_204_NO_CONTENT)
def reset_evaluation(evaluation_id: UUID, db: DbSession, user: CurrentUser):
    EvaluationService().reset_evaluation(db, evaluation_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@submission_router.get("/{submission_id}/answers", response_model=list[StudentAnswerRead])
def list_answers(submission_id: UUID, db: DbSession, user: CurrentUser):
    return EvaluationService().list_answers(db, submission_id, user)

@submission_router.post("/{submission_id}/evaluate", response_model=SubmissionEvaluationSummary)
def evaluate_submission(submission_id: UUID, db: DbSession, user: CurrentUser):
    return EvaluationService().evaluate_submission(db, submission_id, user)

@submission_router.post("/{submission_id}/finalize", response_model=SubmissionFinalizeRead)
def finalize_submission(submission_id: UUID, db: DbSession, user: CurrentUser):
    submission = EvaluationService().finalize_submission(db, submission_id, user)
    return {"submission_id": submission.id, "evaluation_status": submission.evaluation_status, "finalized_at": submission.finalized_at}

@submission_router.post("/{submission_id}/questions/{question_id}/confirm-unanswered", response_model=EvaluationRead)
def confirm_unanswered(submission_id: UUID, question_id: UUID, db: DbSession, user: CurrentUser):
    return EvaluationService().confirm_unanswered(db, submission_id, question_id, user)

@submission_router.post("/{submission_id}/reset-extraction", status_code=status.HTTP_204_NO_CONTENT)
def reset_extraction(submission_id: UUID, db: DbSession, user: CurrentUser):
    EvaluationService().reset_extraction(db, submission_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@submission_router.post("/{submission_id}/reset-evaluations", status_code=status.HTTP_204_NO_CONTENT)
def reset_evaluations(submission_id: UUID, db: DbSession, user: CurrentUser):
    EvaluationService().reset_submission_evaluations(db, submission_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@submission_router.get("/{submission_id}/report")
def submission_report(submission_id: UUID, db: DbSession, user: CurrentUser):
    submission = EvaluationService()._submission(db, submission_id, user)
    answers = sorted((item for item in submission.student_answers if item.question_id), key=lambda item: item.question.sequence_order if item.question else 0)
    return {
        "exam": {"id": submission.exam.id, "name": submission.exam.name, "subject": submission.exam.subject, "class_name": submission.exam.class_name},
        "student": {"id": submission.student.id, "name": submission.student.name, "roll_number": submission.student.roll_number},
        "submission_id": submission.id,
        "evaluation_status": submission.evaluation_status,
        "finalized_at": submission.finalized_at,
        "evaluator": user.name,
        "questions": [
            {
                "question_number": answer.question.question_number,
                "question_text": answer.question.question_text,
                "maximum_marks": answer.question.maximum_marks,
                "student_answer": answer.effective_answer_text,
                "ai_marks": answer.evaluation.ai_marks if answer.evaluation else None,
                "faculty_marks": answer.evaluation.manual_marks if answer.evaluation else None,
                "final_marks": answer.evaluation.final_marks if answer.evaluation else None,
                "justification": answer.evaluation.feedback if answer.evaluation else None,
                "faculty_remarks": answer.evaluation.faculty_remarks if answer.evaluation else None,
                "status": answer.evaluation.status.value if answer.evaluation else "not_evaluated",
            }
            for answer in answers
        ],
    }

@exam_router.get("/results", response_model=list[StudentResultRead])
def results(exam_id: UUID, db: DbSession, user: CurrentUser):
    submissions = EvaluationService().results(db, exam_id, user)
    rows = []
    from decimal import Decimal
    from sqlalchemy import select
    from app.models.question import Question
    exam_questions = list(db.scalars(select(Question).where(Question.exam_id == exam_id).order_by(Question.sequence_order)))
    latest_by_student = {}
    for sub in submissions:
        if any(answer.evaluation is not None and answer.evaluation.status.value != "stale" for answer in sub.student_answers):
            current = latest_by_student.get(sub.student_id)
            if current is None or sub.created_at > current.created_at:
                latest_by_student[sub.student_id] = sub
    for sub in latest_by_student.values():
        evaluations_by_question = {}
        for answer in sub.student_answers:
            if not answer.question or not answer.evaluation or answer.evaluation.status.value == "stale": continue
            evaluation = answer.evaluation
            evaluations_by_question[answer.question_id] = evaluation
        values = []
        for question in exam_questions:
            evaluation = evaluations_by_question.get(question.id)
            values.append({"question_number": question.question_number, "question_id": question.id, "ai_marks": evaluation.ai_marks if evaluation else None, "faculty_marks": evaluation.manual_marks if evaluation else None, "final_marks": evaluation.final_marks if evaluation else None, "maximum_marks": question.maximum_marks, "status": evaluation.status.value if evaluation else "not_evaluated"})
        total = sum((item["final_marks"] or Decimal("0") for item in values), Decimal("0"))
        maximum = sum((item["maximum_marks"] for item in values), Decimal("0"))
        percentage = (total / maximum * 100).quantize(Decimal("0.01")) if maximum else Decimal("0.00")
        rows.append({"submission_id": sub.id, "student_id": sub.student_id, "student_name": sub.student.name, "roll_number": sub.student.roll_number, "total_marks": total, "maximum_marks": maximum, "percentage": percentage, "status": sub.evaluation_status, "questions": values})
    return rows


@exam_router.get("/submissions")
def submissions(exam_id: UUID, db: DbSession, user: CurrentUser):
    values = EvaluationService().results(db, exam_id, user)
    latest_by_student = {}
    for item in values:
        if not item.files and not item.student_answers:
            continue
        current = latest_by_student.get(item.student_id)
        if current is None or item.created_at > current.created_at:
            latest_by_student[item.student_id] = item
    return [{"id": item.id, "student_id": item.student_id, "student_name": item.student.name, "roll_number": item.student.roll_number, "status": item.status.value, "evaluation_status": item.evaluation_status, "finalized_at": item.finalized_at, "answer_sheet_id": item.files[0].answer_sheet_id if item.files else None} for item in sorted(latest_by_student.values(), key=lambda value: value.created_at, reverse=True)]

@exam_router.get("/results.csv")
def results_csv(exam_id: UUID, db: DbSession, user: CurrentUser):
    import csv
    import io
    rows = results(exam_id, db, user); out = io.StringIO(); writer = csv.writer(out)
    question_numbers = [item["question_number"] for item in rows[0]["questions"]] if rows else []
    writer.writerow(["student_name", "roll_number", *question_numbers, "total_marks", "maximum_marks", "percentage", "status"])
    for row in rows:
        marks = {item["question_number"]: item["final_marks"] for item in row["questions"]}
        writer.writerow([row["student_name"], row["roll_number"] or "", *[marks.get(number) if marks.get(number) is not None else "" for number in question_numbers], row["total_marks"], row["maximum_marks"], row["percentage"], row["status"]])
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="exam-{exam_id}-results.csv"'})


@exam_router.get("/results.xlsx")
def results_xlsx(exam_id: UUID, db: DbSession, user: CurrentUser):
    from io import BytesIO
    from openpyxl import Workbook
    rows = results(exam_id, db, user)
    question_numbers = [item["question_number"] for item in rows[0]["questions"]] if rows else []
    workbook = Workbook(); sheet = workbook.active; sheet.title = "Results"
    sheet.append(["Student", "Roll", *question_numbers, "Total", "Maximum", "Percentage", "Status"])
    for row in rows:
        marks = {item["question_number"]: item["final_marks"] for item in row["questions"]}
        sheet.append([row["student_name"], row["roll_number"] or "", *[float(marks[number]) if marks.get(number) is not None else None for number in question_numbers], float(row["total_marks"]), float(row["maximum_marks"]), float(row["percentage"]), row["status"]])
    output = BytesIO(); workbook.save(output); output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="exam-{exam_id}-results.xlsx"'})
