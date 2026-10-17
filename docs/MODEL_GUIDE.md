# Trying another AI model when results are poor

## What is and is not established

The application's OpenAI default is `gpt-4.1-mini`. It accepts images and structured output, but we have **not run a comparative live OpenAI benchmark on these answer sheets**. Mocked tests verify application behavior, not whether a model reads handwriting correctly. Gemma has had limited live synthetic-page testing, not comprehensive handwriting validation.

Do not choose a model because its answer is mathematically better. Choose it because it copies the student's visible work faithfully, including incorrect work. Valid JSON and high reported confidence do not prove transcription accuracy.

## OpenAI models to compare

These are explicit trial candidates, not a measured accuracy ranking. Check current model access and pricing in your API project before running a full exam.

| Exact model ID | Why try it | Project evidence / caution |
|---|---|---|
| `gpt-4.1-mini` | Existing economical baseline for structured text and image tasks | Keep as the comparison baseline; handwritten Maths fidelity is unvalidated. |
| `gpt-4.1` | Full-size model in the same family; a useful comparison when mini misses content | Supports image input and structured outputs. No measured improvement on our sheets yet; compare actual transcripts and cost. |
| `gpt-5.4` | Candidate for difficult document/handwriting extraction; OpenAI publishes document-understanding guidance for it | Supports image input and structured outputs. Not live-verified with this project's pinned SDK and schemas; test one small request before batch use. |

Official sources: [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini), [GPT-4.1](https://developers.openai.com/api/docs/models/gpt-4.1), [GPT-5.4](https://developers.openai.com/api/docs/models/gpt-5.4), and [GPT-5.4 document-understanding guidance](https://developers.openai.com/cookbook/examples/multimodal/document_and_multimodal_understanding_tips). Model support does not guarantee access for your account, availability forever, or accuracy on your scans.

Our current code sends images with `detail="high"`. The GPT-5.4 guidance discusses `detail="original"` for difficult handwriting and crop-and-rerun inspection. **Changing the model name does not enable those techniques.** They need separate, model-compatible implementation and testing. Do not add undocumented environment variables expecting to enable them.

## Exactly which file and line to edit

Edit **`.env` in the project root**, beside `README.md` and `docker-compose.yml`. It is private and intentionally absent from GitHub. If it does not exist, follow README step 4 to copy `.env.example` once.

The line numbers below refer to the current `.env.example` and a freshly copied `.env`. Your private file's line numbers may differ: search for the variable name instead. In VS Code/PyCharm, open the file and use Find. Do not post the whole file or a screenshot containing your key.

| Setting | Template line | Purpose |
|---|---:|---|
| `OPENAI_API_KEY` | 10 | Your private API key; non-empty selects OpenAI with auto. |
| `QUESTION_PARSER_MODEL` | **11** | Shared model for **all OpenAI tasks**. |
| `AI_PROVIDER` | 12 | `auto` selects by key; `ollama` explicitly forces local AI. |
| `OLLAMA_BASE_URL` | 13 | Local Ollama service, normally http://localhost:11434. |
| `OLLAMA_TEXT_MODEL` | 14 | Local text question-paper parser model. |
| `OLLAMA_VISION_MODEL` | 15 | Local scanned-paper parser and student-answer transcription model. |
| `OLLAMA_MAPPING_MODEL` | 16 | Local semantic mapping model; blank uses text model. |
| `OLLAMA_EVALUATION_MODEL` | 17 | Local grading model; blank uses text model. |
| `OLLAMA_NUM_CTX` | 20 | Leave blank on the demonstrated 16 GB setup. |

**Do not edit Python source to switch your local model.** For a developer tracing the settings, current source locations are:

- [backend/app/core/config.py](../backend/app/core/config.py), line 21: OpenAI default; lines 24–27: Ollama defaults.
- [backend/app/ai/question_parser.py](../backend/app/ai/question_parser.py), line 307: OpenAI paper parser uses the shared setting.
- [backend/app/ai/structured_provider.py](../backend/app/ai/structured_provider.py), line 26: extraction/mapping/evaluation share that OpenAI setting too.

Source line numbers may shift in later revisions. Editing `.env.example` changes the template for future installations, not your existing `.env`. Editing the Python default will not override an explicit `.env`/shell value.

## Example: switch OpenAI from mini to GPT-4.1

1. Open root `.env`.
2. Keep your real API key on its existing private line. Ensure `AI_PROVIDER=auto`.
3. Replace the existing model line with exactly:

   ```dotenv
   QUESTION_PARSER_MODEL=gpt-4.1
   ```

4. Save the file. Do not add a second `QUESTION_PARSER_MODEL` line.
5. In the backend terminal, press **Ctrl+C**. From `backend`, with the existing venv activated, restart:

   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

6. Leave the frontend running. Test a small disposable exam first.

To trial GPT-5.4, repeat with `QUESTION_PARSER_MODEL=gpt-5.4`. To roll back, use `QUESTION_PARSER_MODEL=gpt-4.1-mini` and restart again. Neither switching nor rollback automatically changes saved transcriptions, grades or results.

One setting changes question-paper text/vision parsing, student-answer transcription, semantic mapping, and evaluation. There is currently **no way to select different OpenAI models per task using environment variables**. That would require a separate implementation change. Exact label mapping and mark totals remain deterministic code and do not use a model.

## Check effective settings without printing your API key

From `backend` with venv active, run:

```bash
python -c "from app.core.config import get_settings; s=get_settings(); p=('openai' if (s.openai_api_key or '').strip() else 'ollama') if s.ai_provider=='auto' else s.ai_provider; print('provider:', p); print('OpenAI model:', s.question_parser_model); print('Ollama text/vision:', s.ollama_text_model, s.ollama_vision_model)"
```

This only reports configuration; it does not make a paid call or prove the server was restarted. Run it in the same environment used to launch the backend. If output differs from `.env`, check for previously exported shell variables, which take precedence. Restart the server after correcting them.

## Local Ollama choices

Keep `gemma3:4b` as the demonstrated local baseline. Earlier `qwen3-vl:8b` requests stalled on the 16 GB Mac, and `llama3.2-vision` had a load error in that environment. Neither is a recommended beginner fallback on that machine. A bigger local model is not automatically a practical improvement.

If an experienced user trials a different installed model, use `ollama list` to get its exact tag. For image transcription it must support images and the structured JSON request used here. Pull the chosen model first, then change line 15 (`OLLAMA_VISION_MODEL`) in root `.env` and restart backend. Change lines 14/16/17 only for the other tasks you intend to test. A text-only model is unsuitable for line 15. Installed/working does not mean accurate; run the same comparison below. Use `AI_PROVIDER=ollama`, or `auto` with an empty OpenAI key, to actually select these settings.

## Test a new model without confusing cached results

1. Create a **new disposable exam** with the same questions/references and one known synthetic sheet. This preserves the existing reviewed submission.
2. For question papers, explicitly click **Parse / reparse** after restarting. Reparse changes candidates, not previously imported questions.
3. For student answers, upload/process the sheet in the new exam. Clicking Process on an already extracted submission can return stored answers. Refreshing the browser does not run a new model.
4. If you deliberately reuse an existing submission, **Reset extraction** removes its answers, corrections and dependent evaluations/results. Only do that when those records can be discarded, then Process again. Reset is not an automatic model switch step.
5. For grading comparisons, use reviewed transcriptions and explicit **Re-evaluate**. This can replace the current evaluation; use the disposable exam rather than a finalized one.

Compare every visible line to the source, especially:

- Aman Q2: preserve `3x = 4` and `x = 4/3`; never replace with the correct solution.
- Wrong probability, HCF, circumference, mean and incomplete factorization: preserve the actual written errors.
- Question count, Q10(a)/Q10(b) separation, intermediate steps, fractions, signs, superscripts and page continuations.
- Time taken, failed requests and API cost, alongside accuracy.

Repeat on actual handwriting with a human-checked transcript before claiming suitability. Zero invented/corrected steps in the demo acceptance set is a useful requirement, but it is not a guarantee on unseen sheets. Retain faculty review for every model.

If switching yields authentication/quota/model-access or schema errors, check the backend and API project before changing prompts. If a new model rejects this request format, return to the known configuration and ask a developer to review compatibility; do not disable Pydantic validation. Blurry inputs, low-resolution rendering and omitted regions may need better scans or focused crops rather than another model name.
