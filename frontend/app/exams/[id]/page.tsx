"use client";

import { FormEvent, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { ExamShell } from "@/components/exam-shell";
import { api, ApiError, Exam, Question, RubricCriterion } from "@/lib/api-client";

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

function validNumber(value: FormDataEntryValue | null): boolean {
  const number = Number(value);
  return value !== null && value !== "" && Number.isFinite(number) && number >= 0;
}

function optionalText(form: FormData, name: string): string | null {
  const value = String(form.get(name) ?? "").trim();
  return value || null;
}

export default function ExamDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [exam, setExam] = useState<Exam | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [criteria, setCriteria] = useState<Record<string, RubricCriterion[]>>({});
  const [error, setError] = useState("");
  const [addingFor, setAddingFor] = useState<string | null>(null);
  const [editingQuestionId, setEditingQuestionId] = useState<string | null>(null);
  const [editingCriterionId, setEditingCriterionId] = useState<string | null>(null);
  const [selectedQuestionIds, setSelectedQuestionIds] = useState<string[]>([]);

  async function load() {
    try {
      const [currentExam, items] = await Promise.all([
        api<Exam>("/api/exams/" + params.id),
        api<Question[]>("/api/exams/" + params.id + "/questions"),
      ]);
      const criterionEntries = await Promise.all(
        items.map(async (item) =>
          [item.id, await api<RubricCriterion[]>("/api/questions/" + item.id + "/rubric-criteria")] as const,
        ),
      );
      setExam(currentExam);
      setQuestions(items);
      setCriteria(Object.fromEntries(criterionEntries));
    } catch {
      router.replace("/login");
    }
  }

  // Data is fetched on initial route load. Subsequent mutations update local state immediately.
  // eslint-disable-next-line react-hooks/exhaustive-deps, react-hooks/set-state-in-effect
  useEffect(() => { void load(); }, [params.id]);

  async function addQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    if (!validNumber(form.get("maximum_marks")) || !validNumber(form.get("sequence_order"))) {
      setError("Maximum marks and sequence order must be zero or greater.");
      return;
    }
    setError("");
    try {
      const created = await api<Question>("/api/exams/" + params.id + "/questions", {
        method: "POST",
        body: JSON.stringify({
          question_number: form.get("question_number"),
          question_text: form.get("question_text"),
          model_answer: form.get("model_answer") || null,
          key_concepts: optionalText(form, "key_concepts"),
          acceptable_alternatives: optionalText(form, "acceptable_alternatives"),
          reference_solution: optionalText(form, "reference_solution"),
          marking_notes: optionalText(form, "marking_notes"),
          maximum_marks: form.get("maximum_marks"),
          sequence_order: Number(form.get("sequence_order")),
        }),
      });
      setQuestions((current) => [...current, created].sort((a, b) => a.sequence_order - b.sequence_order));
      setCriteria((current) => ({ ...current, [created.id]: [] }));
      formElement.reset();
    } catch (requestError) {
      setError(errorMessage(requestError, "Unable to add question."));
    }
  }

  async function updateQuestion(event: FormEvent<HTMLFormElement>, question: Question) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    if (!validNumber(form.get("maximum_marks")) || !validNumber(form.get("sequence_order"))) {
      setError("Maximum marks and sequence order must be zero or greater.");
      return;
    }
    setError("");
    try {
      const updated = await api<Question>("/api/questions/" + question.id, {
        method: "PUT",
        body: JSON.stringify({
          question_number: form.get("question_number"),
          question_text: form.get("question_text"),
          model_answer: form.get("model_answer") || null,
          key_concepts: optionalText(form, "key_concepts"),
          acceptable_alternatives: optionalText(form, "acceptable_alternatives"),
          reference_solution: optionalText(form, "reference_solution"),
          marking_notes: optionalText(form, "marking_notes"),
          maximum_marks: form.get("maximum_marks"),
          sequence_order: Number(form.get("sequence_order")),
          parent_question_id: question.parent_question_id,
        }),
      });
      setQuestions((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)).sort((a, b) => a.sequence_order - b.sequence_order),
      );
      setEditingQuestionId(null);
    } catch (requestError) {
      setError(errorMessage(requestError, "Unable to update question."));
    }
  }

  async function addCriterion(event: FormEvent<HTMLFormElement>, questionId: string) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setError("");
    if (!validNumber(form.get("maximum_marks")) || !validNumber(form.get("sequence_order"))) {
      setError("Criterion marks and sequence order must be zero or greater.");
      return;
    }
    try {
      const created = await api<RubricCriterion>("/api/questions/" + questionId + "/rubric-criteria", {
        method: "POST",
        body: JSON.stringify({
          criterion: form.get("criterion"),
          description: form.get("description") || null,
          maximum_marks: form.get("maximum_marks"),
          sequence_order: Number(form.get("sequence_order")),
        }),
      });
      setCriteria((current) => ({
        ...current,
        [questionId]: [...(current[questionId] ?? []), created].sort((a, b) => a.sequence_order - b.sequence_order),
      }));
      setAddingFor(null);
    } catch (requestError) {
      setError(errorMessage(requestError, "Unable to add criterion."));
    }
  }

  async function updateCriterion(
    event: FormEvent<HTMLFormElement>,
    questionId: string,
    criterion: RubricCriterion,
  ) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setError("");
    if (!validNumber(form.get("maximum_marks")) || !validNumber(form.get("sequence_order"))) {
      setError("Criterion marks and sequence order must be zero or greater.");
      return;
    }
    try {
      const updated = await api<RubricCriterion>("/api/rubric-criteria/" + criterion.id, {
        method: "PUT",
        body: JSON.stringify({
          criterion: form.get("criterion"),
          description: form.get("description") || null,
          maximum_marks: form.get("maximum_marks"),
          sequence_order: Number(form.get("sequence_order")),
        }),
      });
      setCriteria((current) => ({
        ...current,
        [questionId]: (current[questionId] ?? [])
          .map((item) => (item.id === updated.id ? updated : item))
          .sort((a, b) => a.sequence_order - b.sequence_order),
      }));
      setEditingCriterionId(null);
    } catch (requestError) {
      setError(errorMessage(requestError, "Unable to update criterion."));
    }
  }

  async function removeQuestion(questionId: string) {
    if (!window.confirm("Delete this question and all of its rubric criteria? This cannot be undone.")) return;
    try {
      await api<void>("/api/questions/" + questionId, { method: "DELETE" });
      setQuestions((current) => current.filter((question) => question.id !== questionId));
      setCriteria((current) => {
        const next = { ...current };
        delete next[questionId];
        return next;
      });
      setError("");
    } catch (requestError) {
      setError(errorMessage(requestError, "Unable to delete question."));
    }
  }

  async function removeSelectedQuestions() {
    if (!selectedQuestionIds.length) return;
    if (!window.confirm(`Delete ${selectedQuestionIds.length} selected questions? Associated rubric criteria will also be deleted.`)) return;
    try {
      await api<{ deleted_count: number }>("/api/exams/" + params.id + "/questions/bulk", { method: "DELETE", body: JSON.stringify({ question_ids: selectedQuestionIds }) });
      const removed = new Set(selectedQuestionIds);
      setQuestions((items) => items.filter((item) => !removed.has(item.id)));
      setCriteria((items) => Object.fromEntries(Object.entries(items).filter(([id]) => !removed.has(id))));
      setSelectedQuestionIds([]); setError("");
    } catch (requestError) { setError(errorMessage(requestError, "Unable to delete selected questions.")); }
  }

  async function removeCriterion(questionId: string, criterionId: string) {
    try {
      await api<void>("/api/rubric-criteria/" + criterionId, { method: "DELETE" });
      setCriteria((current) => ({
        ...current,
        [questionId]: (current[questionId] ?? []).filter((criterion) => criterion.id !== criterionId),
      }));
      setError("");
    } catch (requestError) {
      setError(errorMessage(requestError, "Unable to delete criterion."));
    }
  }

  if (!exam) return <ExamShell examId={params.id} examName={null}><p>Loading exam…</p></ExamShell>;

  return (
    <ExamShell examId={exam.id} examName={exam.name}>
      <div className="mb-8 rounded-lg border bg-white p-5">
        <div className="flex flex-wrap justify-between gap-4">
          <div><p className="font-medium">{exam.subject} · {exam.class_name}</p><p className="mt-1 text-sm text-slate-600">{exam.description || "No description provided."}</p></div>
          <p className="text-lg font-semibold">{exam.total_marks} marks</p>
        </div>
      </div>

      <section className="rounded-lg border bg-white p-6">
        <h2 className="font-semibold">Add question</h2>
        <form onSubmit={addQuestion} className="mt-4 grid gap-3 md:grid-cols-2">
          <input name="question_number" placeholder="Question number, e.g. 1(a)" required />
          <input name="maximum_marks" type="number" min="0" step="0.01" placeholder="Maximum marks" required />
          <input name="sequence_order" type="number" min="0" placeholder="Sequence order" required />
          <textarea name="model_answer" placeholder="Model answer (optional)" />
          <textarea className="md:col-span-2" name="question_text" placeholder="Question text" required />
          <textarea name="key_concepts" placeholder="Key concepts (optional)" />
          <textarea name="acceptable_alternatives" placeholder="Acceptable alternatives (optional)" />
          <textarea name="reference_solution" placeholder="Reference solution (optional)" />
          <textarea name="marking_notes" placeholder="Marking notes (optional)" />
          <button className="w-fit bg-blue-700 text-white hover:bg-blue-800">Add question</button>
        </form>
      </section>

      {error && <p className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <section className="mt-8">
        <div className="mb-4 flex flex-wrap items-center gap-2"><h2 className="mr-3 text-lg font-semibold">Questions</h2><button onClick={() => setSelectedQuestionIds(questions.map((q) => q.id))} className="border">Select All</button><button onClick={() => setSelectedQuestionIds([])} className="border">Clear Selection</button><button disabled={!selectedQuestionIds.length} onClick={() => void removeSelectedQuestions()} className="border border-red-200 text-red-700 disabled:opacity-50">Delete Selected</button><span className="text-sm text-slate-600">{selectedQuestionIds.length} questions selected</span></div>
        {questions.length === 0 ? <p className="rounded-lg border border-dashed bg-white p-6 text-slate-600">No questions have been configured.</p> : (
          <div className="space-y-4">
            {questions.map((question) => (
              <article key={question.id} className="rounded-lg border bg-white p-5">
                <label className="mb-3 flex w-fit items-center gap-2 text-sm text-slate-600"><input type="checkbox" checked={selectedQuestionIds.includes(question.id)} onChange={() => setSelectedQuestionIds((ids) => ids.includes(question.id) ? ids.filter((id) => id !== question.id) : [...ids, question.id])} /> Select question</label>
                {editingQuestionId === question.id ? (
                  <form onSubmit={(event) => updateQuestion(event, question)} className="grid gap-3 md:grid-cols-2">
                    <input name="question_number" defaultValue={question.question_number} required />
                    <input name="maximum_marks" type="number" min="0" step="0.01" defaultValue={question.maximum_marks} required />
                    <input name="sequence_order" type="number" min="0" defaultValue={question.sequence_order} required />
                    <textarea name="model_answer" defaultValue={question.model_answer ?? ""} placeholder="Model answer (optional)" />
                    <textarea className="md:col-span-2" name="question_text" defaultValue={question.question_text} required />
                    <textarea name="key_concepts" defaultValue={question.key_concepts ?? ""} placeholder="Key concepts (optional)" />
                    <textarea name="acceptable_alternatives" defaultValue={question.acceptable_alternatives ?? ""} placeholder="Acceptable alternatives (optional)" />
                    <textarea name="reference_solution" defaultValue={question.reference_solution ?? ""} placeholder="Reference solution (optional)" />
                    <textarea name="marking_notes" defaultValue={question.marking_notes ?? ""} placeholder="Marking notes (optional)" />
                    <div className="flex gap-2"><button className="bg-blue-700 text-white hover:bg-blue-800">Save</button><button type="button" onClick={() => setEditingQuestionId(null)} className="border">Cancel</button></div>
                  </form>
                ) : (
                  <div className="flex justify-between gap-4">
                    <div><h3 className="font-semibold">{question.question_number} · {question.maximum_marks} marks</h3><p className="mt-2">{question.question_text}</p>{question.model_answer && <p className="mt-2 whitespace-pre-wrap text-sm text-slate-600"><span className="font-medium">Model answer:</span> {question.model_answer}</p>}{question.key_concepts && <p className="mt-2 text-sm text-slate-600"><span className="font-medium">Key concepts:</span> {question.key_concepts}</p>}{question.acceptable_alternatives && <p className="mt-2 text-sm text-slate-600"><span className="font-medium">Acceptable alternatives:</span> {question.acceptable_alternatives}</p>}{question.reference_solution && <p className="mt-2 whitespace-pre-wrap text-sm text-slate-600"><span className="font-medium">Reference solution:</span> {question.reference_solution}</p>}{question.marking_notes && <p className="mt-2 text-sm text-slate-600"><span className="font-medium">Marking notes:</span> {question.marking_notes}</p>}{!question.model_answer && !(criteria[question.id] ?? []).length && !question.reference_solution && !question.key_concepts && <p className="mt-2 text-sm text-amber-700">Add a model answer or marking criteria before evaluation.</p>}<p className="mt-2 text-xs text-slate-500">Sequence: {question.sequence_order}</p></div>
                    <div className="flex h-fit gap-2"><button onClick={() => setEditingQuestionId(question.id)} className="border border-slate-300 text-slate-700 hover:bg-slate-50">Edit</button><button onClick={() => void removeQuestion(question.id)} className="border border-red-200 text-red-700 hover:bg-red-50">Delete</button></div>
                  </div>
                )}

                <div className="mt-4 border-t pt-4">
                  <p className="text-sm font-medium">Rubric criteria</p>
                  <ul className="mt-2 space-y-2 text-sm text-slate-600">
                    {(criteria[question.id] ?? []).map((criterion) => (
                      <li key={criterion.id} className="rounded border border-slate-100 p-3">
                        {editingCriterionId === criterion.id ? (
                          <form onSubmit={(event) => updateCriterion(event, question.id, criterion)} className="grid gap-2 md:grid-cols-2">
                            <input name="criterion" defaultValue={criterion.criterion} required />
                            <input name="maximum_marks" type="number" min="0" step="0.01" defaultValue={criterion.maximum_marks} required />
                            <input name="sequence_order" type="number" min="0" defaultValue={criterion.sequence_order} required />
                            <input name="description" defaultValue={criterion.description ?? ""} placeholder="Description (optional)" />
                            <div className="flex gap-2"><button className="bg-slate-800 text-white">Save</button><button type="button" onClick={() => setEditingCriterionId(null)} className="border">Cancel</button></div>
                          </form>
                        ) : (
                          <div className="flex justify-between gap-3"><div><span>{criterion.sequence_order}. {criterion.criterion} — {criterion.maximum_marks} marks</span>{criterion.description && <p className="mt-1 text-xs">{criterion.description}</p>}</div><div className="flex h-fit gap-2"><button onClick={() => setEditingCriterionId(criterion.id)} className="border border-slate-300 text-slate-700 hover:bg-slate-50">Edit</button><button onClick={() => void removeCriterion(question.id, criterion.id)} className="border border-red-200 text-red-700 hover:bg-red-50">Delete</button></div></div>
                        )}
                      </li>
                    ))}
                  </ul>

                  {addingFor === question.id ? (
                    <form onSubmit={(event) => addCriterion(event, question.id)} className="mt-3 grid gap-2 md:grid-cols-2">
                      <input name="criterion" placeholder="Criterion" required />
                      <input name="maximum_marks" type="number" min="0" step="0.01" placeholder="Marks" required />
                      <input name="sequence_order" type="number" min="0" placeholder="Order" required />
                      <input name="description" placeholder="Description (optional)" />
                      <div className="flex gap-2"><button className="bg-slate-800 text-white">Save criterion</button><button type="button" onClick={() => setAddingFor(null)} className="border">Cancel</button></div>
                    </form>
                  ) : <button onClick={() => setAddingFor(question.id)} className="mt-3 border border-slate-300 text-slate-700 hover:bg-slate-50">Add criterion</button>}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </ExamShell>
  );
}
