from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import answer_sheets, auth, evaluations, exams, question_papers, questions, students
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title="AI Answer Evaluator API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)
app.include_router(auth.router)
app.include_router(exams.router)
app.include_router(questions.exam_router)
app.include_router(questions.question_router)
app.include_router(questions.criterion_router)
app.include_router(students.exam_router)
app.include_router(students.student_router)
app.include_router(answer_sheets.exam_router)
app.include_router(answer_sheets.answer_sheet_router)
app.include_router(question_papers.router)
app.include_router(evaluations.answer_router)
app.include_router(evaluations.evaluation_router)
app.include_router(evaluations.submission_router)
app.include_router(evaluations.exam_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
