# AGENTS.md

# Project: AI-Based Answer Sheet Evaluation Portal

## 1. Project Goal

Build a web-based AI-powered answer sheet evaluation portal for teachers and evaluators.

The system should:

1. Allow evaluators to create an exam.
2. Upload a question paper.
3. Upload or enter model answers.
4. Upload or define a marking scheme/rubric.
5. Upload scanned student answer sheets in PDF/image format.
6. Extract handwritten or printed student answers using OCR/vision.
7. Map student answers to the correct question numbers.
8. Evaluate each answer using AI and the provided rubric.
9. Generate suggested marks, reasoning, evidence, missing concepts, and confidence.
10. Allow the evaluator to review, edit, approve, or override AI marks.
11. Calculate question-wise and total marks.
12. Generate student result reports.
13. Store exams, answer sheets, extracted answers, evaluations, and final results.

The AI must act as an evaluator assistant, not as an unquestionable final authority.

Human review must always be possible.

---

# 2. Core Product Principle

The system should follow this workflow:

```text
Question Paper
+
Model Answer
+
Marking Scheme
+
Student Answer
        ↓
   AI Evaluation
        ↓
Suggested Marks
+
Reasoning
+
Confidence
        ↓
Human Verification
        ↓
Final Marks
```

AI-generated marks are suggestions.

The evaluator must always be able to modify, approve, or reject them.

---

# 3. MVP Scope

The first working version should include only essential functionality.

## MVP Features

- Evaluator login
- Dashboard
- Create exam
- View exam
- Upload question paper
- Add/edit questions
- Add model answers
- Add marking criteria
- Add students
- Upload student answer sheets
- Process scanned answer sheets
- Extract answers
- Map answers to questions
- AI-based answer evaluation
- Question-wise marks
- Confidence scores
- Manual evaluator override
- Final mark calculation
- Result page
- Basic downloadable report

## Do NOT implement initially

Do not build these unless explicitly requested later:

- Student login
- Parent login
- Payment system
- School ERP integration
- Attendance system
- Mobile application
- Multi-tenant school architecture
- Advanced analytics
- Plagiarism detection
- LMS integration
- Complex role hierarchy
- Notifications
- Email automation
- Advanced billing
- Chatbot features

Keep the initial product focused.

---

# 4. Technology Stack

Use the following stack unless there is a strong technical reason not to.

## Frontend

Use:

- Next.js
- TypeScript
- React
- Tailwind CSS

Preferred approach:

- Next.js App Router
- Server and Client Components appropriately
- reusable UI components
- responsive design
- strict TypeScript

Use either native `fetch` or a centralized API client.

Do not unnecessarily mix multiple HTTP libraries.

## Backend

Use:

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL

## AI

Use the OpenAI API for:

- vision/OCR assistance
- question paper extraction
- answer segmentation
- semantic answer evaluation
- structured outputs

All important AI responses must use structured output and be validated using Pydantic.

## Document Processing

Use:

- PyMuPDF
- Pillow

Additional OCR/document-processing libraries may be introduced if they clearly improve reliability.

Do not rely solely on traditional OCR for handwritten answer sheets.

## Storage

For local MVP development:

- local file storage is acceptable

However, create a storage abstraction so that production can later use:

- AWS S3
- Azure Blob Storage
- Google Cloud Storage

## Deployment

Potential production targets:

Frontend:

- Vercel

Backend:

- Railway
- Render
- AWS

Database:

- PostgreSQL

Do not optimize deployment until the local MVP works correctly.

---

# 5. Repository Structure

Use a clean monorepo-style structure.

Recommended structure:

```text
ai-answer-evaluator/

├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── hooks/
│   ├── types/
│   ├── public/
│   ├── package.json
│   └── tsconfig.json
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── utils/
│   │   └── ai/
│   │
│   ├── tests/
│   ├── alembic/
│   ├── requirements.txt
│   └── pyproject.toml
│
├── storage/
├── docs/
├── scripts/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── README.md
└── AGENTS.md
```

Do not create unnecessary directories.

Do not introduce microservices during the MVP.

A modular monolith is preferred.

---

# 6. Backend Architecture

Use clear separation of concerns.

Recommended flow:

```text
API Route
    ↓
Service
    ↓
Repository
    ↓
Database
```

AI logic must remain separate from database and API logic.

Example:

```text
api/
    auth.py
    exams.py
    questions.py
    students.py
    answer_sheets.py
    evaluations.py
    results.py

services/
    auth_service.py
    exam_service.py
    question_service.py
    student_service.py
    answer_sheet_service.py
    evaluation_service.py
    document_service.py

repositories/
    user_repository.py
    exam_repository.py
    question_repository.py
    student_repository.py
    answer_sheet_repository.py
    evaluation_repository.py

ai/
    question_parser.py
    answer_extractor.py
    evaluator.py
    prompts/
```

Do not put significant business logic directly in FastAPI route handlers.

---

# 7. Core Database Entities

At minimum, design models for the following entities.

## User

Suggested fields:

- id
- name
- email
- password_hash
- role
- created_at
- updated_at

Initial supported role:

- evaluator

---

## Exam

Suggested fields:

- id
- created_by
- name
- subject
- class_name
- description
- total_marks
- status
- created_at
- updated_at

Possible status values:

- draft
- configured
- processing
- completed

---

## Question

Suggested fields:

- id
- exam_id
- question_number
- parent_question_id
- question_text
- model_answer
- maximum_marks
- sequence_order
- created_at
- updated_at

Question numbers must be strings, not integers.

Examples:

```text
1
2
2(a)
2(b)
Q3
Section A - Q1
```

---

## RubricCriterion

Suggested fields:

- id
- question_id
- criterion
- description
- maximum_marks
- sequence_order

Example:

```json
{
  "criterion": "Explains role of chlorophyll",
  "description": "Student should explain that chlorophyll absorbs light energy.",
  "maximum_marks": 1
}
```

---

## Student

Suggested fields:

- id
- exam_id
- name
- roll_number
- external_id
- created_at
- updated_at

---

## AnswerSheet

Suggested fields:

- id
- exam_id
- student_id
- original_filename
- file_path
- status
- uploaded_at
- processing_started_at
- processing_completed_at
- processing_error

Possible statuses:

- uploaded
- processing
- extracted
- evaluated
- review_required
- completed
- failed

---

## AnswerSheetPage

Suggested fields:

- id
- answer_sheet_id
- page_number
- image_path
- extracted_text
- extraction_confidence
- created_at

---

## StudentAnswer

Suggested fields:

- id
- answer_sheet_id
- question_id
- detected_question_number
- answer_text
- page_numbers
- extraction_confidence
- manually_corrected
- created_at
- updated_at

---

## Evaluation

Suggested fields:

- id
- student_answer_id
- ai_marks
- manual_marks
- final_marks
- maximum_marks
- confidence
- strengths
- missing_points
- feedback
- reasoning
- status
- ai_model
- prompt_version
- created_at
- updated_at

Possible statuses:

- pending
- ai_evaluated
- review_required
- approved
- manually_modified

---

# 8. Database Relationships

Use relationships approximately as follows:

```text
User
  └── Exams

Exam
  ├── Questions
  │    └── RubricCriteria
  ├── Students
  └── AnswerSheets

Student
  └── AnswerSheets

AnswerSheet
  ├── AnswerSheetPages
  └── StudentAnswers

Question
  └── StudentAnswers

StudentAnswer
  └── Evaluation
```

Use foreign keys and appropriate indexes.

Do not duplicate data unnecessarily.

---

# 9. REST API Design

Use REST APIs with a consistent `/api` prefix.

## Authentication

```text
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me
```

## Exams

```text
GET    /api/exams
POST   /api/exams
GET    /api/exams/{exam_id}
PUT    /api/exams/{exam_id}
DELETE /api/exams/{exam_id}
```

## Questions

```text
GET    /api/exams/{exam_id}/questions
POST   /api/exams/{exam_id}/questions
GET    /api/questions/{question_id}
PUT    /api/questions/{question_id}
DELETE /api/questions/{question_id}
```

## Question Paper

```text
POST /api/exams/{exam_id}/question-paper
POST /api/exams/{exam_id}/question-paper/parse
```

## Students

```text
GET    /api/exams/{exam_id}/students
POST   /api/exams/{exam_id}/students
GET    /api/students/{student_id}
PUT    /api/students/{student_id}
DELETE /api/students/{student_id}
```

## Answer Sheets

```text
POST /api/exams/{exam_id}/answer-sheets
GET  /api/exams/{exam_id}/answer-sheets
GET  /api/answer-sheets/{answer_sheet_id}
POST /api/answer-sheets/{answer_sheet_id}/process
```

## Extracted Answers

```text
GET /api/answer-sheets/{answer_sheet_id}/answers
GET /api/student-answers/{answer_id}
PUT /api/student-answers/{answer_id}
```

## Evaluations

```text
POST /api/student-answers/{answer_id}/evaluate
GET  /api/student-answers/{answer_id}/evaluation
PUT  /api/evaluations/{evaluation_id}
POST /api/evaluations/{evaluation_id}/approve
POST /api/evaluations/{evaluation_id}/reevaluate
```

## Results

```text
GET /api/exams/{exam_id}/results
GET /api/students/{student_id}/result
```

Do not expose internal implementation details through the API.

---

# 10. Question Paper Parsing

The system should be able to extract questions from an uploaded question paper.

Supported input:

- PDF
- JPG
- JPEG
- PNG

Expected structured output:

```json
{
  "exam_title": "",
  "questions": [
    {
      "question_number": "1",
      "question_text": "",
      "maximum_marks": 5,
      "sub_questions": []
    }
  ]
}
```

Requirements:

- preserve question numbering
- detect subquestions
- detect maximum marks where possible
- preserve section structure where possible
- allow evaluator correction
- do not silently overwrite manually configured questions
- validate parsed output before saving

---

# 11. Answer Sheet Processing

Uploaded answer sheets may contain handwritten or printed responses.

Recommended pipeline:

```text
PDF/Image
    ↓
Page Extraction
    ↓
Image Preprocessing
    ↓
Vision/OCR
    ↓
Question Number Detection
    ↓
Answer Segmentation
    ↓
Question Mapping
    ↓
Structured Student Answers
```

Important real-world cases:

- answers may continue across multiple pages
- students may answer questions in a different order
- handwriting quality may vary
- question numbers may be handwritten
- students may skip questions
- answers may contain diagrams
- answers may contain mathematical notation
- answers may contain tables
- answers may contain crossed-out text
- multiple answers may exist on one page
- one answer may span multiple pages
- students may write additional answers at the end

Always preserve the original scanned pages.

Never discard the source image after extraction.

---

# 12. OCR / Vision Strategy

Do not assume OCR output is correct.

For every extracted answer preserve:

- original page reference
- extracted text
- detected question number
- page numbers
- extraction confidence

Evaluator must be able to compare OCR output with the original scanned page.

If OCR confidence is low:

- flag the answer
- do not silently proceed as if extraction were correct

Where needed, use a vision-capable model instead of pure OCR.

---

# 13. AI Evaluation Engine

The AI evaluator should receive:

- question
- model answer
- rubric
- student answer
- maximum marks

Do not evaluate using simple textual similarity.

Evaluate using semantic understanding and rubric-based scoring.

Expected output:

```json
{
  "marks_awarded": 3.5,
  "max_marks": 5,
  "confidence": 0.86,
  "criteria": [
    {
      "criterion": "Explains concept A",
      "max_marks": 1,
      "awarded_marks": 1,
      "evidence": "Relevant text from the student answer"
    }
  ],
  "strengths": [
    "Correctly explained concept A"
  ],
  "missing_points": [
    "Did not explain concept B"
  ],
  "feedback": "Good answer but missing...",
  "reasoning": "The response covers..."
}
```

All AI output must be structured and validated with Pydantic.

Never depend on parsing uncontrolled prose for marks.

---

# 14. AI Evaluation Rules

The evaluator must follow these rules:

1. Never exceed maximum marks.
2. Do not award negative marks unless negative marking is explicitly configured.
3. Accept semantically equivalent answers.
4. Allow partial credit.
5. Evaluate rubric criteria independently where practical.
6. Do not penalize grammar unless grammar is part of the rubric.
7. Do not penalize spelling unless spelling is part of the rubric.
8. Ignore irrelevant information unless it contradicts the answer.
9. Use evidence from the student's response.
10. Do not assume information that is not written.
11. Do not fabricate student content.
12. If OCR/extraction is unclear, lower confidence.
13. If evaluation is ambiguous, flag for human review.
14. Do not infer quality from answer length.
15. Do not prefer wording merely because it resembles the model answer.
16. Do not treat the model answer as the only valid wording.
17. Never award marks solely because keywords appear.
18. Consider the actual meaning and correctness of the answer.
19. Respect the rubric's maximum marks per criterion.
20. Ensure criterion-level marks add up consistently.

---

# 15. Confidence System

Use confidence values between:

```text
0.0 and 1.0
```

Confidence should consider:

- OCR quality
- answer completeness
- question-answer mapping certainty
- rubric coverage
- semantic ambiguity
- model evaluation certainty

Suggested thresholds:

```text
0.85 - 1.00
High confidence

0.65 - 0.84
Moderate confidence

Below 0.65
Mandatory human review
```

Thresholds should ultimately be configurable.

Do not present confidence as mathematically guaranteed probability unless it actually is calibrated.

---

# 16. Human Review

Human review is a core requirement.

The evaluator should be able to see:

- original scanned answer page
- extracted text
- question
- model answer
- rubric
- AI marks
- criterion-level breakdown
- AI feedback
- AI reasoning
- AI confidence
- manual marks
- final marks

Evaluator actions:

- approve AI marks
- modify marks
- correct OCR text
- re-run evaluation
- flag answer
- add evaluator notes

Manual modification must preserve the original AI evaluation.

---

# 17. Frontend Pages

Implement the following pages.

## Authentication

```text
/login
```

## Dashboard

```text
/dashboard
```

Show:

- total exams
- active exams
- uploaded answer sheets
- evaluated sheets
- pending reviews

## Exams

```text
/exams
/exams/new
/exams/[id]
```

## Questions

```text
/exams/[id]/questions
```

Evaluator should be able to:

- add question
- edit question
- delete question
- add model answer
- add rubric
- set maximum marks

## Students

```text
/exams/[id]/students
```

## Answer Sheet Upload

```text
/exams/[id]/upload
```

Support:

- drag-and-drop
- multiple files
- PDF
- JPG
- JPEG
- PNG
- upload progress
- upload errors

## Evaluation

```text
/exams/[id]/evaluation
```

Preferred layout:

```text
---------------------------------------------------------
| Original Answer Sheet | Evaluation Panel              |
|                       |                               |
| Scanned page          | Question                      |
|                       | Extracted Answer               |
|                       | Model Answer                   |
|                       | Rubric                         |
|                       | AI Marks                       |
|                       | Rubric Breakdown               |
|                       | Confidence                     |
|                       | Final Marks                    |
|                       | Approve / Modify / Reevaluate  |
---------------------------------------------------------
```

## Results

```text
/exams/[id]/results
```

Show:

- student
- roll number
- question-wise marks
- total marks
- percentage
- review status

---

# 18. UI Requirements

The interface should be:

- professional
- clean
- modern
- suitable for schools/universities
- easy for teachers
- responsive
- accessible

Avoid excessive animations.

Prioritize usability over visual effects.

Use consistent:

- typography
- spacing
- buttons
- cards
- tables
- status badges
- loading indicators
- empty states
- error states
- confirmation dialogs

Do not use placeholder-looking AI-generated UI if a simpler professional interface is better.

---

# 19. Authentication

For MVP, implement simple evaluator authentication.

Requirements:

- passwords must be hashed
- plaintext passwords must never be stored
- protected endpoints require authentication
- frontend must handle unauthenticated states
- do not expose authentication secrets to frontend code

Do not overengineer authorization initially.

Only evaluator role is necessary for MVP.

---

# 20. Security

Follow standard application-security practices.

Requirements:

- never expose OpenAI/API secrets in frontend code
- use environment variables
- password hashing
- input validation
- file-type validation
- file-size validation
- safe filenames
- prevent path traversal
- sanitize unsafe inputs where appropriate
- CORS configuration
- SQL injection protection through ORM
- safe exception handling
- do not return stack traces in production
- do not commit secrets

Create:

```text
.env.example
```

Never put a real API key in `.env.example`.

---

# 21. Privacy

Answer sheets may contain personal educational data.

Therefore:

- avoid unnecessary logging of student content
- never log API keys
- avoid logging complete answer sheets
- separate files by exam/student where practical
- preserve auditability
- minimize unnecessary external data transfers
- only send required content to AI services
- avoid retaining temporary files longer than necessary

---

# 22. Auditability

Every final evaluation should preserve:

- original student answer
- original extracted text
- original AI output
- AI model name
- prompt version
- timestamp
- AI marks
- manual marks
- final marks
- evaluator action

Manual changes must not overwrite the original AI result.

This is critical for transparency and debugging.

---

# 23. Prompt Management

Do not scatter prompts throughout the codebase.

Store prompts centrally.

Recommended location:

```text
backend/app/ai/prompts/
```

Every production evaluation should store a prompt version.

Example:

```text
evaluation_v1
question_parser_v1
answer_extractor_v1
```

Prompt changes should be explicit and traceable.

---

# 24. Deterministic Logic

Do not use AI for tasks that ordinary application code can perform reliably.

Use deterministic code for:

- totals
- percentages
- maximum-mark validation
- status calculations
- IDs
- timestamps
- database filtering
- simple formatting
- arithmetic

Example:

```text
Question 1: 4 / 5
Question 2: 7 / 10
Question 3: 3.5 / 5

Total: 14.5 / 20
```

The backend should calculate this.

Do not ask the AI to calculate the final total.

---

# 25. Error Handling

Explicitly handle:

- unsupported file format
- corrupt PDF
- empty file
- OCR failure
- vision failure
- AI API failure
- AI timeout
- malformed AI response
- failed Pydantic validation
- missing question
- missing model answer
- missing rubric
- missing student
- database failure
- duplicate student
- duplicate roll number
- duplicate answer sheet
- failed mark calculation

Never silently fail.

Return meaningful API errors and show useful frontend messages.

---

# 26. File Upload Rules

Validate uploads.

Allowed answer-sheet formats initially:

- PDF
- JPG
- JPEG
- PNG

Validate:

- extension
- MIME type where possible
- file size
- filename
- empty file

Generate safe server-side names instead of blindly trusting uploaded filenames.

Keep the original filename as metadata.

---

# 27. AI Cost Awareness

AI API calls may become expensive.

Design the application to avoid repeated unnecessary calls.

Use:

- cached question-paper parsing
- stored OCR results
- stored extracted answers
- stored evaluations
- re-evaluation only when explicitly requested
- page-level processing where appropriate
- answer-level evaluation instead of repeatedly sending entire documents

Do not resend the full question paper or answer sheet when only one answer is needed.

---

# 28. Performance

For the initial MVP, synchronous processing may be acceptable for small files.

However, keep long-running logic inside service boundaries so it can later move to background workers.

Potential long-running operations:

- PDF rendering
- OCR
- vision processing
- answer segmentation
- batch evaluations
- report generation

Eventually these can move to:

- Redis
- Celery
- RQ
- another job queue

Do not introduce a queue until necessary.

---

# 29. Testing

Write tests for important backend functionality.

At minimum test:

- authentication
- exam CRUD
- question CRUD
- student CRUD
- answer-sheet upload
- file validation
- answer extraction schema
- evaluation schema
- mark validation
- final score calculation

Important invariant:

```text
final_marks <= maximum_marks
```

Also validate:

```text
ai_marks <= maximum_marks
manual_marks <= maximum_marks
```

Do not allow negative values unless specifically configured.

Frontend tests should focus on important flows rather than trying to test every visual component.

---

# 30. Python Coding Standards

Use:

- type hints
- Pydantic models
- SQLAlchemy models
- descriptive naming
- small functions
- service boundaries
- dependency injection where appropriate
- async only where it provides value

Avoid:

- giant route handlers
- duplicated logic
- wildcard imports
- global mutable state
- hidden side effects
- unexplained magic values

---

# 31. TypeScript Coding Standards

Use:

- strict TypeScript
- reusable components
- explicit interfaces/types
- typed API responses
- centralized API client where useful
- clear server/client boundaries

Avoid:

- `any` unless absolutely necessary
- duplicated API code
- giant page components
- deeply nested prop drilling when a simpler pattern exists
- unnecessary state-management libraries

---

# 32. Environment Variables

Use environment variables for values such as:

```text
DATABASE_URL
OPENAI_API_KEY
SECRET_KEY
BACKEND_URL
NEXT_PUBLIC_API_URL
```

Only variables intentionally safe for the browser may use:

```text
NEXT_PUBLIC_
```

Never expose:

```text
OPENAI_API_KEY
DATABASE_URL
SECRET_KEY
```

to frontend code.

---

# 33. README Requirements

Maintain a useful `README.md`.

README should explain:

- project purpose
- architecture
- prerequisites
- setup
- environment variables
- backend setup
- frontend setup
- PostgreSQL setup
- migrations
- how to run locally
- how to run tests
- project structure

Update README whenever setup instructions change.

---

# 34. Git Practices

Use Git.

Do not commit:

- `.env`
- API keys
- `node_modules`
- Python virtual environments
- uploaded answer sheets
- generated student data
- local databases
- temporary files
- caches

Create a proper `.gitignore`.

Prefer small logical commits.

---

# 35. Development Approach

Do NOT attempt to implement the entire project at once.

Work in phases.

---

# PHASE 1 — Foundation

Implement:

- project structure
- frontend scaffold
- backend scaffold
- PostgreSQL configuration
- SQLAlchemy
- Alembic
- basic authentication
- database models
- health endpoint
- exam CRUD
- question CRUD
- Docker Compose
- README
- `.env.example`
- `.gitignore`

Do NOT implement AI yet.

Success criteria:

- frontend starts
- backend starts
- database connects
- migrations work
- authentication works
- exam CRUD works
- question CRUD works
- tests for basic backend functionality pass

---

# PHASE 2 — Core Portal

Implement:

- dashboard
- exam creation UI
- exam details
- question editor
- model-answer editor
- rubric editor
- student management
- answer-sheet upload UI
- answer-sheet storage

Success criteria:

Evaluator can:

- sign in
- create exam
- configure questions
- configure model answers
- configure rubrics
- add students
- upload answer sheets

No AI evaluation is required yet.

---

# PHASE 3 — Question Paper Intelligence

Implement:

- PDF processing
- PDF page rendering
- image input handling
- question-paper parsing
- question detection
- subquestion detection
- marks detection
- structured response
- correction/edit UI

Success criteria:

An uploaded question paper can be converted into editable structured questions.

---

# PHASE 4 — Answer Sheet Extraction

Implement:

- PDF/image processing
- page extraction
- image preprocessing
- OCR/vision extraction
- question-number detection
- answer segmentation
- multi-page answers
- question mapping
- extracted-answer editor
- extraction confidence

Success criteria:

Uploaded answer sheets produce structured question-wise student answers.

---

# PHASE 5 — AI Evaluation

Implement:

- evaluation prompt
- structured evaluation schema
- rubric-based scoring
- semantic grading
- partial credit
- evidence extraction
- feedback
- confidence
- human-review flag

Success criteria:

Each student answer receives:

- AI marks
- maximum marks
- criterion breakdown
- evidence
- strengths
- missing points
- feedback
- confidence

---

# PHASE 6 — Human Review

Implement:

- side-by-side scanned answer viewer
- extracted answer
- evaluation panel
- manual mark override
- approve action
- OCR correction
- re-evaluation
- reviewer notes

Success criteria:

Evaluator can inspect and finalize each answer.

---

# PHASE 7 — Results

Implement:

- question-wise results
- total marks
- percentages
- student result page
- exam result page
- review status
- report generation

Optional after core functionality works:

- PDF export
- CSV export
- Excel export

---

# PHASE 8 — Production Hardening

Only after the MVP works.

Potential additions:

- cloud object storage
- stronger production authentication
- Redis
- background workers
- job queue
- rate limiting
- monitoring
- production logging
- deployment
- backups
- advanced audit logs
- retry policies
- observability

Do not implement these prematurely.

---

# 36. Important AI Development Rule

Never blindly trust AI output.

Every important AI call must have:

1. defined input data
2. explicit prompt
3. defined output schema
4. server-side validation
5. error handling
6. retry strategy where appropriate
7. confidence handling where relevant
8. human-review path

Do not parse critical marks from arbitrary free-form text.

---

# 37. Important OCR Rule

Never assume OCR text is correct.

Preserve:

- original page
- extracted text
- page references
- extraction confidence
- manual corrections

The evaluator must be able to compare extracted text against the original scan.

---

# 38. Important Marking Rule

Marks must be validated by backend logic.

Rules:

```text
0 <= awarded marks <= maximum marks
```

unless negative marking is explicitly configured later.

Criterion marks must not collectively exceed the question maximum.

Final score calculation must be deterministic.

---

# 39. Architecture Decisions

Before adding a major dependency or pattern:

1. inspect the existing repository
2. reuse current architecture where reasonable
3. avoid unnecessary dependencies
4. explain why a new dependency is required

Do not create multiple competing approaches for the same task.

Examples:

Do not use both:

```text
Axios AND fetch everywhere
```

or:

```text
two different ORM patterns
```

or:

```text
multiple authentication systems
```

without a strong reason.

---

# 40. Codex Working Rules

Whenever implementing a task:

1. Read this entire `AGENTS.md`.
2. Inspect relevant existing files.
3. Understand the current implementation.
4. Plan the smallest correct change.
5. Reuse existing conventions.
6. Implement the feature.
7. Run relevant tests.
8. Run lint/type checks.
9. Fix errors introduced by the change.
10. Update documentation if necessary.
11. Summarize what changed.
12. Mention unresolved issues.

Do not modify unrelated functionality.

Do not perform large unrelated refactors.

Do not remove working functionality without explanation.

---

# 41. Before Writing Code

For substantial tasks, first inspect the project.

Before implementation, identify:

- affected frontend files
- affected backend files
- affected database models
- migrations required
- APIs required
- tests required

Do not generate large amounts of code without first understanding existing code.

---

# 42. When Debugging

Do not immediately patch symptoms.

Use this process:

1. reproduce the issue
2. inspect relevant logs/errors
3. trace data flow
4. identify root cause
5. implement the smallest correct fix
6. run relevant tests
7. check related functionality for regressions

Example flow:

```text
Frontend
   ↓
API
   ↓
Service
   ↓
Repository
   ↓
Database
```

For AI/document problems:

```text
Upload
   ↓
Storage
   ↓
PDF/Image Processing
   ↓
OCR/Vision
   ↓
Segmentation
   ↓
Question Mapping
   ↓
Evaluation
```

---

# 43. Before Large Architectural Changes

Before making a large architectural change:

- explain the proposed change
- explain why it is necessary
- list likely affected files
- mention migration implications
- mention risks
- wait for approval unless explicitly told to proceed

---

# 44. Definition of Done

A feature is not done merely because code was written.

A feature is complete when:

- implementation exists
- typing passes
- linting passes
- relevant tests pass
- validation exists
- errors are handled
- frontend has loading state where appropriate
- frontend has error state where appropriate
- no secrets were introduced
- documentation is updated if needed
- existing functionality still works

---

# 45. MVP Priorities

The immediate goal is to build a functioning MVP quickly without creating an unmaintainable system.

Prioritize:

1. correctness
2. simplicity
3. usability
4. maintainability
5. implementation speed
6. AI reliability
7. cost awareness

Avoid:

- premature optimization
- unnecessary infrastructure
- unnecessary abstractions
- overly complex design patterns
- microservices
- unnecessary third-party libraries

---

# 46. Key Product Risks

Be aware of these risks throughout development.

## Handwriting Recognition

Handwritten OCR may be inaccurate.

Mitigation:

- preserve scans
- confidence scores
- manual correction
- vision models
- human verification

## Answer Segmentation

Identifying where one answer ends and another begins can be difficult.

Mitigation:

- question-number detection
- page context
- AI-based segmentation
- evaluator correction

## Question Mapping

Students may answer questions out of order.

Mitigation:

- do not map answers based only on page sequence
- detect question identifiers
- use semantic/contextual mapping when needed

## AI Evaluation Consistency

AI may produce varying scores.

Mitigation:

- rubric-based evaluation
- structured output
- low randomness
- prompt versioning
- regression tests
- human review

## Hallucination

AI may infer content that the student never wrote.

Mitigation:

- require evidence from student text
- prohibit invented content
- reduce confidence for ambiguity
- expose reasoning to evaluator

## Cost

Large batches can create significant API usage.

Mitigation:

- store OCR output
- cache parsing results
- evaluate answer-by-answer
- avoid unnecessary reprocessing

---

# 47. Initial Development Assumptions

For the first MVP assume:

- one evaluator role
- relatively small number of students
- answer sheets are primarily PDF/JPG/PNG
- local storage is acceptable
- PostgreSQL is available locally or via Docker
- AI API usage is acceptable during development
- evaluator manually verifies questionable results
- no institutional ERP integration is required

These assumptions may change later.

---

# 48. First Task for Codex

When first working in this repository:

DO NOT implement the full application immediately.

First:

1. inspect the repository
2. read this entire `AGENTS.md`
3. identify prerequisites
4. propose the final repository structure
5. propose database tables and relationships
6. propose REST endpoints
7. propose Phase 1 implementation steps
8. identify technical risks
9. identify anything that should be simplified
10. identify required local software

Then stop.

Wait for approval before implementing Phase 1.

---

# 49. First Codex Response Format

The first analysis should be organized as:

## A. Architecture

Explain the proposed architecture.

## B. Repository Structure

Show the proposed directory structure.

## C. Database

List entities, relationships, and important constraints.

## D. API

List the proposed endpoints.

## E. Local Prerequisites

List software required on the developer machine.

## F. Phase 1 Plan

Provide an ordered implementation plan.

## G. Risks

Identify technical risks, especially:

- handwriting OCR
- answer segmentation
- AI scoring reliability
- cost
- privacy

## H. MVP Simplifications

Recommend any changes that will allow the MVP to be completed faster without damaging the architecture.

After this analysis:

STOP AND WAIT FOR APPROVAL.

Do not create project files until approval is explicitly given.