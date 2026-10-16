import base64
import json
import logging
import re
from decimal import Decimal
from typing import Any, Callable

import httpx
from openai import OpenAI, RateLimitError
from pydantic import ValidationError

from app.ai.prompts.question_parser_v1 import QUESTION_PARSER_PROMPT
from app.core.config import get_settings
from app.schemas.question_paper import QuestionPaperParseResult
from app.services.question_paper_document_service import DocumentExtraction

logger = logging.getLogger(__name__)
_LEADING_QUESTION_NUMBER = re.compile(
    r"^\s*(?P<number>Q?\s*\d+\s*(?:\(\s*(?:[A-Za-z]+|[ivxlcdmIVXLCDM]+)\s*\))?)(?:\s*[.:\-]\s*|\s+)",
)
_SUBQUESTION_NUMBER = re.compile(r"^(?P<parent>Q?\s*\d+)\s*\(")
_SOURCE_QUESTION_NUMBER = re.compile(r"(?m)^\s*(?P<number>Q?\s*\d+\s*(?:\(\s*(?:[A-Za-z]+|[ivxlcdmIVXLCDM]+)\s*\))?)\s*[.:)]")
_VISIBLE_MARKS = re.compile(r"(?:\[|\()\s*(?P<marks>\d+(?:\.\d+)?)\s*marks?\s*(?:\]|\))", re.IGNORECASE)
_MARK_VALUE = re.compile(r"^\s*(?:(?:marks?|m)\s*:\s*)?(?:\[|\()?\s*(?P<marks>\d+(?:\.\d+)?)\s*(?:marks?|m)?\s*(?:\]|\))?\s*$", re.IGNORECASE)
_QUESTION_IDENTIFIER = re.compile(r"^\s*(?:Q\s*)?(?P<number>\d+)(?P<sub>\s*\(\s*(?:[A-Za-z]+|[ivxlcdmIVXLCDM]+)\s*\))?\s*$", re.IGNORECASE)
_LEADING_MARK = re.compile(r"^\s*(?:(?:\[|\()\s*(?P<bracket>\d+(?:\.\d+)?)\s*(?:marks?|m)?\s*(?:\]|\))|(?:(?:marks?|m)\s*:\s*)?(?P<plain>\d+(?:\.\d+)?)\s*(?:marks?|m))\s*(?:[.:-]\s*)?", re.IGNORECASE)
_TRAILING_MARK = re.compile(r"(?:\s|[.:-])+(?:(?:\[|\()\s*(?P<bracket>\d+(?:\.\d+)?)\s*(?:marks?|m)?\s*(?:\]|\))|(?:(?:marks?|m)\s*:\s*)?(?P<plain>\d+(?:\.\d+)?)\s*(?:marks?|m))\s*[.]?\s*$", re.IGNORECASE)


class QuestionPaperParsingError(RuntimeError):
    pass


def _ollama_error_detail(response: httpx.Response) -> str | None:
    """Return only Ollama's short server error, never document or prompt data."""
    try:
        value = response.json().get("error")
    except (ValueError, AttributeError):
        return None
    return str(value)[:300] if isinstance(value, str) else None


def normalize_question_paper_result(result: QuestionPaperParseResult) -> QuestionPaperParseResult:
    """Correct predictable model formatting errors without inventing question content."""
    normalized_sections = []
    for section in result.sections:
        normalized_questions = []
        for question in section.questions:
            question_number = canonical_question_number(question.question_number)
            question_text = question.question_text.strip()
            visible = _LEADING_QUESTION_NUMBER.match(question_text)
            if visible:
                visible_number = canonical_question_number(visible.group("number"))
                # The visible source identifier is more authoritative than a truncated model field.
                question_number = visible_number
                question_text = question_text[visible.end():].strip()
            mark_match = _LEADING_MARK.match(question_text)
            maximum_marks = question.maximum_marks
            if mark_match:
                if maximum_marks is None:
                    maximum_marks = Decimal(mark_match.group("bracket") or mark_match.group("plain"))
                question_text = question_text[mark_match.end():].strip()
            trailing_mark = _TRAILING_MARK.search(question_text)
            if trailing_mark:
                if maximum_marks is None:
                    maximum_marks = Decimal(trailing_mark.group("bracket") or trailing_mark.group("plain"))
                question_text = question_text[:trailing_mark.start()].strip()
                separator = trailing_mark.group(0).lstrip()[:1]
                if separator in {".", ":"}:
                    question_text += separator
            parent = canonical_question_number(question.parent_question_number) if question.parent_question_number else None
            subquestion = _SUBQUESTION_NUMBER.match(question_number)
            if subquestion:
                parent = canonical_question_number(subquestion.group("parent"))
            elif parent == question_number:
                # A top-level item must never be its own parent.
                parent = None
            normalized_questions.append(question.model_copy(update={"question_number": question_number, "question_text": question_text, "maximum_marks": maximum_marks, "parent_question_number": parent}))
        normalized_sections.append(section.model_copy(update={"questions": normalized_questions}))
    return deduplicate_question_paper_result(result.model_copy(update={"sections": normalized_sections}))


def canonical_question_number(value: str) -> str:
    """Use Q-prefixed display numbers while retaining the visible subquestion style."""
    raw = value.strip().rstrip(".:")
    compact = re.sub(r"\s+", "", raw)
    match = _QUESTION_IDENTIFIER.match(compact)
    if not match:
        return raw
    return "Q" + match.group("number") + (match.group("sub") or "")


def deduplicate_question_paper_result(result: QuestionPaperParseResult) -> QuestionPaperParseResult:
    """Keep one highest-quality candidate per logical identifier, in source order."""
    selected: dict[str, tuple[int, int, Any]] = {}
    for section_index, section in enumerate(result.sections):
        for question_index, question in enumerate(section.questions):
            key = canonical_question_number(question.question_number).lower()
            current = selected.get(key)
            if current is None:
                selected[key] = (section_index, question_index, question)
                continue
            _, _, existing = current
            # Prefer non-empty/cleaner wording, then an explicitly detected mark.
            candidate_score = (len(question.question_text.strip()), question.maximum_marks is not None)
            existing_score = (len(existing.question_text.strip()), existing.maximum_marks is not None)
            winner, other = (question, existing) if candidate_score > existing_score else (existing, question)
            warnings = list(dict.fromkeys([*winner.warnings, *other.warnings]))
            if winner.maximum_marks is None and other.maximum_marks is not None:
                winner = winner.model_copy(update={"maximum_marks": other.maximum_marks})
            selected[key] = (section_index, question_index, winner.model_copy(update={"warnings": warnings}))
    sections = []
    next_sequence = 1
    for section_index, section in enumerate(result.sections):
        questions = []
        for key, (owner_section, _, question) in selected.items():
            if owner_section != section_index:
                continue
            questions.append(question.model_copy(update={"sequence_order": next_sequence}))
            next_sequence += 1
        if questions:
            sections.append(section.model_copy(update={"questions": questions}))
    return result.model_copy(update={"sections": sections})


def recover_visible_marks(result: QuestionPaperParseResult, source_text: str) -> QuestionPaperParseResult:
    """Fill only missing marks explicitly printed beside a source question in extractable PDF text."""
    matches = list(_SOURCE_QUESTION_NUMBER.finditer(source_text))
    marks_by_number: dict[str, str] = {}
    for index, match in enumerate(matches):
        segment = source_text[match.end():matches[index + 1].start() if index + 1 < len(matches) else len(source_text)]
        visible_marks = _VISIBLE_MARKS.search(segment)
        if visible_marks:
            marks_by_number[re.sub(r"\s+", "", match.group("number"))] = visible_marks.group("marks")
    sections = []
    for section in result.sections:
        questions = [question.model_copy(update={"maximum_marks": marks_by_number.get(question.question_number, question.maximum_marks)}) if question.maximum_marks is None else question for question in section.questions]
        sections.append(section.model_copy(update={"questions": questions}))
    return result.model_copy(update={"sections": sections})


def recover_vision_marks(result: QuestionPaperParseResult, visible_marks: dict[str, Decimal], exam_total: Decimal | None = None) -> QuestionPaperParseResult:
    """Apply only model-read marks for already parsed question IDs; flag the rest for review."""
    existing_total = sum((question.maximum_marks or Decimal("0") for section in result.sections for question in section.questions), Decimal("0"))
    if exam_total is not None and existing_total + sum(visible_marks.values(), Decimal("0")) > exam_total:
        visible_marks = {}
    sections = []
    for section in result.sections:
        questions = []
        for question in section.questions:
            marks = question.maximum_marks if question.maximum_marks is not None else visible_marks.get(question.question_number)
            warnings = list(question.warnings)
            if marks is None and "Maximum marks could not be determined from the visible document." not in warnings:
                warnings.append("Maximum marks could not be determined from the visible document.")
            questions.append(question.model_copy(update={"maximum_marks": marks, "warnings": warnings}))
        sections.append(section.model_copy(update={"questions": questions}))
    return result.model_copy(update={"sections": sections})


def coerce_visible_mark(value: object) -> Decimal | None:
    if isinstance(value, (int, float)) and value >= 0:
        return Decimal(str(value))
    match = _MARK_VALUE.match(value) if isinstance(value, str) else None
    return Decimal(match.group("marks")) if match else None


def strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    if isinstance(schema, dict):
        if isinstance(schema.get("properties"), dict):
            schema["required"] = list(schema["properties"])
            schema["additionalProperties"] = False
        for value in schema.values():
            strict_schema(value)
    elif isinstance(schema, list):
        for value in schema:
            strict_schema(value)
    return schema


def normalize_provider_output_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize only provider formatting tokens before the final strict Pydantic boundary."""
    normalized = json.loads(json.dumps(payload))
    sections = normalized.get("sections")
    if not isinstance(sections, list):
        return normalized
    for section in sections:
        if not isinstance(section, dict) or not isinstance(section.get("questions"), list):
            continue
        for question in section["questions"]:
            if not isinstance(question, dict) or "maximum_marks" not in question:
                continue
            value = question["maximum_marks"]
            if value is None:
                pass
            else:
                mark = coerce_visible_mark(value)
                # Leave non-structural strings unchanged so strict validation rejects them.
                if mark is not None:
                    question["maximum_marks"] = mark
            criteria = question.get("rubric_criteria")
            if isinstance(criteria, list):
                for criterion in criteria:
                    if not isinstance(criterion, dict) or "maximum_marks" not in criterion:
                        continue
                    criterion_mark = coerce_visible_mark(criterion.get("maximum_marks"))
                    if criterion_mark is not None:
                        criterion["maximum_marks"] = criterion_mark
    return normalized


def validate_parser_output(raw_output: str) -> QuestionPaperParseResult:
    """Adapt harmless local-model omissions while preserving required source-derived content."""
    try:
        payload = normalize_provider_output_payload(_json_object_from_model_output(raw_output, required_key="sections"))
    except json.JSONDecodeError as error:
        raise QuestionPaperParsingError("The parser returned invalid JSON") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("sections"), list):
        raise QuestionPaperParsingError("The parser returned an invalid structured result")
    sections = []
    for section in payload["sections"]:
        if not isinstance(section, dict) or not isinstance(section.get("questions"), list):
            raise QuestionPaperParsingError("The parser returned an invalid structured result")
        questions = []
        for index, question in enumerate(section["questions"]):
            if not isinstance(question, dict) or not isinstance(question.get("question_number"), str) or not isinstance(question.get("question_text"), str):
                raise QuestionPaperParsingError("The parser returned an invalid structured result")
            confidence = question.get("confidence", 0.5)
            if isinstance(confidence, (int, float)) and confidence > 1:
                confidence = confidence / 100
            if not isinstance(confidence, (int, float)):
                confidence = 0.5
            rubric_criteria = question.get("rubric_criteria")
            questions.append({
                "question_number": question["question_number"],
                "question_text": question["question_text"],
                "maximum_marks": question.get("maximum_marks"),
                "parent_question_number": question.get("parent_question_number"),
                "sequence_order": question.get("sequence_order", index),
                "confidence": min(max(float(confidence), 0.0), 1.0),
                "warnings": question.get("warnings") if isinstance(question.get("warnings"), list) else [],
                "model_answer": question.get("model_answer"),
                "key_concepts": question.get("key_concepts"),
                "acceptable_alternatives": question.get("acceptable_alternatives"),
                "reference_solution": question.get("reference_solution"),
                "marking_notes": question.get("marking_notes"),
                "rubric_criteria": rubric_criteria if isinstance(rubric_criteria, list) else [],
            })
        sections.append({"section_label": section.get("section_label"), "instructions": section.get("instructions"), "questions": questions})
    try:
        return normalize_question_paper_result(QuestionPaperParseResult.model_validate({"exam_title": payload.get("exam_title"), "subject": payload.get("subject"), "sections": sections}))
    except ValidationError as error:
        raise QuestionPaperParsingError("The parser returned an invalid structured result") from error


def parse_ollama_question_paper_content(raw_content: str, *, debug_output: bool = False) -> QuestionPaperParseResult:
    """Use Ollama's structured assistant content first; retain a bounded compatibility adapter for harmless omissions."""
    if not raw_content.strip():
        raise QuestionPaperParsingError("Ollama returned an empty assistant response.")
    try:
        payload = normalize_provider_output_payload(_json_object_from_model_output(raw_content, required_key="sections"))
        return normalize_question_paper_result(QuestionPaperParseResult.model_validate(payload))
    except (ValidationError, json.JSONDecodeError) as direct_error:
        if debug_output and isinstance(direct_error, ValidationError):
            logger.warning("QUESTION_PARSER_DEBUG_PYDANTIC_VALIDATION_ERRORS=%s", direct_error.errors(include_url=False))
        try:
            return validate_parser_output(raw_content)
        except (QuestionPaperParsingError, ValidationError) as error:
            if debug_output and isinstance(error, ValidationError):
                logger.warning("QUESTION_PARSER_DEBUG_PYDANTIC_VALIDATION_ERRORS=%s", error.errors(include_url=False))
            raise QuestionPaperParsingError("Ollama returned output that did not match the required parser schema.") from error


def _json_object_from_model_output(raw_output: str, *, required_key: str | None = None) -> dict[str, Any]:
    """Find a schema-shaped JSON object after optional model prose/thinking, then validate it strictly."""
    value = raw_output.strip()
    candidates: list[str] = []
    if value.startswith("```"):
        lines = value.splitlines()
        if len(lines) >= 3 and lines[-1].strip().startswith("```"):
            candidates.append("\n".join(lines[1:-1]).strip())
    candidates.append(value)
    decoder = json.JSONDecoder()
    for candidate in candidates:
        # Qwen thinking/prose can contain braces before the actual fenced JSON. Try every object start.
        for match in re.finditer(r"\{", candidate):
            try:
                decoded, _ = decoder.raw_decode(candidate[match.start():])
            except json.JSONDecodeError:
                continue
            if isinstance(decoded, dict) and (required_key is None or required_key in decoded):
                return decoded
    raise json.JSONDecodeError(
        f"JSON object with required key '{required_key}' not found" if required_key else "JSON object not found",
        value,
        0,
    )


class OpenAIQuestionPaperParser:
    provider = "openai"

    def __init__(self, client: OpenAI | None = None) -> None:
        settings = get_settings()
        if client is None and not (settings.openai_api_key or "").strip():
            raise QuestionPaperParsingError("OPENAI_API_KEY is not configured")
        self.client = client or OpenAI(api_key=settings.openai_api_key)
        self.model = self.text_model = self.vision_model = settings.question_parser_model

    def parse(self, document: DocumentExtraction) -> QuestionPaperParseResult:
        content: list[dict[str, str]] = [{"type": "input_text", "text": QUESTION_PARSER_PROMPT}]
        if document.use_text:
            content.append({"type": "input_text", "text": "Question paper text:\n" + document.text})
        else:
            content.append({"type": "input_text", "text": "Read these question-paper pages in order."})
            content.extend({"type": "input_image", "image_url": "data:image/png;base64," + base64.b64encode(image).decode(), "detail": "high"} for image in document.images)
        try:
            response = self.client.responses.create(model=self.model, input=[{"role": "user", "content": content}], text={"format": {"type": "json_schema", "name": "question_paper_parse", "schema": strict_schema(QuestionPaperParseResult.model_json_schema()), "strict": True}}, store=False)
            return validate_parser_output(response.output_text)
        except ValidationError as error:
            raise QuestionPaperParsingError("The parser returned an invalid structured result") from error
        except RateLimitError as error:
            raise QuestionPaperParsingError("OpenAI parsing is unavailable because the API account has no remaining credits") from error
        except Exception as error:
            raise QuestionPaperParsingError("Question-paper parsing failed") from error


class OllamaQuestionPaperParser:
    provider = "ollama"

    def __init__(self, post: Callable[..., httpx.Response] | None = None, exam_total: Decimal | None = None) -> None:
        settings = get_settings()
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.text_model, self.vision_model = settings.ollama_text_model, settings.ollama_vision_model
        self.num_ctx, self.timeout_seconds = settings.ollama_num_ctx, settings.ollama_timeout_seconds
        self.debug_output = settings.question_parser_debug_output
        self.model = self.text_model
        self._post = post or httpx.post
        self.exam_total = exam_total

    def parse(self, document: DocumentExtraction) -> QuestionPaperParseResult:
        endpoint, payload = self.build_request(document)
        try:
            self._log_request_metadata(endpoint, payload)
            response = self._post(self.base_url + endpoint, json=payload, timeout=self.timeout_seconds)
            self._raise_for_ollama_status(response)
            response.raise_for_status()
            result = self._chat_content(response)
            try:
                parsed = parse_ollama_question_paper_content(result, debug_output=self.debug_output)
            except QuestionPaperParsingError as error:
                if self.debug_output:
                    logger.warning("QUESTION_PARSER_DEBUG_FAILURE=%s\nQUESTION_PARSER_DEBUG_RAW_OLLAMA_OUTPUT_START\n%s\nQUESTION_PARSER_DEBUG_RAW_OLLAMA_OUTPUT_END", error, result[:50000])
                raise
            return self._recover_marks_from_images(document, parsed) if not document.use_text else parsed
        except QuestionPaperParsingError:
            raise
        except ValidationError as error:
            raise QuestionPaperParsingError("Ollama returned an invalid structured result") from error
        except httpx.ConnectError as error:
            raise QuestionPaperParsingError("Ollama is unavailable. Start it and verify http://localhost:11434.") from error
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                raise QuestionPaperParsingError(f"Ollama model '{model}' is unavailable. Run: ollama pull {model}") from error
            detail = _ollama_error_detail(error.response)
            raise QuestionPaperParsingError(f"Ollama parsing request failed (HTTP {error.response.status_code})" + (f": {detail}" if detail else "")) from error
        except httpx.TimeoutException as error:
            raise QuestionPaperParsingError("Ollama request timed out.") from error
        except (httpx.HTTPError, ValueError) as error:
            raise QuestionPaperParsingError("Ollama parsing request failed") from error

    def build_request(self, document: DocumentExtraction) -> tuple[str, dict[str, Any]]:
        """Build the exact native Ollama chat request used in production and diagnostics."""
        model = self.text_model if document.use_text else self.vision_model
        prompt = QUESTION_PARSER_PROMPT + "\n\n" + ("Question paper text:\n" + document.text if document.use_text else "Read the attached question-paper pages in order.")
        message: dict[str, Any] = {"role": "user", "content": prompt}
        if not document.use_text:
            message["images"] = [base64.b64encode(image).decode("ascii") for image in document.images]
        options: dict[str, Any] = {"temperature": 0}
        if self.num_ctx is not None:
            options["num_ctx"] = self.num_ctx
        return "/api/chat", {"model": model, "messages": [message], "stream": False, "format": QuestionPaperParseResult.model_json_schema(), "options": options}

    def _log_request_metadata(self, endpoint: str, payload: dict[str, Any]) -> None:
        if not self.debug_output:
            return
        schema = payload.get("format")
        messages = payload.get("messages") if isinstance(payload.get("messages"), list) else []
        images = [image for message in messages if isinstance(message, dict) for image in message.get("images", []) if isinstance(image, str)]
        prompt_characters = sum(len(message.get("content", "")) for message in messages if isinstance(message, dict) and isinstance(message.get("content"), str))
        logger.warning(
            "QUESTION_PARSER_DEBUG_OLLAMA_REQUEST endpoint=%s model=%s stream=%s format_included=%s schema_characters=%s messages=%s prompt_characters=%s options=%s images=%s image_base64_characters=%s timeout_seconds=%s",
            endpoint, payload.get("model"), payload.get("stream"), "format" in payload,
            len(json.dumps(schema)) if isinstance(schema, dict) else 0, len(messages), prompt_characters,
            payload.get("options"), len(images), [len(image) for image in images], self.timeout_seconds,
        )

    def _raise_for_ollama_status(self, response: httpx.Response) -> None:
        if 200 <= response.status_code < 300:
            return
        if response.status_code == 404:
            raise QuestionPaperParsingError(f"Ollama model '{self.text_model}' is unavailable. Run: ollama pull {self.text_model}")
        raw_body = str(getattr(response, "text", ""))[:4000]
        detail = _ollama_error_detail(response) or raw_body or f"HTTP {response.status_code}"
        if self.debug_output:
            logger.warning("QUESTION_PARSER_DEBUG_OLLAMA_HTTP_ERROR status=%s body=%s", response.status_code, raw_body)
        raise QuestionPaperParsingError(f"Ollama rejected the request: {detail}")

    def _recover_marks_from_images(self, document: DocumentExtraction, parsed: QuestionPaperParseResult) -> QuestionPaperParseResult:
        missing = [question.question_number for section in parsed.sections for question in section.questions if question.maximum_marks is None]
        if not missing:
            return parsed
        prompt = """Inspect every full question-paper page, including its right edge, lower labels, tables, and columns. Extract marks only when visibly printed next to one of these existing question IDs: """ + ", ".join(missing) + ". Return JSON only: {\"marks\":[{\"question_number\":string,\"maximum_marks\":number}]}. Accept [2 marks], [2], (2 marks), (2), 2 marks, Marks: 2, M: 2, and 2M. Do not invent any mark or question." 
        message: dict[str, Any] = {"role": "user", "content": prompt, "images": [base64.b64encode(image).decode("ascii") for image in document.images]}
        options: dict[str, Any] = {"temperature": 0}
        if self.num_ctx is not None:
            options["num_ctx"] = self.num_ctx
        payload: dict[str, Any] = {"model": self.vision_model, "messages": [message], "stream": False, "format": "json", "options": options}
        try:
            response = self._post(self.base_url + "/api/chat", json=payload, timeout=self.timeout_seconds)
            response.raise_for_status()
            items = self._chat_content(response)
            decoded = _json_object_from_model_output(items, required_key="marks")
            allowed = set(missing)
            marks: dict[str, Decimal] = {}
            for item in decoded.get("marks", []):
                if not isinstance(item, dict) or str(item.get("question_number")) not in allowed:
                    continue
                value = item.get("maximum_marks")
                parsed_value = coerce_visible_mark(value)
                if parsed_value is not None:
                    marks[str(item["question_number"])] = parsed_value
        except (httpx.HTTPError, ValueError, TypeError, json.JSONDecodeError):
            marks = {}
        return recover_vision_marks(parsed, marks, self.exam_total)

    def _chat_content(self, response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError as error:
            raise QuestionPaperParsingError("Ollama returned a non-JSON HTTP response") from error
        message = body.get("message") if isinstance(body, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if self.debug_output:
            logger.warning(
                "QUESTION_PARSER_DEBUG_OLLAMA_METADATA status=%s top_level_keys=%s message_keys=%s content_length=%s thinking_length=%s done=%s done_reason=%s eval_count=%s",
                response.status_code,
                sorted(body) if isinstance(body, dict) else [],
                sorted(message) if isinstance(message, dict) else [],
                len(content) if isinstance(content, str) else 0,
                len(message.get("thinking", "")) if isinstance(message, dict) and isinstance(message.get("thinking", ""), str) else 0,
                body.get("done") if isinstance(body, dict) else None,
                body.get("done_reason") if isinstance(body, dict) else None,
                body.get("eval_count") if isinstance(body, dict) else None,
            )
        if not isinstance(content, str) or not content.strip():
            raise QuestionPaperParsingError("Ollama returned an empty assistant response.")
        return content


class QuestionPaperParser:
    """Configuration-selected parser with a single Pydantic result contract."""

    def __init__(self, exam_total: Decimal | None = None) -> None:
        settings = get_settings()
        provider = settings.ai_provider
        if provider == "auto":
            provider = "openai" if (settings.openai_api_key or "").strip() else "ollama"
        if provider == "openai":
            self._parser = OpenAIQuestionPaperParser()
        elif provider == "ollama":
            self._parser = OllamaQuestionPaperParser(exam_total=exam_total)
        else:
            raise QuestionPaperParsingError("AI_PROVIDER must be auto, openai, or ollama")
        logger.info("Question-paper parser provider=%s text_model=%s vision_model=%s", self.provider, self.text_model, self.vision_model)

    @property
    def provider(self) -> str: return self._parser.provider
    @property
    def model(self) -> str: return self._parser.model
    @property
    def text_model(self) -> str: return self._parser.text_model
    @property
    def vision_model(self) -> str: return self._parser.vision_model
    def parse(self, document: DocumentExtraction) -> QuestionPaperParseResult: return self._parser.parse(document)
