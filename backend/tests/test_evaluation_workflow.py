from decimal import Decimal
from uuid import UUID

from app.ai.evaluator import AnswerEvaluator
from app.core.security import hash_password
from app.db.session import get_db
from app.models.evaluation import StudentAnswer
from app.models.submission import StudentSubmission
from app.models.user import User
from app.schemas.evaluation import AIEvaluationCriterion, AIEvaluationResult


def setup_exam(client, *, question_count: int = 1, with_reference: bool = True):
    generator = client.app.dependency_overrides[get_db](); db = next(generator)
    db.add(User(name="Evaluator", email="eval@example.com", password_hash=hash_password("password123"))); db.commit(); generator.close()
    assert client.post("/api/auth/login", json={"email": "eval@example.com", "password": "password123"}).status_code == 200
    exam = client.post("/api/exams", json={"name": "Evaluation Exam", "subject": "Maths", "class_name": "10", "total_marks": str(question_count * 5)}).json()
    student = client.post(f"/api/exams/{exam['id']}/students", json={"name": "Rahul", "roll_number": "101"}).json()
    questions = []
    for number in range(1, question_count + 1):
        questions.append(client.post(f"/api/exams/{exam['id']}/questions", json={
            "question_number": f"Q{number}", "question_text": f"Question {number}",
            "model_answer": f"Reference {number}" if with_reference else None,
            "maximum_marks": "5", "sequence_order": number,
        }).json())
    generator = client.app.dependency_overrides[get_db](); db = next(generator)
    submission = StudentSubmission(exam_id=UUID(exam["id"]), student_id=UUID(student["id"])); db.add(submission); db.flush()
    answers = []
    for question in questions:
        answer = StudentAnswer(student_submission_id=submission.id, question_id=UUID(question["id"]), detected_question_number=question["question_number"], answer_text="raw answer", raw_text="raw answer", edited_text="faculty corrected answer", page_numbers=[1], extraction_confidence=Decimal(".9"), mapping_confidence=Decimal("1"), mapping_status="auto_mapped", extraction_status="extracted")
        db.add(answer); answers.append(answer)
    db.commit(); result = (exam, student, questions, submission.id, [answer.id for answer in answers]); generator.close(); return result


def overall_result(marks: str = "4") -> AIEvaluationResult:
    return AIEvaluationResult(marks_awarded=Decimal(marks), max_marks=Decimal("5"), confidence=Decimal(".9"), feedback="Semantically correct with minor omission", reasoning="Compared against reference data")


def test_no_rubric_reference_evaluation_uses_edited_text_and_reuses_current_row(client, monkeypatch) -> None:
    exam, _, _, _, answer_ids = setup_exam(client)
    payloads = []
    monkeypatch.setattr(AnswerEvaluator, "evaluate", lambda self, payload: payloads.append(payload) or overall_result("4"))
    first = client.post(f"/api/student-answers/{answer_ids[0]}/evaluate")
    assert first.status_code == 200, first.text
    assert first.json()["evaluation_method"] == "overall_reference"
    assert first.json()["ai_marks"] == "4.00"
    assert payloads[0]["student_answer"] == "faculty corrected answer"
    second = client.post(f"/api/student-answers/{answer_ids[0]}/evaluate")
    assert second.status_code == 200 and second.json()["id"] == first.json()["id"]
    assert len(client.get(f"/api/exams/{exam['id']}/results").json()) == 1


def test_evaluation_requires_reference_and_evaluate_all_keeps_partial_success(client, monkeypatch) -> None:
    _, _, questions, submission_id, answer_ids = setup_exam(client, question_count=2, with_reference=False)
    first = client.put(f"/api/questions/{questions[0]['id']}", json={**questions[0], "model_answer": "Reference one"})
    assert first.status_code == 200, first.text
    monkeypatch.setattr(AnswerEvaluator, "evaluate", lambda self, payload: overall_result("3"))
    missing = client.post(f"/api/student-answers/{answer_ids[1]}/evaluate")
    assert missing.status_code == 422 and "model answer or marking criteria" in missing.json()["detail"]
    summary = client.post(f"/api/student-submissions/{submission_id}/evaluate")
    assert summary.status_code == 200, summary.text
    assert (summary.json()["total"], summary.json()["evaluated"], summary.json()["failed"]) == (2, 1, 1)


def test_rubric_total_faculty_override_accept_finalize_results_and_exports(client, monkeypatch) -> None:
    exam, _, questions, submission_id, answer_ids = setup_exam(client)
    first_rubric = client.post(f"/api/questions/{questions[0]['id']}/rubric-criteria", json={"criterion": "Method", "maximum_marks": "2", "sequence_order": 1}).json()
    second_rubric = client.post(f"/api/questions/{questions[0]['id']}/rubric-criteria", json={"criterion": "Result", "maximum_marks": "3", "sequence_order": 2}).json()
    monkeypatch.setattr(AnswerEvaluator, "evaluate", lambda self, payload: AIEvaluationResult(
        marks_awarded=Decimal("5"), max_marks=Decimal("5"), confidence=Decimal(".9"), feedback="Review",
        criteria=[
            AIEvaluationCriterion(rubric_criterion_id=UUID(first_rubric["id"]), criterion_text="Method", maximum_marks=Decimal("2"), awarded_marks=Decimal("3"), status="correct", reason="Method shown"),
            AIEvaluationCriterion(rubric_criterion_id=UUID(second_rubric["id"]), criterion_text="Result", maximum_marks=Decimal("3"), awarded_marks=Decimal("1"), status="partial", reason="Incomplete result"),
        ],
    ))
    evaluated = client.post(f"/api/student-answers/{answer_ids[0]}/evaluate")
    assert evaluated.status_code == 200, evaluated.text
    value = evaluated.json(); assert value["evaluation_method"] == "rubric" and value["ai_marks"] == "3.00"
    assert value["status"] == "review_required" and value["warnings"]
    criteria = value["criteria"]
    override = client.patch(f"/api/evaluations/{value['id']}", json={"manual_marks": "5", "faculty_remarks": "Method correct; result partially correct.", "criterion_marks": [
        {"criterion_id": criteria[0]["id"], "faculty_awarded_marks": "2"},
        {"criterion_id": criteria[1]["id"], "faculty_awarded_marks": "2"},
    ]})
    assert override.status_code == 200, override.text
    assert override.json()["ai_marks"] == "3.00" and override.json()["manual_marks"] == "4.00" and override.json()["final_marks"] == "4.00"
    assert client.patch(f"/api/evaluations/{value['id']}", json={"manual_marks": "6"}).status_code == 422
    finalized = client.post(f"/api/student-submissions/{submission_id}/finalize")
    assert finalized.status_code == 200 and finalized.json()["evaluation_status"] == "finalized"
    rows = client.get(f"/api/exams/{exam['id']}/results").json()
    assert len(rows) == 1 and rows[0]["total_marks"] == "4.00" and rows[0]["maximum_marks"] == "5.00" and rows[0]["percentage"] == "80.00"
    assert client.get(f"/api/exams/{exam['id']}/results.csv").status_code == 200
    assert client.get(f"/api/exams/{exam['id']}/results.xlsx").status_code == 200
    report = client.get(f"/api/student-submissions/{submission_id}/report")
    assert report.status_code == 200 and report.json()["questions"][0]["faculty_remarks"]
    assert client.post(f"/api/student-submissions/{submission_id}/reset-evaluations").status_code == 204
    assert client.get(f"/api/exams/{exam['id']}/results").json() == []


def test_unmapped_answer_and_cross_owner_evaluation_are_rejected(client, monkeypatch) -> None:
    _, _, _, _, answer_ids = setup_exam(client)
    generator = client.app.dependency_overrides[get_db](); db = next(generator)
    answer = db.get(StudentAnswer, answer_ids[0]); answer.question_id = None; db.commit(); generator.close()
    monkeypatch.setattr(AnswerEvaluator, "evaluate", lambda self, payload: overall_result())
    assert client.post(f"/api/student-answers/{answer_ids[0]}/evaluate").status_code == 422
    generator = client.app.dependency_overrides[get_db](); db = next(generator)
    db.add(User(name="Other", email="other@example.com", password_hash=hash_password("password123"))); db.commit(); generator.close()
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={"email": "other@example.com", "password": "password123"}).status_code == 200
    assert client.post(f"/api/student-answers/{answer_ids[0]}/evaluate").status_code == 404


def test_reference_change_marks_evaluation_stale_and_invalidates_result(client, monkeypatch) -> None:
    exam, _, questions, submission_id, answer_ids = setup_exam(client)
    monkeypatch.setattr(AnswerEvaluator, "evaluate", lambda self, payload: overall_result("4"))
    evaluated = client.post(f"/api/student-answers/{answer_ids[0]}/evaluate").json()
    assert client.post(f"/api/evaluations/{evaluated['id']}/approve").status_code == 200
    assert client.post(f"/api/student-submissions/{submission_id}/finalize").status_code == 200
    question = questions[0]
    changed = client.put(f"/api/questions/{question['id']}", json={
        "question_number": question["question_number"], "question_text": question["question_text"],
        "model_answer": "Changed reference", "key_concepts": None, "acceptable_alternatives": None,
        "reference_solution": None, "marking_notes": None, "maximum_marks": question["maximum_marks"],
        "sequence_order": question["sequence_order"], "parent_question_id": question["parent_question_id"],
    })
    assert changed.status_code == 200, changed.text
    assert client.get(f"/api/student-answers/{answer_ids[0]}/evaluation").json()["status"] == "stale"
    assert client.get(f"/api/exams/{exam['id']}/results").json() == []
    finalized = client.post(f"/api/student-submissions/{submission_id}/finalize")
    assert finalized.status_code == 422


def test_faculty_can_confirm_missing_question_as_unanswered(client, monkeypatch) -> None:
    exam, _, questions, submission_id, answer_ids = setup_exam(client, question_count=2)
    assert client.delete(f"/api/student-answers/{answer_ids[1]}").status_code == 204
    monkeypatch.setattr(AnswerEvaluator, "evaluate", lambda self, payload: overall_result("4"))
    evaluated = client.post(f"/api/student-answers/{answer_ids[0]}/evaluate").json()
    assert client.post(f"/api/evaluations/{evaluated['id']}/approve").status_code == 200
    unanswered = client.post(f"/api/student-submissions/{submission_id}/questions/{questions[1]['id']}/confirm-unanswered")
    assert unanswered.status_code == 200, unanswered.text
    assert unanswered.json()["evaluation_method"] == "deterministic_unanswered"
    assert unanswered.json()["final_marks"] == "0.00"
    assert client.post(f"/api/student-submissions/{submission_id}/finalize").status_code == 200
    result = client.get(f"/api/exams/{exam['id']}/results").json()[0]
    assert result["total_marks"] == "4.00" and result["maximum_marks"] == "10.00"
