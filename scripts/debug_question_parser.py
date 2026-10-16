"""Local-only Ollama parser payload diagnostic. Does not use FastAPI or PostgreSQL."""
from __future__ import annotations

import json
import argparse
from pathlib import Path

import httpx

from app.ai.prompts.question_parser_v1 import QUESTION_PARSER_PROMPT
from app.ai.question_parser import OllamaQuestionPaperParser, QuestionPaperParsingError, parse_ollama_question_paper_content
from app.schemas.question_paper import QuestionPaperParseResult
from app.services.question_paper_document_service import DocumentExtraction, QuestionPaperDocumentService

PDF = Path(__file__).resolve().parents[1] / "class10_math_exam_50_marks.pdf"
TINY_TEXT = """Q1. Find HCF of 36 and 48. [2 marks]
Q2. Solve 3x - 7 = 11. [2 marks]
Q3(a). Define a prime number. [2 marks]
Q3(b). Give one example. [1 mark]"""


def metadata(response: httpx.Response) -> dict[str, object]:
    try:
        body = response.json()
    except ValueError:
        return {"http_status": response.status_code, "raw_error_body": response.text[:4000]}
    message = body.get("message") if isinstance(body, dict) else None
    return {
        "http_status": response.status_code,
        "top_level_keys": sorted(body) if isinstance(body, dict) else [],
        "message_keys": sorted(message) if isinstance(message, dict) else [],
        "content_length": len(message.get("content", "")) if isinstance(message, dict) and isinstance(message.get("content"), str) else 0,
        "thinking_length": len(message.get("thinking", "")) if isinstance(message, dict) and isinstance(message.get("thinking", ""), str) else 0,
        "done": body.get("done") if isinstance(body, dict) else None,
        "done_reason": body.get("done_reason") if isinstance(body, dict) else None,
        "eval_count": body.get("eval_count") if isinstance(body, dict) else None,
        "prompt_eval_count": body.get("prompt_eval_count") if isinstance(body, dict) else None,
    }


def run_case(name: str, parser: OllamaQuestionPaperParser, prompt: str, include_schema: bool) -> None:
    options: dict[str, object] = {"temperature": 0}
    if parser.num_ctx is not None:
        options["num_ctx"] = parser.num_ctx
    payload: dict[str, object] = {
        "model": parser.text_model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": options,
    }
    if include_schema:
        payload["format"] = QuestionPaperParseResult.model_json_schema()
    print(f"\n=== {name} ===")
    print(json.dumps({"model": payload["model"], "format": include_schema, "prompt_characters": len(prompt), "schema_characters": len(json.dumps(payload.get("format", {}))), "options": payload["options"]}))
    try:
        response = httpx.post(parser.base_url + "/api/chat", json=payload, timeout=parser.timeout_seconds)
    except httpx.TimeoutException:
        print("result=TIMEOUT timeout_seconds=" + str(parser.timeout_seconds))
        return
    except httpx.HTTPError as error:
        print("result=HTTP_CLIENT_ERROR error=" + str(error))
        return
    print(json.dumps(metadata(response)))
    if not response.is_success:
        print("raw_error_body=" + response.text[:4000])
        return
    body = response.json(); content = body.get("message", {}).get("content", "")
    if not content:
        print("validation=EMPTY_CONTENT")
        return
    try:
        parsed = parse_ollama_question_paper_content(content)
        questions = [question for section in parsed.sections for question in section.questions]
        print("validation=OK candidates=" + str(len(questions)) + " numbers=" + ",".join(question.question_number for question in questions))
    except QuestionPaperParsingError as error:
        print("validation=FAILED error=" + str(error))


def main() -> None:
    arguments = argparse.ArgumentParser()
    arguments.add_argument("--case", choices=["A", "B", "C", "D", "E"], help="Run one progressive case only")
    selected = arguments.parse_args().case
    parser = OllamaQuestionPaperParser()
    document = QuestionPaperDocumentService().extract(PDF, "application/pdf")
    print("schema_inspection=" + json.dumps({"characters": len(json.dumps(QuestionPaperParseResult.model_json_schema())), "has_defs": "$defs" in QuestionPaperParseResult.model_json_schema(), "has_refs": "$ref" in json.dumps(QuestionPaperParseResult.model_json_schema()), "has_any_of": "anyOf" in json.dumps(QuestionPaperParseResult.model_json_schema())}))
    cases = [
        ("A", "A tiny prompt, no schema", "Return exactly JSON: {\"status\":\"ok\"}", False),
        ("B", "B tiny prompt plus schema", QUESTION_PARSER_PROMPT + "\nQuestion paper text:\n" + TINY_TEXT, True),
        ("C", "C Maths text, no schema", document.text, False),
        ("D", "D Maths text plus schema", document.text, True),
    ]
    for code, name, prompt, include_schema in cases:
        if selected in (None, code):
            run_case(name, parser, prompt, include_schema)
    endpoint, real_payload = parser.build_request(document)
    if selected in (None, "E"):
        run_case("E full real parser prompt plus schema", parser, real_payload["messages"][0]["content"], True)


if __name__ == "__main__":
    main()
