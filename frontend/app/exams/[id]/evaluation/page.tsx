"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { ExamShell } from "@/components/exam-shell";
import { api, ApiError, Evaluation, Exam, Question, StudentAnswer, SubmissionEvaluationSummary } from "@/lib/api-client";

type Submission = { id: string; student_name: string; roll_number: string | null; evaluation_status: string; finalized_at: string | null };
const message = (error: unknown, fallback: string) => error instanceof ApiError ? error.message : fallback;

export default function EvaluationPage() {
  const { id } = useParams<{ id: string }>();
  const [exam, setExam] = useState<Exam | null>(null);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [submissionId, setSubmissionId] = useState("");
  const [answers, setAnswers] = useState<StudentAnswer[]>([]);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [rubricQuestionIds, setRubricQuestionIds] = useState<string[]>([]);
  const [evaluations, setEvaluations] = useState<Record<string, Evaluation>>({});
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState("");

  async function loadSubmission(selectedId: string) {
    if (!selectedId) { setAnswers([]); setEvaluations({}); return; }
    const items = await api<StudentAnswer[]>(`/api/student-submissions/${selectedId}/answers`);
    const current = await Promise.all(items.map((answer) => api<Evaluation>(`/api/student-answers/${answer.id}/evaluation`).catch(() => null)));
    setAnswers(items);
    setEvaluations(Object.fromEntries(current.filter((value): value is Evaluation => value !== null).map((value) => [value.student_answer_id, value])));
  }

  useEffect(() => { void (async () => {
    try {
      const [loadedExam, loadedSubmissions, loadedQuestions] = await Promise.all([
        api<Exam>(`/api/exams/${id}`), api<Submission[]>(`/api/exams/${id}/submissions`), api<Question[]>(`/api/exams/${id}/questions`),
      ]);
      setExam(loadedExam); setSubmissions(loadedSubmissions); setQuestions(loadedQuestions);
      const rubricRows = await Promise.all(loadedQuestions.map(async (question) => [question.id, await api<unknown[]>(`/api/questions/${question.id}/rubric-criteria`)] as const));
      setRubricQuestionIds(rubricRows.filter(([, criteria]) => criteria.length > 0).map(([questionId]) => questionId));
      if (loadedSubmissions[0]) { setSubmissionId(loadedSubmissions[0].id); await loadSubmission(loadedSubmissions[0].id); }
    } catch (requestError) { setError(message(requestError, "Unable to load evaluation.")); }
  })(); }, [id]);

  async function evaluateAnswer(answer: StudentAnswer) {
    const question = questions.find((item) => item.id === answer.question_id);
    setBusy(`Evaluating ${question?.question_number ?? "answer"}…`); setError(""); setNotice("");
    try {
      const value = await api<Evaluation>(`/api/student-answers/${answer.id}/evaluate`, { method: "POST" });
      setEvaluations((current) => ({ ...current, [answer.id]: value }));
    } catch (requestError) { setError(message(requestError, "Evaluation failed.")); }
    finally { setBusy(""); }
  }

  async function evaluateAll() {
    if (!submissionId) return;
    setBusy("Evaluating mapped answers sequentially…"); setError(""); setNotice("");
    try {
      const summary = await api<SubmissionEvaluationSummary>(`/api/student-submissions/${submissionId}/evaluate`, { method: "POST" });
      setEvaluations(Object.fromEntries(summary.evaluations.map((value) => [value.student_answer_id, value])));
      setNotice(`${summary.evaluated} of ${summary.total} mapped answers evaluated.${summary.failed ? ` ${summary.failed} failed: ${summary.failures.map((item) => `${item.question_number ?? "answer"}: ${item.detail}`).join("; ")}` : ""}`);
      await loadSubmission(submissionId);
    } catch (requestError) { setError(message(requestError, "Unable to evaluate mapped answers.")); }
    finally { setBusy(""); }
  }

  async function approve(evaluation: Evaluation) {
    setBusy("Saving faculty approval…"); setError("");
    try {
      const value = await api<Evaluation>(`/api/evaluations/${evaluation.id}/approve`, { method: "POST" });
      setEvaluations((current) => ({ ...current, [value.student_answer_id]: value })); setNotice("AI suggestion accepted for faculty review.");
    } catch (requestError) { setError(message(requestError, "Unable to approve evaluation.")); }
    finally { setBusy(""); }
  }

  async function save(evaluation: Evaluation) {
    const mark = (document.getElementById(`mark-${evaluation.id}`) as HTMLInputElement).value;
    const remarks = (document.getElementById(`remarks-${evaluation.id}`) as HTMLTextAreaElement).value;
    const criterionMarks = evaluation.criteria.map((criterion) => ({ criterion_id: criterion.id, faculty_awarded_marks: (document.getElementById(`criterion-${criterion.id}`) as HTMLInputElement).value }));
    setBusy("Saving faculty review…"); setError("");
    try {
      const value = await api<Evaluation>(`/api/evaluations/${evaluation.id}`, { method: "PATCH", body: JSON.stringify({ manual_marks: mark, faculty_remarks: remarks || null, criterion_marks: criterionMarks }) });
      setEvaluations((current) => ({ ...current, [value.student_answer_id]: value })); setNotice("Faculty marks and remarks saved.");
    } catch (requestError) { setError(message(requestError, "Unable to save faculty review.")); }
    finally { setBusy(""); }
  }

  async function resetAll() {
    if (!submissionId || !window.confirm("Reset all evaluations for this student? Extraction and mappings will be kept.")) return;
    setBusy("Resetting evaluations…");
    try { await api<void>(`/api/student-submissions/${submissionId}/reset-evaluations`, { method: "POST" }); setEvaluations({}); setNotice("Evaluations reset; extraction and mappings were preserved."); setError(""); }
    catch (requestError) { setError(message(requestError, "Unable to reset evaluations.")); }
    finally { setBusy(""); }
  }

  async function finalize() {
    if (!submissionId) return;
    setBusy("Finalizing student evaluation…"); setError("");
    try {
      await api(`/api/student-submissions/${submissionId}/finalize`, { method: "POST" });
      setSubmissions((items) => items.map((item) => item.id === submissionId ? { ...item, evaluation_status: "finalized", finalized_at: new Date().toISOString() } : item));
      setNotice("Student evaluation finalized. Results now show the final faculty-reviewed total.");
    } catch (requestError) { setError(message(requestError, "Unable to finalize evaluation.")); }
    finally { setBusy(""); }
  }

  async function confirmUnanswered(question: Question) {
    if (!submissionId || !window.confirm(`Confirm ${question.question_number} as unanswered and award 0/${question.maximum_marks}?`)) return;
    setBusy(`Confirming ${question.question_number} as unanswered…`); setError("");
    try {
      await api<Evaluation>(`/api/student-submissions/${submissionId}/questions/${question.id}/confirm-unanswered`, { method: "POST" });
      await loadSubmission(submissionId); setNotice(`${question.question_number} recorded as faculty-confirmed unanswered.`);
    } catch (requestError) { setError(message(requestError, "Unable to confirm unanswered question.")); }
    finally { setBusy(""); }
  }

  const mappedCount = answers.filter((answer) => answer.question_id).length;
  const unmappedCount = answers.length - mappedCount;
  const evaluatedCount = Object.keys(evaluations).length;
  const reviewedCount = Object.values(evaluations).filter((value) => ["approved", "manually_modified"].includes(value.status)).length;
  const canFinalize = answers.length > 0 && mappedCount === questions.length && evaluatedCount === questions.length && reviewedCount === questions.length;
  const currentSubmission = submissions.find((item) => item.id === submissionId);
  const missingQuestions = questions.filter((question) => !answers.some((answer) => answer.question_id === question.id));

  return <ExamShell examId={id} examName={exam?.name ?? null}>
    {error && <p className="mb-4 rounded bg-red-50 p-3 text-red-700">{error}</p>}
    {notice && <p className="mb-4 rounded bg-green-50 p-3 text-green-800">{notice}</p>}
    {busy && <p className="mb-4 rounded bg-blue-50 p-3 text-blue-800">{busy}</p>}
    {unmappedCount > 0 && <p className="mb-4 rounded bg-amber-50 p-3 text-amber-800">{unmappedCount} extracted answer(s) still need question mapping before evaluation.</p>}
    <div className="rounded border bg-white p-5"><div className="flex flex-wrap items-end justify-between gap-4"><label className="text-sm font-medium">Student submission<select value={submissionId} onChange={(event) => { setSubmissionId(event.target.value); setNotice(""); void loadSubmission(event.target.value); }}><option value="">Select student</option>{submissions.map((submission) => <option key={submission.id} value={submission.id}>{submission.student_name} · {submission.roll_number || "—"}</option>)}</select></label><div className="flex flex-wrap gap-2"><button disabled={!submissionId || busy !== ""} onClick={() => void evaluateAll()} className="bg-blue-700 text-white disabled:opacity-50">Evaluate all mapped answers</button><button disabled={!canFinalize || busy !== "" || currentSubmission?.evaluation_status === "finalized"} onClick={() => void finalize()} className="bg-slate-800 text-white disabled:opacity-50">Finalize evaluation</button><button disabled={!submissionId || evaluatedCount === 0 || busy !== ""} onClick={() => void resetAll()} className="border border-red-200 text-red-700 disabled:opacity-50">Reset all evaluations</button></div></div><p className="mt-4 text-sm text-slate-600">{answers.length} extracted · {mappedCount} mapped · {evaluatedCount} evaluated · {reviewedCount} faculty reviewed · Status: {currentSubmission?.evaluation_status?.replaceAll("_", " ") ?? "—"}</p></div>
    {submissionId && missingQuestions.length > 0 && <section className="mt-5 rounded border border-amber-200 bg-amber-50 p-4"><h2 className="font-semibold">Questions with no detected answer</h2><p className="mt-1 text-sm text-amber-800">Confirm zero marks only after checking the source answer sheet.</p><div className="mt-3 flex flex-wrap gap-2">{missingQuestions.map((question) => <button key={question.id} disabled={busy !== ""} onClick={() => void confirmUnanswered(question)} className="border border-amber-300 bg-white">Confirm {question.question_number}: 0/{question.maximum_marks}</button>)}</div></section>}
    <div className="mt-5 space-y-4">{answers.map((answer) => {
      const evaluation = evaluations[answer.id]; const question = questions.find((item) => item.id === answer.question_id); const effectiveText = answer.edited_text ?? answer.raw_text ?? answer.answer_text; const hasReference = Boolean(question && (question.model_answer || question.key_concepts || question.reference_solution || question.marking_notes || rubricQuestionIds.includes(question.id))); const canEvaluate = Boolean(question && effectiveText.trim());
      return <article key={answer.id} className="rounded border bg-white p-5"><div className="grid gap-6 lg:grid-cols-2"><div><h2 className="font-semibold">{question ? `${question.question_number} — ${question.maximum_marks} marks` : "Unmapped answer — review required"}</h2>{question && <p className="mt-2 text-sm text-slate-600">{question.question_text}</p>}<h3 className="mt-4 font-medium">Student answer</h3><p className="mt-2 whitespace-pre-wrap">{effectiveText || "No answer — confirmed by faculty."}</p><p className="mt-3 text-sm text-slate-600">Extraction confidence: {answer.extraction_confidence ?? "—"} · {answer.extraction_status.replaceAll("_", " ")}</p></div><div><h2 className="font-semibold">Reference and evaluation</h2>{question && <div className="mt-2 space-y-2 text-sm text-slate-600">{question.model_answer && <p><b>Model answer:</b> {question.model_answer}</p>}{question.key_concepts && <p><b>Key concepts:</b> {question.key_concepts}</p>}{question.acceptable_alternatives && <p><b>Alternatives:</b> {question.acceptable_alternatives}</p>}{question.reference_solution && <p className="whitespace-pre-wrap"><b>Reference solution:</b> {question.reference_solution}</p>}{question.marking_notes && <p><b>Marking notes:</b> {question.marking_notes}</p>}</div>}{!canEvaluate && !evaluation ? <Link href={`/exams/${id}/extraction`} className="mt-3 inline-block border">Go to Extraction to map</Link> : !evaluation ? <div className="mt-3">{!hasReference && <p className="mb-2 text-sm text-amber-700">A rubric or reference data is required.</p>}<button disabled={busy !== ""} onClick={() => void evaluateAnswer(answer)} className="bg-blue-700 text-white disabled:opacity-50">Evaluate</button></div> : <><p className="mt-3">AI suggested: <b>{evaluation.ai_marks} / {evaluation.maximum_marks}</b> · Confidence {Math.round(Number(evaluation.confidence) * 100)}%</p><p className="mt-1 text-sm text-slate-600">Method: {evaluation.evaluation_method === "rubric" ? "Rubric-based" : evaluation.evaluation_method === "deterministic_unanswered" ? "Faculty-confirmed unanswered" : "Overall reference"} · Status: {evaluation.status.replaceAll("_", " ")}</p>{evaluation.criteria.length > 0 && <div className="mt-3 space-y-2">{evaluation.criteria.map((criterion) => <label key={criterion.id} className="block rounded border p-3 text-sm"><span className="font-medium">{criterion.criterion_text_snapshot}</span><span className="ml-2">AI {criterion.awarded_marks}/{criterion.maximum_marks} · {criterion.status}</span><input id={`criterion-${criterion.id}`} className="mt-2" defaultValue={criterion.faculty_awarded_marks ?? criterion.awarded_marks} type="number" min="0" max={criterion.maximum_marks} step="0.01" /><span className="ml-2 text-slate-600">{criterion.reason || criterion.evidence}</span></label>)}</div>}{evaluation.feedback && <p className="mt-3 text-sm"><b>Justification:</b> {evaluation.feedback}</p>}{evaluation.warnings.length > 0 && <p className="mt-3 text-sm text-amber-700">{evaluation.warnings.join(" ")}</p>}<label className="mt-3 block text-sm">Faculty marks<input id={`mark-${evaluation.id}`} defaultValue={evaluation.manual_marks ?? evaluation.final_marks} type="number" min="0" max={evaluation.maximum_marks} step="0.01" /></label><label className="mt-3 block text-sm">Faculty remarks<textarea id={`remarks-${evaluation.id}`} defaultValue={evaluation.faculty_remarks ?? ""} placeholder="Optional faculty remarks" /></label><div className="mt-3 flex flex-wrap gap-2"><button disabled={busy !== ""} onClick={() => void save(evaluation)} className="border">Modify & Save</button><button disabled={busy !== ""} onClick={() => void approve(evaluation)} className="bg-slate-800 text-white">Accept AI marks</button>{evaluation.evaluation_method !== "deterministic_unanswered" && <button disabled={busy !== ""} onClick={() => void evaluateAnswer(answer)} className="border">Re-evaluate</button>}</div><p className="mt-3 text-sm">AI: {evaluation.ai_marks} · Faculty: {evaluation.manual_marks ?? "—"} · Final: <b>{evaluation.final_marks}</b></p></>}</div></div></article>;
    })}</div>
  </ExamShell>;
}
