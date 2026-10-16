import pytest
from uuid import UUID
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User
from app.models.answer_sheet import AnswerSheet, AnswerSheetStatus
from app.models.student import Student
from app.models.submission import StudentSubmission
from app.services.submission_service import SubmissionService
def seed_user(client) -> None:
    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    db.add(User(name="Ada Evaluator", email="ada@example.com", password_hash=hash_password("correct-horse")))
    db.commit()
    generator.close()
def login(client) -> None:
    assert client.post("/api/auth/login", json={"email": "ada@example.com", "password": "correct-horse"}).status_code == 200
def test_health(client) -> None:
    assert client.get("/health").json() == {"status": "ok"}
def test_authentication_and_exam_crud(client) -> None:
    seed_user(client)
    assert client.get("/api/exams").status_code == 401
    login(client)
    assert client.get("/api/auth/me").json()["email"] == "ada@example.com"
    payload = {"name": "Biology Midterm", "subject": "Biology", "class_name": "Grade 10", "total_marks": "25.00"}
    created = client.post("/api/exams", json=payload)
    assert created.status_code == 201
    exam = created.json()
    assert exam["total_marks"] == "25.00"
    updated = client.put(f"/api/exams/{exam['id']}", json={**payload, "name": "Biology Final", "status": "configured"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Biology Final"
    assert len(client.get("/api/exams").json()) == 1
    assert client.delete(f"/api/exams/{exam['id']}").status_code == 204
    assert client.get("/api/exams").json() == []
def test_question_and_rubric_crud_with_mark_validation(client) -> None:
    seed_user(client); login(client)
    exam = client.post("/api/exams", json={"name": "Physics", "subject": "Physics", "class_name": "Grade 9", "total_marks": "20"}).json()
    payload = {"question_number": "1(a)", "question_text": "Define velocity.", "model_answer": "Rate of displacement.", "maximum_marks": "2.00", "sequence_order": 1}
    question = client.post(f"/api/exams/{exam['id']}/questions", json=payload)
    assert question.status_code == 201
    question_id = question.json()["id"]
    criterion = client.post(f"/api/questions/{question_id}/rubric-criteria", json={"criterion": "Correct definition", "maximum_marks": "2.00", "sequence_order": 1})
    assert criterion.status_code == 201
    assert client.get(f"/api/questions/{question_id}/rubric-criteria").json()[0]["maximum_marks"] == "2.00"
    updated_question = client.put(
        f"/api/questions/{question_id}",
        json={**payload, "question_number": "1", "question_text": "Define scalar velocity.", "sequence_order": 2},
    )
    assert updated_question.status_code == 200
    assert updated_question.json()["question_text"] == "Define scalar velocity."
    assert len(client.get(f"/api/questions/{question_id}/rubric-criteria").json()) == 1
    criterion_id = criterion.json()["id"]
    updated_criterion = client.put(
        f"/api/rubric-criteria/{criterion_id}",
        json={"criterion": "Precise definition", "description": "Includes displacement", "maximum_marks": "2.00", "sequence_order": 2},
    )
    assert updated_criterion.status_code == 200
    assert updated_criterion.json()["criterion"] == "Precise definition"
    excessive_criterion = client.post(
        f"/api/questions/{question_id}/rubric-criteria",
        json={"criterion": "Over maximum", "maximum_marks": "0.50", "sequence_order": 3},
    )
    assert excessive_criterion.status_code == 422
    reduced_question = client.put(
        f"/api/questions/{question_id}",
        json={**payload, "question_number": "1", "maximum_marks": "1.00", "sequence_order": 2},
    )
    assert reduced_question.status_code == 422
    assert client.delete(f"/api/rubric-criteria/{criterion_id}").status_code == 204
    assert client.get(f"/api/questions/{question_id}/rubric-criteria").json() == []
    assert client.post(f"/api/exams/{exam['id']}/questions", json={**payload, "question_number": "2", "sequence_order": 2, "maximum_marks": "-1"}).status_code == 422
    assert client.post(f"/api/exams/{exam['id']}/questions", json={**payload, "sequence_order": 2}).status_code == 409


def create_exam(client, name: str = "Upload Exam") -> dict:
    response = client.post("/api/exams", json={"name": name, "subject": "Science", "class_name": "Grade 8", "total_marks": "20"})
    assert response.status_code == 201
    return response.json()


def create_student(client, exam_id: str, name: str = "Sam Student", roll_number: str | None = "R-01") -> dict:
    response = client.post(f"/api/exams/{exam_id}/students", json={"name": name, "roll_number": roll_number})
    assert response.status_code == 201
    return response.json()


def test_student_crud_and_duplicate_roll_number(client) -> None:
    seed_user(client); login(client)
    exam = create_exam(client)
    student = create_student(client, exam["id"])
    assert client.get(f"/api/exams/{exam['id']}/students").json()[0]["id"] == student["id"]
    assert client.get(f"/api/students/{student['id']}").status_code == 200
    updated = client.put(f"/api/students/{student['id']}", json={"name": "Sam Updated", "roll_number": "R-02", "external_id": "EXT-1"})
    assert updated.status_code == 200
    assert updated.json()["roll_number"] == "R-02"
    assert client.post(f"/api/exams/{exam['id']}/students", json={"name": "Duplicate", "roll_number": "R-02"}).status_code == 409
    assert client.delete(f"/api/students/{student['id']}").status_code == 204
    assert client.get(f"/api/exams/{exam['id']}/students").json() == []


def test_answer_sheet_upload_validation_listing_and_cleanup(client) -> None:
    seed_user(client); login(client)
    exam = create_exam(client)
    student = create_student(client, exam["id"])
    endpoint = f"/api/exams/{exam['id']}/answer-sheets"
    valid = client.post(endpoint, data={"student_id": student["id"]}, files={"file": ("sheet.pdf", b"PDF!", "application/pdf")})
    assert valid.status_code == 201, valid.text
    sheet = valid.json()
    assert sheet["status"] == "uploaded"
    assert sheet["student_name"] == "Sam Student"
    assert len(client.get(endpoint).json()) == 1
    assert client.get(f"/api/answer-sheets/{sheet['id']}").status_code == 200
    from pathlib import Path
    assert any(item.is_file() for item in Path("/private/tmp/answer-evaluator-test-storage").rglob("*"))
    assert client.post(endpoint, data={"student_id": student["id"]}, files={"file": ("bad.txt", b"text", "text/plain")}).status_code == 422
    assert client.post(endpoint, data={"student_id": student["id"]}, files={"file": ("empty.pdf", b"", "application/pdf")}).status_code == 422
    assert client.post(endpoint, data={"student_id": student["id"]}, files={"file": ("large.pdf", b"123456789", "application/pdf")}).status_code == 422
    assert client.delete(f"/api/answer-sheets/{sheet['id']}").status_code == 204
    assert not any(item.is_file() for item in Path("/private/tmp/answer-evaluator-test-storage").rglob("*"))


def test_student_and_answer_sheet_ownership_enforcement(client) -> None:
    seed_user(client); login(client)
    first_exam = create_exam(client, "First evaluator exam")
    first_student = create_student(client, first_exam["id"])
    sheet = client.post(f"/api/exams/{first_exam['id']}/answer-sheets", data={"student_id": first_student["id"]}, files={"file": ("sheet.pdf", b"PDF!", "application/pdf")}).json()
    generator = client.app.dependency_overrides[get_db](); db = next(generator)
    db.add(User(name="Other", email="other@example.com", password_hash=hash_password("correct-horse"))); db.commit(); generator.close()
    assert client.post("/api/auth/login", json={"email": "other@example.com", "password": "correct-horse"}).status_code == 200
    assert client.get(f"/api/exams/{first_exam['id']}/students").status_code == 404
    assert client.get(f"/api/answer-sheets/{sheet['id']}").status_code == 404
    other_exam = create_exam(client, "Other evaluator exam")
    assert client.post(f"/api/exams/{other_exam['id']}/answer-sheets", data={"student_id": first_student["id"]}, files={"file": ("sheet.pdf", b"PDF!", "application/pdf")}).status_code == 404


def test_submission_file_invariants_and_submission_history(client) -> None:
    seed_user(client); login(client)
    exam = create_exam(client, "Submission domain exam")
    first_student_data = create_student(client, exam["id"], "First student", "A-1")
    second_student_data = create_student(client, exam["id"], "Second student", "A-2")
    other_exam = create_exam(client, "Other submission exam")
    other_student_data = create_student(client, other_exam["id"], "Other exam student", "B-1")
    generator = client.app.dependency_overrides[get_db](); db = next(generator)
    exam_id = UUID(exam["id"])
    first_student = db.get(Student, UUID(first_student_data["id"]))
    second_student = db.get(Student, UUID(second_student_data["id"]))
    other_student = db.get(Student, UUID(other_student_data["id"]))
    source = AnswerSheet(exam_id=exam_id, student_id=None, original_filename="combined.pdf", stored_filename="combined-test.pdf", file_path="answer-sheets/combined-test.pdf", mime_type="application/pdf", file_size=10, status=AnswerSheetStatus.UPLOADED)
    extra_source = AnswerSheet(exam_id=exam_id, student_id=second_student.id, original_filename="extra.pdf", stored_filename="extra-test.pdf", file_path="answer-sheets/extra-test.pdf", mime_type="application/pdf", file_size=10, status=AnswerSheetStatus.UPLOADED)
    db.add_all([source, extra_source]); db.flush()
    service = SubmissionService()
    with pytest.raises(Exception):
        service.create(db, exam_id=exam_id, student=other_student)
    first_submission = service.create(db, exam_id=exam_id, student=first_student)
    service.link_source(db, submission=first_submission, source_upload=source, sequence_order=1, page_start=1, page_end=2)
    service.link_source(db, submission=first_submission, source_upload=extra_source, sequence_order=2, file_role="supplementary")
    second_submission = service.create(db, exam_id=exam_id, student=second_student)
    service.link_source(db, submission=second_submission, source_upload=source, sequence_order=1, page_start=3, page_end=4)
    db.commit()
    assert source.student_id is None
    assert len(first_submission.files) == 2
    assert len(second_submission.files) == 1
    with pytest.raises(Exception):
        service.link_source(db, submission=first_submission, source_upload=source, sequence_order=3, page_start=1, page_end=2)
    db.rollback()
    with pytest.raises(Exception):
        service.link_source(db, submission=first_submission, source_upload=source, sequence_order=3, page_start=5, page_end=4)
    db.rollback()
    service.reassign(db, submission=first_submission, student=second_student)
    replacement = service.create(db, exam_id=exam_id, student=second_student, replaces_submission_id=first_submission.id)
    db.commit()
    assert db.get(StudentSubmission, first_submission.id) is not None
    assert replacement.replaces_submission_id == first_submission.id
    db.delete(second_student); db.commit()
    source_after_student_delete = db.get(AnswerSheet, extra_source.id)
    assert source_after_student_delete is not None
    assert source_after_student_delete.student_id is None
    generator.close()


def test_question_paper_upload_delete_and_import_preserves_manual_questions(client) -> None:
    seed_user(client); login(client)
    exam = create_exam(client, "Question paper exam")
    manual = client.post(f"/api/exams/{exam['id']}/questions", json={"question_number":"1", "question_text":"Manual", "maximum_marks":"2", "sequence_order":0})
    assert manual.status_code == 201
    endpoint = f"/api/exams/{exam['id']}/question-paper"
    uploaded = client.post(endpoint, files={"file": ("paper.pdf", b"PDF!", "application/pdf")})
    assert uploaded.status_code == 201, uploaded.text
    paper = uploaded.json()
    assert client.post(endpoint, files={"file": ("bad.txt", b"x", "text/plain")}).status_code == 422
    imported = client.post(endpoint + "/import", json={"questions":[
        {"question_number":"1", "question_text":"Conflict", "maximum_marks":"2", "parent_question_number":None, "sequence_order":0, "confidence":0.9, "warnings":[]},
        {"question_number":"2(a)", "question_text":"Imported", "maximum_marks":"3", "parent_question_number":None, "sequence_order":1, "confidence":0.9, "warnings":[]},
    ]})
    assert imported.status_code == 200
    assert imported.json()["skipped_conflicts"] == ["Q1"]
    questions = client.get(f"/api/exams/{exam['id']}/questions").json()
    assert {item["question_number"] for item in questions} == {"1", "Q2(a)"}
    assert client.delete(endpoint).status_code == 204
    assert client.get(endpoint).json() is None
    from pathlib import Path
    assert not any(item.name == paper["stored_filename"] for item in Path("/private/tmp/answer-evaluator-test-storage").rglob("*"))


def test_question_paper_imports_reference_fields_and_rubric_criteria(client) -> None:
    seed_user(client); login(client)
    exam = create_exam(client, "Reference import")
    endpoint = f"/api/exams/{exam['id']}/question-paper/import"
    response = client.post(endpoint, json={"questions": [
        {
            "question_number": "Q1",
            "question_text": "Explain photosynthesis.",
            "maximum_marks": "3",
            "parent_question_number": None,
            "sequence_order": 1,
            "confidence": 0.95,
            "warnings": [],
            "model_answer": "Photosynthesis is the process by which green plants make food using sunlight.",
            "key_concepts": "chlorophyll; sunlight; carbon dioxide; water; glucose; oxygen",
            "acceptable_alternatives": "Credit equivalent wording about food preparation in green plants.",
            "reference_solution": "CO2 and water are converted into glucose and oxygen in the presence of sunlight and chlorophyll.",
            "marking_notes": "Award marks for concept, inputs, and products.",
            "rubric_criteria": [
                {"criterion": "Defines photosynthesis", "maximum_marks": "1", "description": "Mentions green plants make food."},
                {"criterion": "Lists required inputs", "maximum_marks": "1", "description": "Sunlight, water, and carbon dioxide."},
                {"criterion": "Lists products", "maximum_marks": "1", "description": "Glucose/food and oxygen."},
            ],
        }
    ]})
    assert response.status_code == 200, response.text
    assert response.json()["skipped_conflicts"] == []
    questions = client.get(f"/api/exams/{exam['id']}/questions").json()
    assert len(questions) == 1
    question = questions[0]
    assert question["model_answer"].startswith("Photosynthesis is the process")
    assert "chlorophyll" in question["key_concepts"]
    assert "equivalent wording" in question["acceptable_alternatives"]
    assert "CO2 and water" in question["reference_solution"]
    assert "Award marks" in question["marking_notes"]
    criteria = client.get(f"/api/questions/{question['id']}/rubric-criteria").json()
    assert [(item["criterion"], item["maximum_marks"]) for item in criteria] == [
        ("Defines photosynthesis", "1.00"),
        ("Lists required inputs", "1.00"),
        ("Lists products", "1.00"),
    ]

    invalid = client.post(endpoint, json={"questions": [
        {
            "question_number": "Q2",
            "question_text": "Invalid rubric total.",
            "maximum_marks": "2",
            "parent_question_number": None,
            "sequence_order": 2,
            "confidence": 0.9,
            "warnings": [],
            "rubric_criteria": [{"criterion": "Too much", "maximum_marks": "3", "description": None}],
        }
    ]})
    assert invalid.status_code == 200
    assert invalid.json()["imported"] == []
    assert invalid.json()["skipped_conflicts"] == ["Q2: rubric criteria marks exceed question maximum"]


def test_question_paper_document_text_extraction_and_schema() -> None:
    from pathlib import Path
    import fitz
    from app.schemas.question_paper import QuestionPaperParseResult
    from app.services.question_paper_document_service import QuestionPaperDocumentService
    path = Path("/private/tmp/question-paper-text-test.pdf")
    document = fitz.open(); page = document.new_page(); page.insert_text((72, 72), "Section A\n1. Explain photosynthesis. [5 marks]\n2. Define chlorophyll. [2 marks]"); document.save(path); document.close()
    extracted = QuestionPaperDocumentService().extract(path, "application/pdf")
    assert extracted.use_text and "photosynthesis" in extracted.text
    assert QuestionPaperParseResult.model_validate({"sections":[{"section_label":"A","instructions":None,"questions":[{"question_number":"1","question_text":"Explain","maximum_marks":"5","parent_question_number":None,"sequence_order":1,"confidence":0.9,"warnings":[]}]}]}).sections[0].questions[0].question_number == "1"
    path.unlink()


def test_question_paper_provider_selection_and_ollama_contract(monkeypatch) -> None:
    import json
    import httpx
    from app.ai.question_parser import OllamaQuestionPaperParser, OpenAIQuestionPaperParser, QuestionPaperParser, QuestionPaperParsingError
    from app.core.config import get_settings
    from app.services.question_paper_document_service import DocumentExtraction

    parsed = {"exam_title": None, "subject": None, "sections": [{"section_label": "A", "instructions": None, "questions": [{"question_number": "1", "question_text": "Define energy.", "maximum_marks": "2", "parent_question_number": None, "sequence_order": 1, "confidence": 0.9, "warnings": []}]}]}
    monkeypatch.setenv("AI_PROVIDER", "auto"); monkeypatch.delenv("OPENAI_API_KEY", raising=False); get_settings.cache_clear()
    assert QuestionPaperParser().provider == "ollama"
    monkeypatch.setenv("OPENAI_API_KEY", "test-key"); get_settings.cache_clear()
    assert QuestionPaperParser().provider == "openai"
    assert isinstance(QuestionPaperParser()._parser, OpenAIQuestionPaperParser)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False); monkeypatch.setenv("OLLAMA_TEXT_MODEL", "llava:7b"); monkeypatch.setenv("OLLAMA_VISION_MODEL", "llava:7b"); get_settings.cache_clear()
    calls = []
    class Response:
        def raise_for_status(self): return None
        status_code = 200
        def json(self): return {"message": {"role": "assistant", "content": json.dumps(parsed), "thinking": "ignored"}, "done": True, "done_reason": "stop"}
    def post(*args, **kwargs): calls.append((args, kwargs)); return Response()
    parser = OllamaQuestionPaperParser(post=post)
    text_result = parser.parse(DocumentExtraction("1. Define energy.", [], True))
    vision_result = parser.parse(DocumentExtraction("", [b"image"], False))
    assert text_result == vision_result
    assert calls[0][1]["json"]["model"] == parser.text_model
    assert "images" not in calls[0][1]["json"]["messages"][0] and calls[1][1]["json"]["messages"][0]["images"]
    assert calls[1][1]["json"]["model"] == parser.vision_model
    assert "think" not in calls[0][1]["json"]
    def unavailable(*args, **kwargs): raise httpx.ConnectError("down")
    with pytest.raises(QuestionPaperParsingError, match="unavailable"):
        OllamaQuestionPaperParser(post=unavailable).parse(DocumentExtraction("x", [], True))
    class MissingResponse:
        status_code = 404
        def raise_for_status(self): raise httpx.HTTPStatusError("missing", request=httpx.Request("POST", "http://test"), response=self)
    with pytest.raises(QuestionPaperParsingError, match="ollama pull"):
        OllamaQuestionPaperParser(post=lambda *args, **kwargs: MissingResponse()).parse(DocumentExtraction("x", [], True))
    class InvalidResponse:
        def raise_for_status(self): return None
        status_code = 200
        def json(self): return {"message": {"role": "assistant", "content": "{invalid", "thinking": "ignored"}, "done": True}
    with pytest.raises(QuestionPaperParsingError, match="required parser schema"):
        OllamaQuestionPaperParser(post=lambda *args, **kwargs: InvalidResponse()).parse(DocumentExtraction("x", [], True))


def test_qwen_ollama_requests_use_native_chat_without_thinking_override(monkeypatch) -> None:
    import json
    from app.ai.question_parser import OllamaQuestionPaperParser
    from app.core.config import get_settings
    from app.services.question_paper_document_service import DocumentExtraction
    monkeypatch.setenv("OLLAMA_TEXT_MODEL", "qwen3-vl:8b"); monkeypatch.setenv("OLLAMA_VISION_MODEL", "qwen3-vl:8b"); get_settings.cache_clear()
    payload = {"sections":[{"questions":[{"question_number":"Q1","question_text":"One"}]}]}
    calls = []
    class Response:
        def raise_for_status(self): return None
        status_code = 200
        def json(self): return {"message": {"role": "assistant", "content": json.dumps(payload), "thinking": "ignored"}, "done": True}
    parser = OllamaQuestionPaperParser(post=lambda *args, **kwargs: calls.append(kwargs["json"]) or Response())
    parser.parse(DocumentExtraction("Q1. One", [], True)); parser.parse(DocumentExtraction("", [b"image"], False))
    assert "think" not in calls[0] and "think" not in calls[1]


def test_ollama_chat_response_reads_message_content_and_ignores_thinking(monkeypatch) -> None:
    import json
    from app.ai.question_parser import OllamaQuestionPaperParser, QuestionPaperParsingError
    from app.services.question_paper_document_service import DocumentExtraction
    monkeypatch.setenv("OLLAMA_TEXT_MODEL", "qwen3-vl:8b"); monkeypatch.setenv("OLLAMA_VISION_MODEL", "qwen3-vl:8b")
    from app.core.config import get_settings
    get_settings.cache_clear()
    valid = {"sections": [{"questions": [{"question_number": "Q1", "question_text": "Find HCF.", "maximum_marks": "2", "parent_question_number": None, "sequence_order": 1, "confidence": .9, "warnings": []}]}]}
    class Response:
        status_code = 200
        def __init__(self, content, thinking="reasoning text"): self.content = content; self.thinking = thinking
        def raise_for_status(self): return None
        def json(self): return {"message": {"role": "assistant", "content": self.content, "thinking": self.thinking}, "done": True, "done_reason": "stop", "eval_count": 12}
    parser = OllamaQuestionPaperParser(post=lambda *args, **kwargs: Response(json.dumps(valid)))
    result = parser.parse(DocumentExtraction("Q1. Find HCF. [2 marks]", [], True))
    assert result.sections[0].questions[0].question_number == "Q1"
    with pytest.raises(QuestionPaperParsingError, match="empty assistant response"):
        OllamaQuestionPaperParser(post=lambda *args, **kwargs: Response("", "thinking only")).parse(DocumentExtraction("Q1", [], True))
    with pytest.raises(QuestionPaperParsingError, match="required parser schema"):
        OllamaQuestionPaperParser(post=lambda *args, **kwargs: Response("{invalid}", "thinking only")).parse(DocumentExtraction("Q1", [], True))


def test_blank_ollama_context_is_omitted_from_chat_options(monkeypatch) -> None:
    from app.ai.question_parser import OllamaQuestionPaperParser
    from app.core.config import get_settings
    from app.services.question_paper_document_service import DocumentExtraction
    monkeypatch.setenv("OLLAMA_NUM_CTX", ""); get_settings.cache_clear()
    endpoint, payload = OllamaQuestionPaperParser().build_request(DocumentExtraction("Q1. Test", [], True))
    assert endpoint == "/api/chat"
    assert payload["options"] == {"temperature": 0}


def test_local_ollama_defaults_and_specialized_model_fallbacks(monkeypatch) -> None:
    from app.ai.answer_mapper import AnswerMapper
    from app.ai.evaluator import AnswerEvaluator
    from app.ai.structured_provider import StructuredAIProvider
    from app.core.config import Settings, get_settings

    defaults = Settings(_env_file=None)
    assert defaults.ollama_text_model == "gemma3:4b"
    assert defaults.ollama_vision_model == "gemma3:4b"
    assert defaults.ollama_mapping_model == "gemma3:4b"
    assert defaults.ollama_evaluation_model == "gemma3:4b"

    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_TEXT_MODEL", "gemma3:4b")
    monkeypatch.setenv("OLLAMA_MAPPING_MODEL", "")
    monkeypatch.setenv("OLLAMA_EVALUATION_MODEL", "")
    get_settings.cache_clear()
    assert AnswerMapper(provider=StructuredAIProvider()).provider.text_model == "gemma3:4b"
    assert AnswerEvaluator(provider=StructuredAIProvider()).provider.text_model == "gemma3:4b"


def test_structured_ollama_provider_uses_minimal_options(monkeypatch) -> None:
    import httpx
    from pydantic import BaseModel
    from app.ai.structured_provider import StructuredAIProvider
    from app.core.config import get_settings

    class TinyResult(BaseModel):
        ok: bool

    calls = []

    class Response:
        def raise_for_status(self): return None
        def json(self): return {"response": '{"ok": true}'}

    def post(*args, **kwargs):
        calls.append(kwargs["json"])
        return Response()

    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_NUM_CTX", "")
    get_settings.cache_clear()
    monkeypatch.setattr(httpx, "post", post)
    result = StructuredAIProvider().generate(prompt="Return JSON", schema_model=TinyResult)
    assert isinstance(result, TinyResult)
    assert calls[0]["options"] == {"temperature": 0}
    assert "num_ctx" not in calls[0]["options"]


def test_question_paper_subquestion_normalization() -> None:
    from app.ai.question_parser import normalize_question_paper_result
    from app.schemas.question_paper import QuestionPaperParseResult
    result = QuestionPaperParseResult.model_validate({"sections": [{"section_label": None, "instructions": None, "questions": [
        {"question_number": "Q1", "question_text": "Q1. State the law.", "maximum_marks": "1", "parent_question_number": None, "sequence_order": 1, "confidence": 0.9, "warnings": []},
        {"question_number": "Q3", "question_text": "Q3(a). What is evaporation?", "maximum_marks": "2", "parent_question_number": None, "sequence_order": 2, "confidence": 0.9, "warnings": []},
        {"question_number": "Q3(b)", "question_text": "Q3(b). Give one example.", "maximum_marks": "2", "parent_question_number": None, "sequence_order": 3, "confidence": 0.9, "warnings": []},
        {"question_number": "5(i)", "question_text": "5(i). Explain.", "maximum_marks": "2", "parent_question_number": None, "sequence_order": 4, "confidence": 0.9, "warnings": []},
        {"question_number": "Section A - Q1", "question_text": "Define matter.", "maximum_marks": "1", "parent_question_number": None, "sequence_order": 5, "confidence": 0.9, "warnings": []},
    ]}]})
    questions = normalize_question_paper_result(result).sections[0].questions
    assert [(item.question_number, item.question_text, item.parent_question_number) for item in questions] == [
        ("Q1", "State the law.", None), ("Q3(a)", "What is evaporation?", "Q3"),
        ("Q3(b)", "Give one example.", "Q3"), ("Q5(i)", "Explain.", "Q5"),
        ("Section A - Q1", "Define matter.", None),
    ]


def test_question_paper_recovers_only_visible_marks() -> None:
    from app.ai.question_parser import recover_visible_marks
    from app.schemas.question_paper import QuestionPaperParseResult
    result = QuestionPaperParseResult.model_validate({"sections": [{"section_label": None, "instructions": None, "questions": [
        {"question_number": "Q1", "question_text": "Define.", "maximum_marks": None, "parent_question_number": None, "sequence_order": 1, "confidence": 0.9, "warnings": []},
        {"question_number": "Q3(a)", "question_text": "Explain.", "maximum_marks": None, "parent_question_number": "Q3", "sequence_order": 2, "confidence": 0.9, "warnings": []},
        {"question_number": "Q4", "question_text": "No mark shown.", "maximum_marks": None, "parent_question_number": None, "sequence_order": 3, "confidence": 0.9, "warnings": []},
    ]}]})
    source = "Q1. Define.\n[2 marks]\nQ3(a). Explain.\n(1.5 marks)\nQ4. No mark shown."
    questions = recover_visible_marks(result, source).sections[0].questions
    assert [str(question.maximum_marks) if question.maximum_marks is not None else None for question in questions] == ["2", "1.5", None]


def test_question_paper_local_model_output_adapter() -> None:
    from app.ai.question_parser import validate_parser_output
    output = '{"exam_title":"Science","sections":[{"section_label":"A","questions":[{"question_number":"Q3(a)","question_text":"Explain.","sequence_order":3,"confidence":100}]}]}'
    question = validate_parser_output(output).sections[0].questions[0]
    assert question.maximum_marks is None
    assert question.parent_question_number == "Q3"
    assert question.confidence == 1


def test_question_paper_reference_fields_are_optional_and_not_invented() -> None:
    from app.ai.question_parser import validate_parser_output
    output = '{"sections":[{"questions":[{"question_number":"Q1","question_text":"Define matter.","maximum_marks":"2","sequence_order":1,"confidence":0.9}]}]}'
    question = validate_parser_output(output).sections[0].questions[0]
    assert question.model_answer is None
    assert question.key_concepts is None
    assert question.acceptable_alternatives is None
    assert question.reference_solution is None
    assert question.marking_notes is None
    assert question.rubric_criteria == []


def test_question_paper_parser_accepts_reference_blocks_and_rubrics() -> None:
    from app.ai.question_parser import validate_parser_output
    output = """{"sections":[{"questions":[{
        "question_number":"Q1",
        "question_text":"Explain photosynthesis.",
        "maximum_marks":"3",
        "sequence_order":1,
        "confidence":0.95,
        "model_answer":"Plants make food using sunlight.",
        "key_concepts":"chlorophyll; sunlight",
        "acceptable_alternatives":"Equivalent wording is acceptable.",
        "reference_solution":"CO2 + water -> glucose + oxygen",
        "marking_notes":"Award partial credit.",
        "rubric_criteria":[
            {"criterion":"Defines process","maximum_marks":"1","description":"Mentions food making."},
            {"criterion":"Mentions inputs","maximum_marks":"[2 marks]","description":null}
        ]
    }]}]}"""
    question = validate_parser_output(output).sections[0].questions[0]
    assert question.model_answer == "Plants make food using sunlight."
    assert question.key_concepts == "chlorophyll; sunlight"
    assert question.rubric_criteria[1].maximum_marks == 2


def test_question_paper_local_model_markdown_json_adapter() -> None:
    from app.ai.question_parser import validate_parser_output
    output = "Here is the result:\n```json\n{\"sections\":[{\"questions\":[{\"question_number\":\"1\",\"question_text\":\"Define matter.\"}]}]}\n```\n"
    question = validate_parser_output(output).sections[0].questions[0]
    assert question.question_number == "Q1"
    assert question.question_text == "Define matter."


def test_question_paper_adapter_skips_qwen_thinking_json_before_result() -> None:
    from app.ai.question_parser import validate_parser_output
    output = '<think>{"draft": "not the result"}</think>\nThe final JSON is {"sections":[{"questions":[{"question_number":"Q1","question_text":"Actual result"}]}]}'
    question = validate_parser_output(output).sections[0].questions[0]
    assert question.question_number == "Q1"
    assert question.question_text == "Actual result"


def test_question_paper_vision_marks_recovery_and_review_warning() -> None:
    from app.ai.question_parser import coerce_visible_mark, recover_vision_marks
    from app.schemas.question_paper import QuestionPaperParseResult
    parsed = QuestionPaperParseResult.model_validate({"sections": [{"section_label": None, "instructions": None, "questions": [
        {"question_number": "Q1", "question_text": "One.", "maximum_marks": None, "parent_question_number": None, "sequence_order": 1, "confidence": 0.9, "warnings": []},
        {"question_number": "Q2", "question_text": "Two.", "maximum_marks": None, "parent_question_number": None, "sequence_order": 2, "confidence": 0.9, "warnings": []},
        {"question_number": "Q3(a)", "question_text": "Three.", "maximum_marks": None, "parent_question_number": "Q3", "sequence_order": 3, "confidence": 0.9, "warnings": []},
        {"question_number": "Q4", "question_text": "Four.", "maximum_marks": None, "parent_question_number": None, "sequence_order": 4, "confidence": 0.9, "warnings": []},
    ]}]})
    questions = recover_vision_marks(parsed, {"Q1": 2, "Q2": 3, "Q3(a)": 5}).sections[0].questions
    assert [str(question.maximum_marks) if question.maximum_marks is not None else None for question in questions] == ["2", "3", "5", None]
    assert questions[2].parent_question_number == "Q3"
    assert questions[3].warnings == ["Maximum marks could not be determined from the visible document."]
    assert [str(coerce_visible_mark(value)) for value in ["[2 marks]", "[3]", "(5 marks)", "Marks: 2", "M: 2", "2M"]] == ["2", "3", "5", "2", "2", "2"]


def test_ollama_vision_second_pass_recovers_right_column_marks(monkeypatch) -> None:
    import json
    from app.ai.question_parser import OllamaQuestionPaperParser
    from app.core.config import get_settings
    from app.services.question_paper_document_service import DocumentExtraction
    monkeypatch.delenv("OPENAI_API_KEY", raising=False); get_settings.cache_clear()
    responses = iter([
        {"message": {"role": "assistant", "content": json.dumps({"sections": [{"questions": [
            {"question_number": "Q1", "question_text": "One.", "confidence": 0.9},
            {"question_number": "Q2", "question_text": "Two.", "confidence": 0.9},
            {"question_number": "Q3(a)", "question_text": "Three.", "confidence": 0.9},
            {"question_number": "Q4", "question_text": "Four.", "confidence": 0.9},
        ]}]}), "thinking": "ignored"}, "done": True},
        {"message": {"role": "assistant", "content": json.dumps({"marks": [
            {"question_number": "Q1", "maximum_marks": "[2 marks]"},
            {"question_number": "Q2", "maximum_marks": "[3]"},
            {"question_number": "Q3(a)", "maximum_marks": "(5 marks)"},
        ]}), "thinking": "ignored"}, "done": True},
    ])
    class Response:
        def raise_for_status(self): return None
        status_code = 200
        def json(self): return next(responses)
    parsed = OllamaQuestionPaperParser(post=lambda *args, **kwargs: Response()).parse(DocumentExtraction("", [b"scan"], False))
    questions = parsed.sections[0].questions
    assert [str(question.maximum_marks) if question.maximum_marks is not None else None for question in questions] == ["2", "3", "5", None]
    assert questions[2].parent_question_number == "Q3"
    assert questions[3].warnings == ["Maximum marks could not be determined from the visible document."]


def test_bulk_question_delete_is_owned_and_transactional(client) -> None:
    seed_user(client); login(client)
    exam = create_exam(client, "Bulk questions")
    first = client.post(f"/api/exams/{exam['id']}/questions", json={"question_number":"1", "question_text":"One", "maximum_marks":"1", "sequence_order":1}).json()
    second = client.post(f"/api/exams/{exam['id']}/questions", json={"question_number":"2", "question_text":"Two", "maximum_marks":"1", "sequence_order":2}).json()
    deleted = client.request("DELETE", f"/api/exams/{exam['id']}/questions/bulk", json={"question_ids":[first["id"], second["id"]]})
    assert deleted.status_code == 200 and deleted.json()["deleted_count"] == 2
    assert client.get(f"/api/exams/{exam['id']}/questions").json() == []


def test_evaluation_clamps_ai_marks_and_preserves_faculty_override(client, monkeypatch) -> None:
    from decimal import Decimal
    from app.ai.evaluator import AnswerEvaluator
    from app.schemas.evaluation import AIEvaluationResult, AIEvaluationCriterion
    from app.models.evaluation import StudentAnswer
    seed_user(client); login(client)
    exam = create_exam(client, "Evaluation")
    student = create_student(client, exam["id"])
    question = client.post(f"/api/exams/{exam['id']}/questions", json={"question_number":"Q1", "question_text":"Define force", "model_answer":"A push or pull", "maximum_marks":"2", "sequence_order":1}).json()
    rubric = client.post(f"/api/questions/{question['id']}/rubric-criteria", json={"criterion":"Definition", "maximum_marks":"2", "sequence_order":1}).json()
    generator = client.app.dependency_overrides[get_db](); db = next(generator)
    submission = StudentSubmission(exam_id=UUID(exam["id"]), student_id=UUID(student["id"])); db.add(submission); db.flush()
    answer = StudentAnswer(student_submission_id=submission.id, question_id=UUID(question["id"]), detected_question_number="Q1", answer_text="A push", page_numbers=[1], extraction_confidence=Decimal(".9"), mapping_confidence=Decimal("1")); db.add(answer); db.commit(); answer_id = answer.id; generator.close()
    def fake(self, payload): return AIEvaluationResult(marks_awarded=Decimal("5"), max_marks=Decimal("2"), confidence=Decimal(".9"), criteria=[AIEvaluationCriterion(rubric_criterion_id=UUID(rubric["id"]), criterion_text="Definition", maximum_marks=Decimal("2"), awarded_marks=Decimal("5"), evidence="push")])
    monkeypatch.setattr(AnswerEvaluator, "evaluate", fake)
    evaluated = client.post(f"/api/student-answers/{answer_id}/evaluate")
    assert evaluated.status_code == 200 and evaluated.json()["ai_marks"] == "2.00"
    evaluation = evaluated.json()
    overridden = client.put(f"/api/evaluations/{evaluation['id']}", json={"manual_marks":"1.50", "faculty_remarks":"partial"})
    assert overridden.status_code == 200 and overridden.json()["ai_marks"] == "2.00" and overridden.json()["final_marks"] == "1.50"
    assert client.put(f"/api/evaluations/{evaluation['id']}", json={"manual_marks":"3"}).status_code == 422


def test_student_answer_edit_preserves_raw_extraction_and_question_normalization(client) -> None:
    from decimal import Decimal
    from app.models.evaluation import StudentAnswer
    from app.services.evaluation_service import EvaluationService
    seed_user(client); login(client)
    exam = create_exam(client, "Extraction review")
    student = create_student(client, exam["id"])
    question = client.post(f"/api/exams/{exam['id']}/questions", json={"question_number":"Q10(a)", "question_text":"Subquestion", "maximum_marks":"2", "sequence_order":1}).json()
    generator = client.app.dependency_overrides[get_db](); db = next(generator)
    submission = StudentSubmission(exam_id=UUID(exam["id"]), student_id=UUID(student["id"])); db.add(submission); db.flush()
    answer = StudentAnswer(student_submission_id=submission.id, question_id=UUID(question["id"]), detected_question_number="10a", answer_text="original OCR", raw_text="original OCR", page_numbers=[1], extraction_confidence=Decimal(".4"), mapping_confidence=Decimal("1"), extraction_status="review_required", warnings=["Handwriting unclear"])
    db.add(answer); db.commit(); answer_id = answer.id; generator.close()
    edited = client.put(f"/api/student-answers/{answer_id}", json={"question_id": question["id"], "answer_text":"faculty correction", "reviewed":True})
    assert edited.status_code == 200, edited.text
    assert edited.json()["raw_text"] == "original OCR"
    assert edited.json()["edited_text"] == "faculty correction"
    assert edited.json()["answer_text"] == "original OCR"
    assert edited.json()["extraction_status"] == "reviewed"
    assert EvaluationService._normal("Question 10(a)") == "q10(a)"
    assert EvaluationService._normal("Q.1") == "q1"
    assert EvaluationService._normal("1") == "q1"
    assert EvaluationService._normal("3a") == "q3(a)"
    assert EvaluationService._normal("10b") == "q10(b)"


def test_answer_extractor_uses_provider_contract_and_processes_every_page() -> None:
    from app.ai.answer_extractor import AnswerExtractor, ExtractionDocument
    from app.ai.prompts.answer_extractor_v1 import ANSWER_EXTRACTOR_PROMPT
    from app.schemas.evaluation import AIExtractionResult

    assert "Never correct arithmetic" in ANSWER_EXTRACTOR_PROMPT
    assert "Never correct algebra" in ANSWER_EXTRACTOR_PROMPT
    assert "strict transcription only" in ANSWER_EXTRACTOR_PROMPT
    assert "does not provide model answers" in ANSWER_EXTRACTOR_PROMPT
    assert "3x = 4\nx = 4/3" in ANSWER_EXTRACTOR_PROMPT
    assert "3x = 18\nx = 6" in ANSWER_EXTRACTOR_PROMPT
    assert "x = 3 or x = 4" in ANSWER_EXTRACTOR_PROMPT
    assert "= 77.5 cm^2" in ANSWER_EXTRACTOR_PROMPT

    class Provider:
        provider = "ollama"
        vision_model = "gemma3:4b"

        def __init__(self):
            self.calls = 0

        def generate(self, **kwargs):
            prompt = kwargs["prompt"]
            assert "Read question labels only from the page image" in prompt
            assert "Expected question labels" not in prompt
            assert "Known questions" not in prompt
            assert "question_text" not in prompt
            assert "model_answer" not in prompt
            assert "reference_solution" not in prompt
            assert "rubric_criteria" not in prompt
            assert "marking_notes" not in prompt
            assert "key_concepts" not in prompt
            self.calls += 1
            page = self.calls
            answer_text = "3x - 7 = 11\n3x = 4\nx = 4/3" if page == 1 else f"answer {page}"
            return AIExtractionResult.model_validate({"answers": [
                {
                    "detected_question_number": f"Q{page}",
                    "answer_text": answer_text,
                    "confidence": 0.9,
                    "source_pages": [page],
                    "warnings": [],
                }
            ]})

    provider = Provider()
    result = AnswerExtractor(provider=provider).extract(
        ExtractionDocument(images=[b"page-1", b"page-2", b"page-3"], page_numbers=[1, 2, 3]),
        [{"question_number": "Q1", "question_text": "One"}],
    )
    assert provider.calls == 3
    assert [item.detected_question_number for item in result.answers] == ["Q1", "Q2", "Q3"]
    assert [item.page_numbers for item in result.answers] == [[1], [2], [3]]
    assert result.answers[0].answer_text == "3x - 7 = 11\n3x = 4\nx = 4/3"


def test_answer_extractor_preserves_known_wrong_student_work_verbatim() -> None:
    from app.ai.answer_extractor import AnswerExtractor, ExtractionDocument
    from app.schemas.evaluation import AIExtractionResult

    wrong_answers = {
        "Q2": "3x - 7 = 11\n3x = 4\nx = 4/3",
        "Q4": "Prime numbers are 2 and 5.\nProbability = 2/6 = 1/3",
        "Q5": "C = pi r\n= 22/7 x 7\n= 22 cm",
        "Q8": "Mean = 12 + 15 + 18 + 20 / 4\n= 65/4\n= 16.25",
        "Q1": "36 = 2 x 2 x 3 x 3\n48 = 2 x 2 x 2 x 2 x 3\nHCF = 6",
        "Q10(a)": "x^2 - 7x + 12 = 0\n(x - 3)(x - 4) = 0\nx = 3",
    }
    corrected_fragments = ["3x = 18", "x = 6", "2, 3, and 5", "1/2", "2πr", "44 cm", "16.25 only", "HCF = 12", "x = 3 or x = 4"]

    class Provider:
        provider = "ollama"
        vision_model = "gemma3:4b"

        def generate(self, **kwargs):
            return AIExtractionResult.model_validate({"answers": [
                {
                    "detected_question_number": label,
                    "answer_text": text,
                    "confidence": 0.93,
                    "source_pages": [1],
                    "warnings": [],
                }
                for label, text in wrong_answers.items()
            ]})

    result = AnswerExtractor(provider=Provider()).extract(ExtractionDocument(images=[b"page"], page_numbers=[1]), list(wrong_answers))
    by_label = {item.detected_question_number: item.answer_text for item in result.answers}
    assert by_label == wrong_answers
    combined = "\n".join(by_label.values())
    for fragment in corrected_fragments:
        assert fragment not in combined


def test_processing_auto_maps_exact_and_semantic_labels(client, monkeypatch) -> None:
    from decimal import Decimal
    from app.ai.answer_extractor import AnswerExtractor
    from app.ai.answer_mapper import AnswerMapper
    from app.models.submission import SubmissionFile
    from app.schemas.evaluation import AIAnswerMappingResult, AIExtractionResult
    from app.services.evaluation_service import EvaluationService

    seed_user(client); login(client)
    exam = create_exam(client, "Automatic mapping")
    student = create_student(client, exam["id"])
    labels = ["Q1", "Q2", "Q3(a)", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9", "Q10(a)", "Q10(b)", "Q11"]
    for order, label in enumerate(labels, 1):
        response = client.post(f"/api/exams/{exam['id']}/questions", json={"question_number": label, "question_text": f"Question {label}", "maximum_marks": "2", "sequence_order": order})
        assert response.status_code == 201, response.text

    generator = client.app.dependency_overrides[get_db](); db = next(generator)
    source = AnswerSheet(exam_id=UUID(exam["id"]), student_id=UUID(student["id"]), original_filename="mapping.pdf", stored_filename="mapping.pdf", file_path="answer-sheets/mapping.pdf", mime_type="application/pdf", file_size=1, status=AnswerSheetStatus.UPLOADED)
    submission = StudentSubmission(exam_id=UUID(exam["id"]), student_id=UUID(student["id"])); db.add_all([source, submission]); db.flush()
    db.add(SubmissionFile(submission_id=submission.id, answer_sheet_id=source.id, sequence_order=1)); db.commit(); source_id = source.id; generator.close()

    wrong_by_label = {
        "Q1": "36 = 2 x 2 x 3 x 3\n48 = 2 x 2 x 2 x 2 x 3\nHCF = 6",
        "Q2": "3x - 7 = 11\n3x = 4\nx = 4/3",
        "Q4": "Prime numbers are 2 and 5.\nProbability = 2/6 = 1/3",
        "Q5": "C = pi r\n= 22/7 x 7\n= 22 cm",
        "Q8": "Mean = 12 + 15 + 18 + 20 / 4\n= 65/4\n= 16.25",
        "Q10(a)": "x^2 - 7x + 12 = 0\n(x - 3)(x - 4) = 0\nx = 3",
    }
    extracted = []
    for order, label in enumerate(labels):
        # Exercise aliases, missing-label fallback, shorthand normalization, and
        # low transcription confidence that must not block an exact label match.
        detected = label
        if order < 4: detected = None
        elif label == "Q7": detected = "Question 7"
        elif label == "Q10(a)": detected = "10a"
        answer_text = wrong_by_label.get(label, f"answer {label}")
        extracted.append({"detected_question_number": detected, "answer_text": answer_text, "confidence": 0.5 if label == "Q7" else 0.95, "source_pages": [order // 4 + 1], "warnings": []})

    monkeypatch.setattr(EvaluationService, "_render_pages", lambda self, source: [b"one", b"two", b"three"])
    monkeypatch.setattr(AnswerExtractor, "extract", lambda self, document, questions: AIExtractionResult.model_validate({"answers": extracted}))
    monkeypatch.setattr(AnswerMapper, "map", lambda self, answers, questions: AIAnswerMappingResult.model_validate({"mappings": [{
        "segment_index": 0,
        "question_number": questions[0]["question_number"],
        "confidence": 0.99,
        "reason": "unique semantic match",
    }]}))

    response = client.post(f"/api/answer-sheets/{source_id}/process")
    assert response.status_code == 200, response.text
    answers = response.json()
    assert len(answers) == 12
    assert all(item["question_id"] is not None and item["mapping_status"] == "auto_mapped" for item in answers)
    assert answers[0]["detected_question_number"] is None
    by_detected_or_text = {item["detected_question_number"] or item["raw_text"]: item for item in answers}
    assert answers[0]["raw_text"] == wrong_by_label["Q1"]
    assert answers[1]["raw_text"] == wrong_by_label["Q2"]
    assert wrong_by_label["Q4"] in {item["raw_text"] for item in answers}
    assert by_detected_or_text["Q5"]["raw_text"] == wrong_by_label["Q5"]
    assert by_detected_or_text["Q8"]["raw_text"] == wrong_by_label["Q8"]
    assert by_detected_or_text["10a"]["raw_text"] == wrong_by_label["Q10(a)"]
    assert all("3x = 18" not in item["raw_text"] and "x = 6" not in item["raw_text"] for item in answers)
    persisted = client.get(f"/api/student-submissions/{answers[0]['student_submission_id']}/answers")
    assert persisted.status_code == 200
    assert persisted.json()[1]["raw_text"] == wrong_by_label["Q2"]
    assert answers[6]["detected_question_number"] == "Question 7"
    assert answers[6]["mapping_confidence"] == "1.0000"


def test_processing_reset_and_delete_lifecycle_preserves_source_until_sheet_delete(client) -> None:
    from decimal import Decimal
    from app.models.evaluation import Evaluation, EvaluationStatus, StudentAnswer
    from app.models.submission import SubmissionFile
    seed_user(client); login(client)
    exam = create_exam(client, "Lifecycle")
    student = create_student(client, exam["id"])
    question = client.post(f"/api/exams/{exam['id']}/questions", json={"question_number":"Q1", "question_text":"One", "maximum_marks":"2", "sequence_order":1}).json()
    generator = client.app.dependency_overrides[get_db](); db = next(generator)
    source = AnswerSheet(exam_id=UUID(exam["id"]), student_id=UUID(student["id"]), original_filename="sheet.pdf", stored_filename="lifecycle.pdf", file_path="answer-sheets/lifecycle.pdf", mime_type="application/pdf", file_size=4, status=AnswerSheetStatus.EXTRACTED)
    submission = StudentSubmission(exam_id=UUID(exam["id"]), student_id=UUID(student["id"])); db.add_all([source, submission]); db.flush()
    link = SubmissionFile(submission_id=submission.id, answer_sheet_id=source.id, sequence_order=1); answer = StudentAnswer(student_submission_id=submission.id, question_id=UUID(question["id"]), detected_question_number="Q1", answer_text="one", raw_text="one", page_numbers=[1], extraction_confidence=Decimal(".9"), mapping_confidence=Decimal("1"), extraction_status="extracted")
    db.add_all([link, answer]); db.flush()
    evaluation = Evaluation(student_answer_id=answer.id, ai_marks=Decimal("1"), final_marks=Decimal("1"), maximum_marks=Decimal("2"), confidence=Decimal(".9"), strengths=[], missing_points=[], feedback="", reasoning="", status=EvaluationStatus.AI_EVALUATED)
    db.add(evaluation); db.commit(); submission_id, source_id, answer_id, link_id = submission.id, source.id, answer.id, link.id; generator.close()
    assert len(client.get(f"/api/exams/{exam['id']}/results").json()) == 1
    assert client.post(f"/api/student-submissions/{submission_id}/reset-evaluations").status_code == 204
    generator = client.app.dependency_overrides[get_db](); db = next(generator)
    assert db.get(StudentAnswer, answer_id) is not None and db.get(StudentAnswer, answer_id).evaluation is None
    generator.close()
    assert client.delete(f"/api/student-answers/{answer_id}").status_code == 204
    generator = client.app.dependency_overrides[get_db](); db = next(generator)
    assert db.get(StudentAnswer, answer_id) is None and db.get(AnswerSheet, source_id) is not None and db.get(StudentSubmission, submission_id) is not None
    replacement = StudentAnswer(student_submission_id=submission_id, question_id=UUID(question["id"]), detected_question_number="Q1", answer_text="replacement", raw_text="replacement", page_numbers=[1], extraction_confidence=Decimal(".8"), mapping_confidence=Decimal("1"), extraction_status="extracted"); db.add(replacement); db.commit(); generator.close()
    assert client.post(f"/api/student-submissions/{submission_id}/reset-extraction").status_code == 204
    generator = client.app.dependency_overrides[get_db](); db = next(generator)
    assert db.scalars(select(StudentAnswer).where(StudentAnswer.student_submission_id == submission_id)).all() == []
    assert db.get(AnswerSheet, source_id) is not None and db.get(StudentSubmission, submission_id) is not None and db.get(SubmissionFile, link_id) is not None
    generator.close()
    assert client.get(f"/api/exams/{exam['id']}/results").json() == []
    assert client.delete(f"/api/answer-sheets/{source_id}").status_code == 204
    generator = client.app.dependency_overrides[get_db](); db = next(generator)
    assert db.get(AnswerSheet, source_id) is None and db.get(StudentSubmission, submission_id) is None and db.get(Student, UUID(student["id"])) is not None
    generator.close()


def test_math_paper_candidate_normalization_deduplicates_and_preserves_subquestions() -> None:
    """Regression: repeated Q1–Q11 model output must become the 12 visible candidates."""
    from app.ai.question_parser import normalize_question_paper_result
    from app.schemas.question_paper import QuestionPaperParseResult
    source = []
    for number in range(1, 10):
        source.append({"question_number": str(number), "question_text": f"[{number % 5 + 1} marks] Question {number}", "maximum_marks": None, "parent_question_number": str(number), "sequence_order": number, "confidence": .9, "warnings": []})
    source += [
        {"question_number":"10(a)","question_text":"Q10(a). [2 marks] First subquestion","maximum_marks":None,"parent_question_number":"10(a)","sequence_order":10,"confidence":.9,"warnings":[]},
        {"question_number":"Q10(b)","question_text":"Q10(b). [3] Second subquestion","maximum_marks":None,"parent_question_number":None,"sequence_order":11,"confidence":.9,"warnings":[]},
        {"question_number":"Q11","question_text":"Q11. [5M] Final question","maximum_marks":None,"parent_question_number":"Q11","sequence_order":12,"confidence":.9,"warnings":["first"]},
    ]
    # Simulate the old repeated second model block; it must not create new candidates.
    source += [{**item, "question_text": "short", "maximum_marks": None, "sequence_order": item["sequence_order"] + 20, "warnings": ["duplicate"]} for item in source]
    parsed = QuestionPaperParseResult.model_validate({"sections":[{"section_label":"A","instructions":None,"questions":source}]})
    questions = normalize_question_paper_result(parsed).sections[0].questions
    assert [question.question_number for question in questions] == [*[f"Q{value}" for value in range(1, 10)], "Q10(a)", "Q10(b)", "Q11"]
    assert [question.sequence_order for question in questions] == list(range(1, 13))
    assert questions[0].question_text == "Question 1" and str(questions[0].maximum_marks) == "2"
    assert questions[0].parent_question_number is None
    assert questions[9].parent_question_number == "Q10"
    assert questions[10].parent_question_number == "Q10"
    assert all(question.parent_question_number != question.question_number for question in questions)


def test_question_text_trailing_mark_metadata_is_promoted_to_marks() -> None:
    from app.ai.question_parser import normalize_question_paper_result
    from app.schemas.question_paper import QuestionPaperParseResult
    result = QuestionPaperParseResult.model_validate({"sections":[{"questions":[
        {"question_number":"Q1","question_text":"Find the HCF. [2 marks]","maximum_marks":None,"parent_question_number":None,"sequence_order":1,"confidence":.9,"warnings":[]},
        {"question_number":"Q2","question_text":"Solve x. (5)","maximum_marks":None,"parent_question_number":None,"sequence_order":2,"confidence":.9,"warnings":[]},
    ]}]})
    questions = normalize_question_paper_result(result).sections[0].questions
    assert [(question.question_text, str(question.maximum_marks)) for question in questions] == [("Find the HCF.", "2"), ("Solve x.", "5")]


@pytest.mark.parametrize("value, expected", [
    (2, "2"), (2.0, "2.0"), ("2", "2"), ("2 marks", "2"), ("[2 marks]", "2"),
    ("[10 marks]", "10"), ("(5 marks)", "5"), ("  [ 2 marks ]  ", "2"), (None, None),
])
def test_provider_marks_are_normalized_before_strict_schema_validation(value, expected) -> None:
    from app.ai.question_parser import parse_ollama_question_paper_content
    import json
    raw = {"sections": [{"section_label": "A", "questions": [{"question_number": "Q1", "question_text": "One", "maximum_marks": value, "sequence_order": 1, "confidence": .9}]}]}
    result = parse_ollama_question_paper_content(json.dumps(raw))
    mark = result.sections[0].questions[0].maximum_marks
    assert (str(mark) if mark is not None else None) == expected


@pytest.mark.parametrize("value", ["Question worth approximately 2 marks maybe", "2 out of 5", "see question 2"])
def test_unsafe_provider_mark_strings_are_not_silently_normalized(value) -> None:
    from app.ai.question_parser import QuestionPaperParsingError, parse_ollama_question_paper_content
    import json
    raw = {"sections": [{"questions": [{"question_number": "Q1", "question_text": "One", "maximum_marks": value, "sequence_order": 1, "confidence": .9}]}]}
    with pytest.raises(QuestionPaperParsingError, match="required parser schema"):
        parse_ollama_question_paper_content(json.dumps(raw))


def test_question_paper_import_rejects_duplicate_selected_candidates(client) -> None:
    seed_user(client); login(client)
    exam = create_exam(client, "Candidate duplicate protection")
    result = client.post(f"/api/exams/{exam['id']}/question-paper/import", json={"questions":[
        {"question_number":"Q10(a)","question_text":"First","maximum_marks":"2","parent_question_number":"Q10","sequence_order":1,"confidence":.9,"warnings":[]},
        {"question_number":"q10(a).","question_text":"Duplicate","maximum_marks":"2","parent_question_number":"Q10","sequence_order":2,"confidence":.9,"warnings":[]},
        {"question_number":"Q10(b)","question_text":"Second","maximum_marks":"2","parent_question_number":"Q10","sequence_order":3,"confidence":.9,"warnings":[]},
    ]})
    assert result.status_code == 200
    assert result.json()["skipped_conflicts"] == ["Q10(a): duplicate candidate"]
    assert [item["question_number"] for item in client.get(f"/api/exams/{exam['id']}/questions").json()] == ["Q10(a)", "Q10(b)"]


def test_reparse_replaces_candidates_and_failed_reparse_keeps_last_success(client, monkeypatch) -> None:
    """Stored candidates are a replacement snapshot, never an append-only history."""
    from pathlib import Path
    from app.ai.question_parser import QuestionPaperParsingError
    from app.models.question_paper import QuestionPaper, QuestionPaperStatus
    from app.schemas.question_paper import QuestionPaperParseResult
    from app.services.question_paper_document_service import DocumentExtraction
    from app.services.question_paper_service import QuestionPaperService
    from app.services.storage_service import LocalStorageService
    seed_user(client); login(client); exam = create_exam(client, "Reparse snapshot")
    generator = client.app.dependency_overrides[get_db](); db = next(generator)
    user = db.scalar(__import__("sqlalchemy").select(User).where(User.email == "ada@example.com"))
    storage = LocalStorageService(); relative = "question-papers/reparse.pdf"; path = storage.root / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b"placeholder")
    paper = QuestionPaper(exam_id=UUID(exam["id"]), original_filename="reparse.pdf", stored_filename="reparse-test.pdf", file_path=relative, mime_type="application/pdf", file_size=1, status=QuestionPaperStatus.REVIEW_REQUIRED, parse_result={"sections":[{"section_label":None,"instructions":None,"questions":[{"question_number":"Q99","question_text":"old","maximum_marks":"1","parent_question_number":None,"sequence_order":1,"confidence":.9,"warnings":[]}]}]})
    db.add(paper); db.commit()
    replacement = QuestionPaperParseResult.model_validate({"sections":[{"section_label":None,"instructions":None,"questions":[{"question_number":"Q1","question_text":"new","maximum_marks":"1","parent_question_number":None,"sequence_order":1,"confidence":.9,"warnings":[]}]}]})
    class Docs:
        def extract(self, *args): return DocumentExtraction("text", [], True)
    class Parser:
        provider="ollama"; model="llava"; text_model="llava"; vision_model="llava"
        def parse(self, *args): return replacement
    monkeypatch.setattr("app.services.question_paper_service.QuestionPaperParser", lambda **kwargs: Parser())
    service = QuestionPaperService(storage=storage, documents=Docs()); parsed = service.parse(db, paper.exam_id, user)
    assert parsed.parse_result.sections[0].questions[0].question_number == "Q1"
    class BrokenParser(Parser):
        def parse(self, *args): raise QuestionPaperParsingError("model unavailable")
    monkeypatch.setattr("app.services.question_paper_service.QuestionPaperParser", lambda **kwargs: BrokenParser())
    with pytest.raises(Exception): service.parse(db, paper.exam_id, user)
    db.refresh(paper); assert paper.parse_result["sections"][0]["questions"][0]["question_number"] == "Q1"
    generator.close()
