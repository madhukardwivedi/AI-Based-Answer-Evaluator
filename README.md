# AI-Based Answer Evaluator — beginner setup

This application helps teachers read scanned answer sheets, review the extracted text, obtain AI-suggested marks, and approve or change those marks. You do not need AI or programming experience to try the demo. AI can misread handwriting or award incorrect marks: always compare the scan and review the result.

Start here, then follow the [step-by-step feature demo](docs/DEMO_GUIDE.md). The [demo file catalogue](demo/README.md) explains which files go together. No database backup or shared login is required.

## 1. What you will run

| Part | What it does | Local address |
|---|---|---|
| Frontend | Website you use in the browser | http://localhost:3000 |
| Backend | Handles uploads, saves data, calls AI | http://localhost:8000 |
| PostgreSQL | Stores exams, students and marks | Port 5432, managed by Docker |
| Ollama (optional) | Runs AI on your computer | http://localhost:11434 |

Choose **Ollama** for local AI without a key, or **OpenAI** for hosted AI with an API account and usage charges. You only need one AI provider. Both choices still need frontend, backend and PostgreSQL. Docker starts the database only.

## 2. Install prerequisites once

| Software | Version / choice | Installation |
|---|---|---|
| Python | Supports 3.11+; use **3.12** for the demo, matching the tested backend environment | [Python downloads](https://www.python.org/downloads/). On Windows enable the launcher/Add to PATH option. Avoid an untested newer Python for this demo. |
| Node.js and npm | Use **Node 22**; installed Next.js requires at least 20.9 | [Node 22 downloads](https://nodejs.org/en/download/archive/v22); npm is included. |
| Git | Current Git installer | [Git downloads](https://git-scm.com/downloads) |
| Docker Desktop | Install and open the application | [Docker Desktop](https://www.docker.com/products/docker-desktop/). Windows users: follow its [WSL 2 requirements](https://docs.docker.com/desktop/setup/install/windows-install/). |
| Editor | VS Code recommended; PyCharm also works; neither is required | [VS Code](https://code.visualstudio.com/Download) or [PyCharm](https://www.jetbrains.com/pycharm/download/) |
| Browser | Chrome, Edge, Firefox or Safari | Use an up-to-date browser. |
| Ollama | Only for local AI | [Ollama download](https://ollama.com/download) |

The existing local vision setup is an Apple M4 Pro with 16 GB RAM using `gemma3:4b`. This is a tested setup, not a guaranteed minimum. CPU-only machines can be much slower. Allow several GB for the model plus Docker and dependencies. OpenAI avoids running a local model but sends document content to the API and incurs usage charges.

Open **Terminal → New Terminal** in VS Code, macOS Terminal, or Windows PowerShell. Reopen the terminal after installing software. Paste one command block at a time; do not paste prompts such as `$` or `%`.

```bash
git --version
node --version
npm --version
docker --version
docker compose version
```

Check Python with `python3.12 --version` on macOS/Linux or `py -3.12 --version` on Windows. Linux users may also need their distribution's Python venv package.

## 3. Download and open the project

In a folder where you keep projects:

```bash
git clone https://github.com/madhukardwivedi/AI-Based-Answer-Evaluator.git
cd AI-Based-Answer-Evaluator
```

Use **File → Open Folder** in VS Code and select this folder, or open it in PyCharm. In PyCharm select `backend/.venv` as the interpreter after step 7. No paid IDE features or AI editor extensions are necessary.

The **project root** means the folder containing `README.md`, `backend`, `frontend`, and `docker-compose.yml`. Each new terminal below starts there unless stated otherwise.

## 4. Create private configuration

macOS/Linux:

```bash
cp .env.example .env
python3.12 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
py -3.12 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Open `.env` in your editor. Replace the value after `SECRET_KEY=` with the random value printed above. It secures login sessions; it is not an AI key. Keep the database defaults for the local demo. Save the file. Never share/commit `.env`, and do not copy over an existing configuration.

The backend reads the root `.env`. Next.js reads frontend environment files separately. No extra frontend file is necessary at the default addresses. If you change the backend address, create `frontend/.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000` adjusted to the new address, then restart frontend. Never put an AI key in a `NEXT_PUBLIC_` variable.

## 5. Choose an AI provider

### Option A — Ollama (local)

Keep these lines in the root `.env`:

```dotenv
AI_PROVIDER=auto
OPENAI_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TEXT_MODEL=gemma3:4b
OLLAMA_VISION_MODEL=gemma3:4b
OLLAMA_MAPPING_MODEL=gemma3:4b
OLLAMA_EVALUATION_MODEL=gemma3:4b
OLLAMA_NUM_CTX=
OLLAMA_TIMEOUT_SECONDS=180
```

Open Ollama, then run:

```bash
ollama --version
ollama pull gemma3:4b
ollama list
```

Wait for the model download to finish. If Ollama is not already serving, run `ollama serve` in another terminal and leave it open. “Address already in use” usually means it is already running. Open http://localhost:11434/api/tags in your browser; it should list `gemma3:4b`.

Leave `OLLAMA_NUM_CTX` blank. Large explicit contexts previously stalled this project's 16 GB Mac. The app does not default to qwen. Local AI can take minutes; do not repeatedly click while a request is running.

### Option B — OpenAI API (hosted)

1. Sign in to the [OpenAI API platform](https://platform.openai.com/).
2. Select/create an API project, arrange API billing/credits as required for your account, and check usage controls. A working ChatGPT login alone does not verify API quota.
3. Create a key on the [API keys page](https://platform.openai.com/api-keys). Keep it private.
4. In the **root `.env`**, set `AI_PROVIDER=auto`, paste your real key after `OPENAI_API_KEY=`, and keep `QUESTION_PARSER_MODEL=gpt-4.1-mini`.
5. Save, stop the backend with **Ctrl+C**, and restart using step 8. No frontend changes are needed. Ollama is unnecessary for this option.

Official setup: [OpenAI API quickstart](https://developers.openai.com/api/docs/quickstart). Monitor API usage during demos. Only send documents you are permitted to share with this provider.

**Model used by this project:** all OpenAI tasks share `QUESTION_PARSER_MODEL`, defaulting to `gpt-4.1-mini`. Despite the name, it is not limited to question-paper parsing. There are no separate OpenAI extraction/mapping/evaluation model variables.

| AI task | OpenAI default | Ollama demo setting |
|---|---|---|
| Digital question-paper parsing | `gpt-4.1-mini` | `OLLAMA_TEXT_MODEL=gemma3:4b` |
| Scanned question-paper parsing | `gpt-4.1-mini` | `OLLAMA_VISION_MODEL=gemma3:4b` |
| Student-answer page transcription | `gpt-4.1-mini` | `OLLAMA_VISION_MODEL=gemma3:4b` |
| Unresolved answer-to-question mapping | `gpt-4.1-mini` | `OLLAMA_MAPPING_MODEL=gemma3:4b` |
| Suggested marks and feedback | `gpt-4.1-mini` | `OLLAMA_EVALUATION_MODEL=gemma3:4b` |

`gpt-4.1-mini` supports image input and structured output used by the code: see the [official model page](https://developers.openai.com/api/docs/models/gpt-4.1-mini). This documents the existing default. Changing the shared setting affects every OpenAI task and needs compatibility testing.

With `AI_PROVIDER=auto`, a non-empty key selects OpenAI; an empty key selects Ollama. Invalid keys/timeouts do **not** trigger runtime fallback. To return to local AI, clear the key, keep `auto`, restart backend and start Ollama. Explicit `AI_PROVIDER=ollama` forces local AI. Shell environment variables override `.env`; remove stale exported values if settings appear ignored.

### Getting poor transcription? Try another model

The default `gpt-4.1-mini` is a baseline, **not a validated guarantee of faithful handwritten Maths OCR**. Alternatives to compare are `gpt-4.1` and `gpt-5.4`; neither has been benchmarked on this project's sheets. A larger model may still omit steps or correct student mistakes.

Open the **root `.env`**, find `QUESTION_PARSER_MODEL` (line **11** in a fresh copy of `.env.example`), and change only its value, for example:

```dotenv
QUESTION_PARSER_MODEL=gpt-4.1
```

Or trial `QUESTION_PARSER_MODEL=gpt-5.4`. Keep a valid OpenAI key and `AI_PROVIDER=auto`, save, and restart the backend. This changes **all OpenAI tasks**, not just parsing. Editing `.env.example` alone does not change your running application.

Read [Model choices and exact switching instructions](docs/MODEL_GUIDE.md) before testing: it includes file/line locations, safe comparison steps, cached-result behavior, costs/access considerations, Ollama controls, and rollback instructions. API compatibility and transcription quality must be checked separately.

## 6. Start PostgreSQL

Open Docker Desktop and wait for its engine to run. From project root:

```bash
docker compose up -d db
docker compose ps
```

Wait for `db` to be healthy. First startup downloads PostgreSQL 16. You do not need a separate PostgreSQL installation or manual table creation.

## 7. Install backend and create your login

macOS/Linux:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
alembic upgrade head
PYTHONPATH=. python ../scripts/create_evaluator.py
```

Windows PowerShell:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
alembic upgrade head
$env:PYTHONPATH = "."
python ..\scripts\create_evaluator.py
```

If PowerShell blocks activation, use a session-only policy and retry:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

`(.venv)` means your isolated Python environment is active. Alembic creates/updates tables; run it inside `backend`, not root. The account script asks for name, email and password (at least 8 characters). Password typing is hidden. Remember these credentials. There is no built-in shared login or public registration. Create your account once.

## 8. Start backend — terminal 1

In the same activated backend terminal:

```bash
uvicorn app.main:app --reload --port 8000
```

Leave it running. Expect `Application startup complete`. Check http://localhost:8000/health. Developer API documentation is at http://localhost:8000/docs; this is not the teacher-facing website.

## 9. Start website — terminal 2

Open a **new terminal in project root**:

```bash
cd frontend
npm ci
npm run dev
```

Leave it running. Open **http://localhost:3000**, sign in with your new account, and follow [the demo guide](docs/DEMO_GUIDE.md). Use `localhost` consistently instead of mixing it with `127.0.0.1`, so cookies and browser requests agree.

An empty dashboard is normal on a fresh installation. Sample files do not populate the database automatically; import/upload them through the guide.

## 10. Stop, restart, update

Stop frontend/backend with **Ctrl+C**. From root, `docker compose stop` stops PostgreSQL while retaining data. Keep both the database volume and uploaded files. Do not use `docker compose down -v` unless you intend to erase the database.

Next day:

1. Open Docker Desktop; from root run `docker compose up -d db`.
2. Start Ollama if using local AI.
3. Terminal 1: `cd backend`, activate the existing venv using step 7, then run `uvicorn app.main:app --reload --port 8000`.
4. Terminal 2: `cd frontend`, then `npm run dev`.
5. Open http://localhost:3000. Do not recreate the venv or evaluator account.

To update: stop both servers, run `git pull` from root, run `python -m pip install -r requirements.txt` and `alembic upgrade head` in the activated backend environment, run `npm ci` in frontend, and restart. Resolve local Git changes before pulling.

## Troubleshooting

| Symptom | What to check |
|---|---|
| Command not found / not recognized | Install the tool, reopen terminal, check its version. |
| Docker daemon unavailable | Start Docker Desktop; on Windows complete its WSL 2/virtualization setup. |
| Port 5432 occupied | Another PostgreSQL may be running. Stop the conflicting instance, or change Compose's host port and the matching `DATABASE_URL` port together. |
| Migration/database error | Run `docker compose ps` from root; wait for healthy. Check root `.env`. Run Alembic inside `backend`. |
| No module named app | Use backend working directory and the `PYTHONPATH` account-creation commands above. |
| Login fails | Use the evaluator account, not a demo student. Check backend terminal and consistent localhost URLs. |
| Website cannot reach API | Keep both servers running; check /health. Custom frontend API URLs belong in `frontend/.env.local`. |
| Ollama unavailable/model missing | Start Ollama; run `ollama list`, then `ollama pull gemma3:4b` if absent. |
| AI timeout | Close memory-heavy apps, leave context blank, try a small file. Do not force qwen on the tested 16 GB Mac. |
| OpenAI fails | Check key, API billing/quota and model access. Restart backend after editing `.env`; never share the key in logs. |
| Missing marks/duplicate import | Review candidates, enter visible marks, skip conflicts. Import does not overwrite existing questions. |
| Evaluation needs reference data | Add model answers/rubrics in Questions using the supplied Maths reference guide. |
| Wrong/missing transcription | Compare the scan and save a faithful transcription. Never repair the student's mathematics in their answer text. |
| Finalize disabled | Every exam question needs a reviewed evaluation or a faculty-confirmed unanswered result. |

## Verification for a technical helper

In `backend`, with venv active:

```bash
pytest
alembic current
alembic heads
```

In `frontend`:

```bash
npm run typecheck
npm run lint
npm run build
```

AI tests use mocks; passing them does not guarantee accurate handwriting recognition. The extraction page has a known Next.js `<img>` lint warning. Windows setup and paid OpenAI requests need separate live verification on the recipient's machine.

## Architecture and storage notes

Next.js/TypeScript/Tailwind frontend; FastAPI/SQLAlchemy/Alembic backend; PostgreSQL with Decimal/NUMERIC marks; JWT in HTTP-only cookies; local storage. Modular monolith; no Redis/Celery/microservices.

`STORAGE_ROOT=storage` resolves relative to the backend working directory with these launch commands, so new uploads normally go under `backend/storage/`. Use an absolute path for a different stable location. Changing it on an existing installation requires preserving its files. Uploads must stay out of Git.

Question-paper parsing uses Ollama `/api/chat`; extraction/mapping/evaluation use `/api/generate`. Both validate structured output. The parser uses `OLLAMA_TIMEOUT_SECONDS`; the shared provider currently has a fixed 180-second timeout. Processing/re-evaluation is explicit, not triggered by page refresh.

Directories: `backend/` (API/migrations/tests), `frontend/` (website), `scripts/` (account creation/parser diagnostics), `demo/` and `samples/` (synthetic demo materials), `docs/` (walkthrough/reference answers). Root sample PDFs keep their original paths for compatibility with the diagnostic script.

CSV/XLSX exports are available. PDF reports, student login, automatic combined-PDF splitting, queues and production deployment are outside the current MVP. Dashboard evaluated/pending counts are incomplete; use Evaluation and Results for actual demo progress.
