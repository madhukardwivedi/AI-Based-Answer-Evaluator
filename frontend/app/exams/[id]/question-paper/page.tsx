"use client";

import { ChangeEvent, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ExamShell } from "@/components/exam-shell";
import { api, ApiError, Exam, ParsedQuestion, ParsedRubricCriterion, QuestionPaper } from "@/lib/api-client";

const message = (error: unknown) => error instanceof ApiError ? error.message : "Something went wrong. Please try again.";
const referenceFields: { key: keyof Pick<ParsedQuestion, "model_answer" | "key_concepts" | "acceptable_alternatives" | "reference_solution" | "marking_notes">; label: string }[] = [
  { key: "model_answer", label: "Model answer" },
  { key: "key_concepts", label: "Key concepts" },
  { key: "acceptable_alternatives", label: "Acceptable alternatives" },
  { key: "reference_solution", label: "Reference solution" },
  { key: "marking_notes", label: "Marking notes" },
];

export default function QuestionPaperPage() {
  const params = useParams<{id:string}>();
  const router = useRouter();
  const [exam, setExam] = useState<Exam | null>(null);
  const [paper, setPaper] = useState<QuestionPaper | null>(null);
  const [questions, setQuestions] = useState<ParsedQuestion[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function load() {
    try {
      const [current, currentPaper] = await Promise.all([
        api<Exam>(`/api/exams/${params.id}`),
        api<QuestionPaper | null>(`/api/exams/${params.id}/question-paper`),
      ]);
      setExam(current);
      setPaper(currentPaper);
      const flat = currentPaper?.parse_result?.sections.flatMap((section) => section.questions) ?? [];
      setQuestions(flat);
      setSelected(new Set(flat.map((_, index) => index)));
    } catch {
      router.replace("/login");
    }
  }

  // Fetch only when the route identifier changes; mutations update local state directly.
  // eslint-disable-next-line react-hooks/exhaustive-deps, react-hooks/set-state-in-effect
  useEffect(() => { void load(); }, [params.id]);

  async function upload() {
    if (!file) {
      setError("Choose a PDF, JPG, JPEG, or PNG file first.");
      return;
    }
    setBusy(true); setError(""); setNotice("");
    try {
      const form = new FormData();
      form.append("file", file);
      const uploaded = await api<QuestionPaper>(`/api/exams/${params.id}/question-paper`, { method: "POST", body: form });
      setPaper(uploaded); setFile(null); setQuestions([]); setSelected(new Set());
      setNotice("Question paper uploaded. Parse it when you are ready.");
    } catch (error_) {
      setError(message(error_));
    } finally {
      setBusy(false);
    }
  }

  async function parse() {
    setBusy(true); setError(""); setNotice("");
    try {
      const parsed = await api<QuestionPaper>(`/api/exams/${params.id}/question-paper/parse`, { method: "POST" });
      setPaper(parsed);
      const flat = parsed.parse_result?.sections.flatMap((section) => section.questions) ?? [];
      setQuestions(flat);
      setSelected(new Set(flat.map((_, index) => index)));
      setNotice("Review and edit the candidate questions before importing.");
    } catch (error_) {
      setError(message(error_));
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!window.confirm("Delete this question paper and its saved parse result?")) return;
    setBusy(true);
    try {
      await api<void>(`/api/exams/${params.id}/question-paper`, { method: "DELETE" });
      setPaper(null); setQuestions([]); setSelected(new Set()); setNotice("Question paper deleted."); setError("");
    } catch (error_) {
      setError(message(error_));
    } finally {
      setBusy(false);
    }
  }

  function edit(index: number, key: keyof ParsedQuestion, value: string) {
    setQuestions((items) => items.map((question, itemIndex) => itemIndex === index ? {
      ...question,
      [key]: key === "maximum_marks" ? (value === "" ? null : value) : key === "sequence_order" ? Number(value) : value,
    } : question));
  }

  function editRubric(index: number, criterionIndex: number, key: keyof ParsedRubricCriterion, value: string) {
    setQuestions((items) => items.map((question, itemIndex) => {
      if (itemIndex !== index) return question;
      return {
        ...question,
        rubric_criteria: question.rubric_criteria.map((criterion, currentIndex) => currentIndex === criterionIndex ? {
          ...criterion,
          [key]: key === "maximum_marks" ? value : value || null,
        } : criterion),
      };
    }));
  }

  function addRubric(index: number) {
    setQuestions((items) => items.map((question, itemIndex) => itemIndex === index ? {
      ...question,
      rubric_criteria: [...question.rubric_criteria, { criterion: "", maximum_marks: "0", description: null }],
    } : question));
  }

  function removeRubric(index: number, criterionIndex: number) {
    setQuestions((items) => items.map((question, itemIndex) => itemIndex === index ? {
      ...question,
      rubric_criteria: question.rubric_criteria.filter((_, currentIndex) => currentIndex !== criterionIndex),
    } : question));
  }

  async function importSelected() {
    const chosen = questions.filter((_, index) => selected.has(index));
    if (!chosen.length) {
      setError("Select at least one question to import.");
      return;
    }
    setBusy(true); setError("");
    try {
      const result = await api<{ imported:string[]; skipped_conflicts:string[] }>(`/api/exams/${params.id}/question-paper/import`, {
        method: "POST",
        body: JSON.stringify({ questions: chosen }),
      });
      setNotice(`Imported ${result.imported.length} question(s).${result.skipped_conflicts.length ? ` Skipped: ${result.skipped_conflicts.join(", ")}` : ""}`);
      setSelected(new Set());
    } catch (error_) {
      setError(message(error_));
    } finally {
      setBusy(false);
    }
  }

  if (!exam) return <ExamShell examId={params.id} examName={null}><p>Loading...</p></ExamShell>;

  return (
    <ExamShell examId={params.id} examName={exam.name}>
      <section className="rounded-lg border bg-white p-6">
        <h2 className="font-semibold">Question paper</h2>
        {paper ? (
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <p className="text-sm">{paper.original_filename} · {paper.status}</p>
            <button disabled={busy} onClick={() => void parse()} className="bg-blue-700 text-white">{busy ? "Working..." : "Parse / reparse"}</button>
            <button disabled={busy} onClick={() => void remove()} className="border border-red-200 text-red-700">Delete</button>
          </div>
        ) : (
          <div className="mt-4 flex flex-wrap gap-3">
            <input type="file" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" onChange={(event: ChangeEvent<HTMLInputElement>) => setFile(event.target.files?.[0] ?? null)} />
            <button disabled={busy} onClick={() => void upload()} className="bg-blue-700 text-white">Upload question paper</button>
          </div>
        )}
      </section>

      {error && <p className="mt-4 rounded bg-red-50 p-3 text-red-700">{error}</p>}
      {notice && <p className="mt-4 rounded bg-green-50 p-3 text-green-700">{notice}</p>}

      {questions.length > 0 && (
        <section className="mt-6 rounded-lg border bg-white p-6">
          <h2 className="font-semibold">Review parsed questions</h2>
          <p className="mt-1 text-sm text-slate-600">Edits here are candidates only; nothing replaces manual questions.</p>
          <div className="mt-4 space-y-4">
            {questions.map((question, index) => (
              <article key={index} className="rounded border p-4">
                <label className="flex gap-2 text-sm">
                  <input type="checkbox" checked={selected.has(index)} onChange={() => setSelected((old) => { const next = new Set(old); if (next.has(index)) next.delete(index); else next.add(index); return next; })} />
                  Import this question
                </label>

                <div className="mt-3 grid gap-2 md:grid-cols-4">
                  <input value={question.question_number} onChange={(event) => edit(index, "question_number", event.target.value)} required />
                  <input type="number" min="0" step="0.01" value={question.maximum_marks ?? ""} placeholder="Marks required" onChange={(event) => edit(index, "maximum_marks", event.target.value)} />
                  <input type="number" min="0" value={question.sequence_order} onChange={(event) => edit(index, "sequence_order", event.target.value)} />
                  <input value={question.parent_question_number ?? ""} placeholder="Parent number" onChange={(event) => edit(index, "parent_question_number", event.target.value)} />
                  <textarea className="md:col-span-4" value={question.question_text} onChange={(event) => edit(index, "question_text", event.target.value)} />
                </div>

                <details className="mt-3 rounded border border-slate-200 bg-slate-50 p-3">
                  <summary className="cursor-pointer text-sm font-medium text-slate-700">Reference answers and rubric</summary>
                  <div className="mt-3 grid gap-3">
                    {referenceFields.map((field) => (
                      <label key={field.key} className="grid gap-1 text-sm">
                        <span className="text-slate-600">{field.label}</span>
                        <textarea value={question[field.key] ?? ""} onChange={(event) => edit(index, field.key, event.target.value)} />
                      </label>
                    ))}
                    <div>
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-slate-700">Rubric criteria</p>
                        <button type="button" onClick={() => addRubric(index)} className="border text-sm">Add criterion</button>
                      </div>
                      <div className="mt-2 space-y-2">
                        {question.rubric_criteria.map((criterion, criterionIndex) => (
                          <div key={criterionIndex} className="grid gap-2 rounded border bg-white p-3 md:grid-cols-[1fr_120px_auto]">
                            <input value={criterion.criterion} placeholder="Criterion" onChange={(event) => editRubric(index, criterionIndex, "criterion", event.target.value)} />
                            <input type="number" min="0" step="0.01" value={criterion.maximum_marks} onChange={(event) => editRubric(index, criterionIndex, "maximum_marks", event.target.value)} />
                            <button type="button" onClick={() => removeRubric(index, criterionIndex)} className="border border-red-200 text-red-700">Remove</button>
                            <textarea className="md:col-span-3" value={criterion.description ?? ""} placeholder="Description" onChange={(event) => editRubric(index, criterionIndex, "description", event.target.value)} />
                          </div>
                        ))}
                        {!question.rubric_criteria.length && <p className="text-sm text-slate-500">No rubric criteria parsed.</p>}
                      </div>
                    </div>
                  </div>
                </details>

                {question.warnings.length > 0 && <p className="mt-2 text-sm text-amber-700">{question.warnings.join(" ")}</p>}
              </article>
            ))}
          </div>
          <button disabled={busy} onClick={() => void importSelected()} className="mt-5 bg-blue-700 text-white">Import selected questions</button>
        </section>
      )}
    </ExamShell>
  );
}
