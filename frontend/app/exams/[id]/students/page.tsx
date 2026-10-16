"use client";

import { FormEvent, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { ExamShell } from "@/components/exam-shell";
import { api, ApiError, Exam, Student, StudentImportResult } from "@/lib/api-client";

function message(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong. Please try again.";
}

export default function StudentsPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [exam, setExam] = useState<Exam | null>(null);
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState("");
  const [operationError, setOperationError] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<StudentImportResult | null>(null);
  const [selectedStudentIds, setSelectedStudentIds] = useState<Set<string>>(new Set());

  async function refreshStudents(showPageError = true): Promise<boolean> {
    setLoading(true);
    try {
      const items = await api<Student[]>("/api/exams/" + params.id + "/students");
      setStudents(items);
      const availableIds = new Set(items.map((student) => student.id));
      setSelectedStudentIds((current) => new Set([...current].filter((studentId) => availableIds.has(studentId))));
      setPageError("");
      return true;
    } catch (requestError) {
      if (showPageError) setPageError(message(requestError));
      if (requestError instanceof ApiError && requestError.status === 401) router.replace("/login");
      return false;
    } finally {
      setLoading(false);
    }
  }

  async function load() {
    setLoading(true);
    try {
      const currentExam = await api<Exam>("/api/exams/" + params.id);
      setExam(currentExam);
      setPageError("");
    } catch (requestError) {
      setPageError(message(requestError));
      if (requestError instanceof ApiError && requestError.status === 401) router.replace("/login");
    }
    await refreshStudents();
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps, react-hooks/set-state-in-effect
  useEffect(() => { void load(); }, [params.id]);

  async function addStudent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    setOperationError("");
    try {
      const student = await api<Student>("/api/exams/" + params.id + "/students", {
        method: "POST",
        body: JSON.stringify({ name: form.get("name"), roll_number: form.get("roll_number") || null, external_id: form.get("external_id") || null }),
      });
      setStudents((current) => [...current, student].sort((a, b) => a.name.localeCompare(b.name)));
      formElement.reset();
      if (!await refreshStudents(false)) {
        setOperationError("Student was added successfully, but the list could not be refreshed.");
      }
    } catch (requestError) { setOperationError(message(requestError)); }
  }

  async function updateStudent(event: FormEvent<HTMLFormElement>, student: Student) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setOperationError("");
    try {
      const updated = await api<Student>("/api/students/" + student.id, {
        method: "PUT",
        body: JSON.stringify({ name: form.get("name"), roll_number: form.get("roll_number") || null, external_id: form.get("external_id") || null }),
      });
      setStudents((current) => current.map((item) => item.id === updated.id ? updated : item).sort((a, b) => a.name.localeCompare(b.name)));
      setEditingId(null);
      if (!await refreshStudents(false)) {
        setOperationError("Student was updated successfully, but the list could not be refreshed.");
      }
    } catch (requestError) { setOperationError(message(requestError)); }
  }

  async function deleteStudent(student: Student) {
    if (!window.confirm("Delete " + student.name + "? Any uploaded answer sheets for this student will also be removed.")) return;
    try {
      await api<void>("/api/students/" + student.id, { method: "DELETE" });
      setStudents((current) => current.filter((item) => item.id !== student.id));
      setOperationError("");
      if (!await refreshStudents(false)) {
        setOperationError("Student was deleted successfully, but the list could not be refreshed.");
      }
    } catch (requestError) { setOperationError(message(requestError)); }
  }

  async function importStudents(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!importFile || importing) return;
    const formElement = event.currentTarget;
    setOperationError("");
    setImportResult(null);
    setImporting(true);
    try {
      const form = new FormData();
      form.append("file", importFile);
      const result = await api<StudentImportResult>("/api/exams/" + params.id + "/students/import", { method: "POST", body: form });
      setImportResult(result);
      setImportFile(null);
      formElement.reset();
      if (!await refreshStudents(false)) {
        setOperationError("Students were imported successfully, but the list could not be refreshed.");
      }
    } catch (requestError) {
      setOperationError(message(requestError));
    } finally {
      setImporting(false);
    }
  }

  function selectAllStudents() {
    setSelectedStudentIds(new Set(students.map((student) => student.id)));
  }

  function toggleStudentSelection(studentId: string) {
    setSelectedStudentIds((current) => {
      const updated = new Set(current);
      if (updated.has(studentId)) updated.delete(studentId);
      else updated.add(studentId);
      return updated;
    });
  }

  return (
    <ExamShell examId={params.id} examName={exam?.name ?? null}>
      <section className="rounded-lg border bg-white p-6">
        <h2 className="font-semibold">Add student</h2>
        <form onSubmit={addStudent} className="mt-4 grid gap-3 md:grid-cols-3">
          <input name="name" placeholder="Student name" required />
          <input name="roll_number" placeholder="Roll number (optional)" />
          <input name="external_id" placeholder="External ID (optional)" />
          <button className="w-fit bg-blue-700 text-white hover:bg-blue-800">Add student</button>
        </form>
      </section>
      <section className="mt-6 rounded-lg border bg-white p-6">
        <h2 className="font-semibold">Bulk import students</h2>
        <p className="mt-1 text-sm text-slate-600">Upload a CSV or XLSX roster. Required: <code>name</code>. Optional: <code>roll_number</code>, <code>external_id</code>.</p>
        <form onSubmit={importStudents} className="mt-4 flex flex-wrap items-center gap-3">
          <input type="file" accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={(event) => setImportFile(event.target.files?.[0] ?? null)} aria-label="Student roster file" />
          <button type="submit" disabled={!importFile || importing} className="bg-blue-700 text-white hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-50">{importing ? "Importing…" : "Import Students"}</button>
          <a className="border border-slate-300 text-slate-700 hover:bg-slate-50" href="/student-roster-template.csv" download>Download CSV Template</a>
        </form>
        {importResult && <div className="mt-4 rounded-md bg-slate-50 p-4 text-sm text-slate-700" role="status">
          <p className="font-medium">Imported {importResult.imported_count} of {importResult.total_rows} students.</p>
          {importResult.skipped_count > 0 && <p className="mt-1 text-amber-800">{importResult.skipped_count} row{importResult.skipped_count === 1 ? " was" : "s were"} skipped.</p>}
          {importResult.errors.length > 0 && <ul className="mt-3 list-disc space-y-1 pl-5 text-amber-900">{importResult.errors.map((issue, index) => <li key={`${issue.row}-${issue.field}-${index}`}>Row {issue.row} — {issue.message}</li>)}</ul>}
        </div>}
      </section>
      {pageError && <p className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{pageError}</p>}
      {operationError && <p className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{operationError}</p>}
      <section className="mt-8">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">Students</h2>
          {!loading && students.length > 0 && <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="text-slate-600">{selectedStudentIds.size} student{selectedStudentIds.size === 1 ? "" : "s"} selected</span>
            <button type="button" onClick={selectAllStudents} disabled={selectedStudentIds.size === students.length} className="border border-slate-300 text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50">Select All</button>
            <button type="button" onClick={() => setSelectedStudentIds(new Set())} disabled={selectedStudentIds.size === 0} className="border border-slate-300 text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50">Clear Selection</button>
          </div>}
        </div>
        {loading ? <p className="text-slate-600">Loading students…</p> : students.length === 0 ? <div className="rounded-lg border border-dashed bg-white p-10 text-center text-slate-600">No students have been added. Add a student before uploading an answer sheet.</div> : (
          <div className="overflow-hidden rounded-lg border bg-white">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-600"><tr><th className="w-12 p-4"><input type="checkbox" aria-label="Select all students" checked={students.length > 0 && selectedStudentIds.size === students.length} onChange={(event) => event.target.checked ? selectAllStudents() : setSelectedStudentIds(new Set())} /></th><th className="p-4">Name</th><th className="p-4">Roll number</th><th className="p-4">External ID</th><th className="p-4">Actions</th></tr></thead>
              <tbody>{students.map((student) => <tr key={student.id} className="border-t">
                {editingId === student.id ? <td colSpan={5} className="p-4"><form onSubmit={(event) => updateStudent(event, student)} className="grid gap-3 md:grid-cols-3"><input name="name" defaultValue={student.name} required /><input name="roll_number" defaultValue={student.roll_number ?? ""} placeholder="Roll number" /><input name="external_id" defaultValue={student.external_id ?? ""} placeholder="External ID" /><div className="flex gap-2"><button className="bg-blue-700 text-white">Save</button><button type="button" onClick={() => setEditingId(null)} className="border">Cancel</button></div></form></td> : <><td className="p-4"><input type="checkbox" aria-label={`Select ${student.name}`} checked={selectedStudentIds.has(student.id)} onChange={() => toggleStudentSelection(student.id)} /></td><td className="p-4 font-medium">{student.name}</td><td className="p-4">{student.roll_number || "—"}</td><td className="p-4">{student.external_id || "—"}</td><td className="p-4"><div className="flex gap-2"><button onClick={() => setEditingId(student.id)} className="border border-slate-300 text-slate-700 hover:bg-slate-50">Edit</button><button onClick={() => void deleteStudent(student)} className="border border-red-200 text-red-700 hover:bg-red-50">Delete</button></div></td></>}
              </tr>)}</tbody>
            </table>
          </div>
        )}
      </section>
    </ExamShell>
  );
}
