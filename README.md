# AI Answer Sheet Evaluation Portal

A practical, human-in-the-loop answer evaluation portal for educators. The current MVP supports question-paper parsing, student uploads, answer extraction, AI-assisted rubric evaluation, faculty overrides, final totals, and CSV results.

## Architecture

- Frontend: Next.js App Router, TypeScript, Tailwind CSS.
- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic.
- Database: PostgreSQL, using NUMERIC(10,2) / Python Decimal for marks.
- Authentication: evaluator-only JWTs in HTTP-only cookies.
- Storage: a local storage abstraction for answer sheets and question papers, configured by STORAGE_ROOT and replaceable with cloud storage later.
- Deployment shape: a modular monolith; no microservices, Redis, Celery, or queue infrastructure.

The backend follows route → service → repository → database. Business rules and ownership checks live in services; routes stay thin.

## Prerequisites

- Git
- Docker Desktop
- Python 3.11+
- Node.js 20 LTS+ and npm

## Setup

1. Copy the example environment file:

       cp .env.example .env

   Replace SECRET_KEY with a long random value. Never commit .env.

2. Start PostgreSQL:

       docker compose up -d db

3. Install backend dependencies and migrate:

       cd backend
       python3 -m venv .venv
       source .venv/bin/activate
       pip install -r requirements.txt
       alembic upgrade head

4. Create the first evaluator account:

       PYTHONPATH=. python ../scripts/create_evaluator.py

5. Start the API:

       uvicorn app.main:app --reload --port 8000

6. In another terminal, install and start the frontend:

       cd frontend
       npm install
       npm run dev

Open http://localhost:3000. API documentation is available at http://localhost:8000/docs.

## Verification

Backend:

    cd backend
    source .venv/bin/activate
    pytest

Frontend:

    cd frontend
    npm run lint
    npm run typecheck

## Available API

- GET /health
- POST /api/auth/login, POST /api/auth/logout, GET /api/auth/me
- CRUD: /api/exams
- CRUD: /api/exams/{exam_id}/questions, /api/questions/{question_id}
- CRUD: /api/questions/{question_id}/rubric-criteria, /api/rubric-criteria/{criterion_id}
- CRUD: /api/exams/{exam_id}/students, /api/students/{student_id}
- POST /api/exams/{exam_id}/students/import (CSV/XLSX roster; `name` required, `roll_number` and `external_id` optional)
- POST/GET: /api/exams/{exam_id}/answer-sheets
- GET/DELETE/POST process: /api/answer-sheets/{answer_sheet_id}
- GET/PUT/evaluate: /api/student-answers/{answer_id}
- GET/PATCH/approve/reevaluate: /api/evaluations/{evaluation_id}
- POST /api/student-submissions/{submission_id}/evaluate, /finalize, and /reset-evaluations
- GET /api/student-submissions/{submission_id}/report (report-ready JSON)
- GET /api/exams/{exam_id}/results, /results.csv, and /results.xlsx
- POST/GET/DELETE: /api/exams/{exam_id}/question-paper
- POST: /api/exams/{exam_id}/question-paper/parse and /import

## Question-paper intelligence (Phase 3)

Set `AI_PROVIDER=auto` in the root `.env`. With a non-empty `OPENAI_API_KEY`, the backend selects OpenAI; without one, it selects Ollama. It never switches providers after a runtime error. `QUESTION_PARSER_MODEL` defaults to `gpt-4.1-mini`; `gemma3:4b` is the default and recommended local Ollama text, vision, mapping, and evaluation model for the current 16 GB development setup.

### Local Ollama setup

Install Ollama from [ollama.com](https://ollama.com), then run:

    ollama --version
    ollama pull gemma3:4b
    ollama serve

In another terminal, verify the local service and model:

    curl http://localhost:11434/api/tags
    ollama list

`gemma3:4b` is recommended locally for question-paper parsing, scanned-document understanding, mark extraction, answer mapping, and evaluation on the current 16 GB development machine. For digital PDFs the backend sends PyMuPDF-extracted text to `OLLAMA_TEXT_MODEL`; for scanned PDFs and image uploads it sends PyMuPDF/Pillow-rendered page images to `OLLAMA_VISION_MODEL`. Other installed Ollama models may be substituted through these environment variables, but the application does not fall back to `qwen3-vl:8b` by default.

Answer extraction first maps normalized labels such as `1`, `Q.1`, `Question 1`, `3a`, and `10b` to configured exam questions deterministically. Only segments without a unique label match are sent to the optional semantic mapper. Its local model and confidence threshold are configured with `OLLAMA_MAPPING_MODEL=gemma3:4b`, `AI_MAPPING_ENABLED=true`, and `AI_MAPPING_CONFIDENCE_THRESHOLD=0.80`; if `OLLAMA_MAPPING_MODEL` is left blank, the backend uses `OLLAMA_TEXT_MODEL`. Lower-confidence results remain available for manual mapping.

AI evaluation uses `OLLAMA_EVALUATION_MODEL=gemma3:4b` by default; if it is left blank, the backend uses `OLLAMA_TEXT_MODEL`. A question is evaluatable when it has a model answer, other reference data, or rubric criteria. Rubric questions are scored criterion-by-criterion and totaled in backend Decimal arithmetic; questions without a rubric use semantic comparison against the configured reference data. AI marks remain suggestions until faculty accepts or overrides them and explicitly finalizes the submission.

Leave `OLLAMA_NUM_CTX=` blank for local development unless you have verified a specific value works on your machine. When blank, the application omits `num_ctx` entirely and lets Ollama use its stable default. Larger contexts substantially increase unified-memory use and may stall on 16 GB machines. `OLLAMA_TIMEOUT_SECONDS=180` remains the local request timeout.

For temporary local parser troubleshooting only, set `QUESTION_PARSER_DEBUG_OUTPUT=true`. The backend will print the raw model response when parsing fails. It can contain document text, so keep it `false` outside local debugging and turn it off after collecting the error.

## Repository Layout

    frontend/    Next.js user interface
    backend/     FastAPI application, migrations, and tests
    storage/     ignored local storage placeholder for later phases
    scripts/     administrative utilities

## Evaluation demo flow

1. Configure questions, maximum marks, and either model/reference data or rubric criteria. Optional reference fields include key concepts, acceptable alternatives, reference solution, and marking notes.
2. Add a student and upload their PDF/JPG/PNG answer sheet.
3. Select **Process / Extract**, then use **Extraction** to correct text or question mapping.
4. Open **Evaluation**, evaluate one answer or all mapped answers, review criterion details, accept or override marks, and add faculty remarks.
5. Explicitly finalize the student evaluation.
6. Open **Results** for deterministic totals and download CSV or XLSX. The submission report endpoint provides data for a future PDF renderer.

The current scope still excludes background workers, student-answer PDF splitting, student/parent logins, advanced analytics, and PDF reports.

## Student roster import

The **Students** page retains manual entry and also accepts a CSV or XLSX roster. The first non-empty row is treated as headers; supported case-insensitive headers are `name`, `roll number`, `roll_number`, `roll no`, `external id`, and `external_id`. Download the CSV template from the page, or use [samples/student-roster-sample.csv](samples/student-roster-sample.csv). Imports trim fields, ignore blank rows, skip duplicate roll numbers or external IDs with row-level feedback, and commit valid rows together. `MAX_STUDENT_IMPORT_SIZE_BYTES` defaults to 2 MB.
