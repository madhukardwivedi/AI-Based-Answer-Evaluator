export type ExamStatus = "draft" | "configured" | "processing" | "completed";
export interface User { id: string; name: string; email: string; role: "evaluator" }
export interface Exam { id: string; created_by_id: string; name: string; subject: string; class_name: string; description: string | null; total_marks: string; status: ExamStatus; created_at: string; updated_at: string; }
export interface Question { id: string; exam_id: string; parent_question_id: string | null; question_number: string; question_text: string; model_answer: string | null; key_concepts: string | null; acceptable_alternatives: string | null; reference_solution: string | null; marking_notes: string | null; maximum_marks: string; sequence_order: number; created_at: string; updated_at: string; }
export interface RubricCriterion { id: string; question_id: string; criterion: string; description: string | null; maximum_marks: string; sequence_order: number; }
export interface Student { id: string; exam_id: string; name: string; roll_number: string | null; external_id: string | null; created_at: string; updated_at: string; }
export interface StudentImportIssue { row: number; field: string; message: string; }
export interface StudentImportResult { total_rows: number; imported_count: number; skipped_count: number; errors: StudentImportIssue[]; }
export interface AnswerSheet { id: string; exam_id: string; student_id: string | null; original_filename: string; stored_filename: string; mime_type: string; file_size: number; status: "uploaded" | "processing" | "extracted" | "evaluated" | "review_required" | "completed" | "failed"; uploaded_at: string; processing_started_at: string | null; processing_completed_at: string | null; processing_error: string | null; student_name: string | null; student_roll_number: string | null; }
export interface ParsedRubricCriterion { criterion: string; maximum_marks: string; description: string | null; }
export interface ParsedQuestion { question_number: string; question_text: string; maximum_marks: string | null; parent_question_number: string | null; sequence_order: number; confidence: number; warnings: string[]; model_answer: string | null; key_concepts: string | null; acceptable_alternatives: string | null; reference_solution: string | null; marking_notes: string | null; rubric_criteria: ParsedRubricCriterion[]; }
export interface ParsedSection { section_label: string | null; instructions: string | null; questions: ParsedQuestion[]; }
export interface QuestionPaper { id: string; exam_id: string; original_filename: string; stored_filename: string; mime_type: string; file_size: number; status: "uploaded" | "parsing" | "parsed" | "review_required" | "failed"; uploaded_at: string; parsed_at: string | null; parsing_error: string | null; parser_model: string | null; prompt_version: string | null; parse_result: { exam_title: string | null; subject: string | null; sections: ParsedSection[] } | null; }
export interface StudentAnswer { id: string; student_submission_id: string; question_id: string | null; detected_question_number: string | null; answer_text: string; raw_text: string | null; edited_text: string | null; extraction_status: string; warnings: string[]; page_numbers: number[]; extraction_confidence: string | null; mapping_confidence: string | null; mapping_status: string; manually_corrected: boolean; reviewed: boolean; }
export interface EvaluationCriterion { id: string; rubric_criterion_id: string | null; criterion_text_snapshot: string; maximum_marks: string; awarded_marks: string; faculty_awarded_marks: string | null; final_awarded_marks: string; evidence: string; status: string; reason: string; }
export interface Evaluation { id: string; student_answer_id: string; ai_marks: string; manual_marks: string | null; final_marks: string; maximum_marks: string; confidence: string; strengths: string[]; missing_points: string[]; feedback: string; reasoning: string; faculty_remarks: string | null; status: string; ai_provider: string | null; ai_model: string | null; prompt_version: string | null; evaluation_method: string; warnings: string[]; criteria: EvaluationCriterion[]; }
export interface SubmissionEvaluationSummary { total: number; evaluated: number; failed: number; evaluations: Evaluation[]; failures: { student_answer_id: string; question_number: string | null; detail: string }[]; }
export interface StudentResult { submission_id: string; student_id: string; student_name: string; roll_number: string | null; total_marks: string; maximum_marks: string; percentage: string; status: string; questions: { question_number: string; question_id: string | null; ai_marks: string | null; faculty_marks: string | null; final_marks: string | null; maximum_marks: string; status: string }[]; }
const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export class ApiError extends Error { constructor(message: string, public readonly status: number) { super(message); } }

function errorDetail(body: unknown): string {
  if (typeof body !== "object" || body === null || !("detail" in body)) return "Request failed";
  const detail = body.detail;
  if (Array.isArray(detail)) return detail.map((item) => typeof item === "object" && item !== null && "msg" in item ? String(item.msg) : String(item)).join(", ");
  return String(detail);
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(apiUrl + path, { ...options, credentials: "include", headers });
  const bodyText = await response.text();
  const body: unknown = bodyText ? (() => { try { return JSON.parse(bodyText) as unknown; } catch { return bodyText; } })() : undefined;
  if (!response.ok) throw new ApiError(errorDetail(body), response.status);
  if (body === undefined) return undefined as T;
  return body as T;
}
