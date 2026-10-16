"use client";

import { ChangeEvent, DragEvent, FormEvent, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { ExamShell } from "@/components/exam-shell";
import { AnswerSheet, api, ApiError, Exam, Student } from "@/lib/api-client";

function message(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong. Please try again.";
}

function formatSize(bytes: number): string {
  return bytes < 1024 * 1024 ? (bytes / 1024).toFixed(1) + " KB" : (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

export default function AnswerSheetsPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [exam, setExam] = useState<Exam | null>(null);
  const [students, setStudents] = useState<Student[]>([]);
  const [sheets, setSheets] = useState<AnswerSheet[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedStudent, setSelectedStudent] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [processingId, setProcessingId] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const [currentExam, currentStudents, currentSheets] = await Promise.all([
        api<Exam>("/api/exams/" + params.id),
        api<Student[]>("/api/exams/" + params.id + "/students"),
        api<AnswerSheet[]>("/api/exams/" + params.id + "/answer-sheets"),
      ]);
      setExam(currentExam); setStudents(currentStudents); setSheets(currentSheets); setError("");
    } catch (requestError) {
      setError(message(requestError));
      if (requestError instanceof ApiError && requestError.status === 401) router.replace("/login");
    } finally { setLoading(false); }
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps, react-hooks/set-state-in-effect
  useEffect(() => { void load(); }, [params.id]);

  function chooseFile(file: File | null) {
    if (!file) return;
    const allowed = ["application/pdf", "image/jpeg", "image/png"];
    if (!allowed.includes(file.type)) {
      setError("Choose a PDF, JPG, JPEG, or PNG file.");
      return;
    }
    setSelectedFile(file); setError("");
  }

  function onInputChange(event: ChangeEvent<HTMLInputElement>) { chooseFile(event.target.files?.[0] ?? null); }
  function onDrop(event: DragEvent<HTMLLabelElement>) { event.preventDefault(); chooseFile(event.dataTransfer.files[0] ?? null); }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    if (!selectedStudent || !selectedFile) { setError("Select a student and answer sheet file."); return; }
    setUploading(true); setError("");
    const form = new FormData();
    form.set("student_id", selectedStudent); form.set("file", selectedFile);
    try {
      const sheet = await api<AnswerSheet>("/api/exams/" + params.id + "/answer-sheets", { method: "POST", body: form });
      setSheets((current) => [sheet, ...current]);
      setSelectedFile(null); setSelectedStudent(""); formElement.reset();
    } catch (requestError) { setError(message(requestError)); }
    finally { setUploading(false); }
  }

  async function deleteSheet(sheet: AnswerSheet) {
    if (!window.confirm("Delete this answer sheet? This removes the uploaded submission, extracted answers, evaluations, and derived results. The student roster entry and exam questions will be kept.")) return;
    try { await api<void>("/api/answer-sheets/" + sheet.id, { method: "DELETE" }); setSheets((current) => current.filter((item) => item.id !== sheet.id)); setError(""); }
    catch (requestError) { setError(message(requestError)); }
  }
  async function processSheet(sheet: AnswerSheet) {
    setProcessingId(sheet.id); setError("");
    try { await api("/api/answer-sheets/" + sheet.id + "/process", { method: "POST" }); setSheets((items) => items.map((item) => item.id === sheet.id ? { ...item, status: "extracted" } : item)); router.push("/exams/" + params.id + "/extraction"); }
    catch (requestError) { setError(message(requestError)); } finally { setProcessingId(null); }
  }

  return (
    <ExamShell examId={params.id} examName={exam?.name ?? null}>
      <section className="rounded-lg border bg-white p-6">
        <h2 className="font-semibold">Upload answer sheet</h2>
        {students.length === 0 ? <p className="mt-3 rounded-md bg-amber-50 p-3 text-sm text-amber-800">Add a student before uploading an answer sheet.</p> : <form onSubmit={upload} className="mt-4 space-y-4">
          <label className="block max-w-md text-sm font-medium">Student<select className="mt-1" value={selectedStudent} onChange={(event) => setSelectedStudent(event.target.value)} required><option value="">Select a student</option>{students.map((student) => <option key={student.id} value={student.id}>{student.name}{student.roll_number ? " · " + student.roll_number : ""}</option>)}</select></label>
          <label onDragOver={(event) => event.preventDefault()} onDrop={onDrop} className="block cursor-pointer rounded-lg border-2 border-dashed border-slate-300 p-6 text-center text-sm text-slate-600 hover:border-blue-500">
            <input className="sr-only" type="file" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" onChange={onInputChange} />
            {selectedFile ? <span><strong>{selectedFile.name}</strong> · {formatSize(selectedFile.size)}</span> : <span>Drag a PDF or image here, or click to choose a file.</span>}
          </label>
          <button disabled={uploading || !selectedFile || !selectedStudent} className="bg-blue-700 text-white hover:bg-blue-800">{uploading ? "Uploading…" : "Upload answer sheet"}</button>
        </form>}
      </section>
      {error && <p className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      <section className="mt-8">
        <h2 className="mb-4 text-lg font-semibold">Uploaded answer sheets</h2>
        {loading ? <p className="text-slate-600">Loading uploads…</p> : sheets.length === 0 ? <div className="rounded-lg border border-dashed bg-white p-10 text-center text-slate-600">No answer sheets have been uploaded.</div> : <div className="overflow-hidden rounded-lg border bg-white"><table className="w-full text-left text-sm"><thead className="bg-slate-50 text-slate-600"><tr><th className="p-4">Student</th><th className="p-4">File</th><th className="p-4">Uploaded</th><th className="p-4">Status</th><th className="p-4">Action</th></tr></thead><tbody>{sheets.map((sheet) => <tr key={sheet.id} className="border-t"><td className="p-4">{sheet.student_name || "Unknown"}<p className="text-slate-500">{sheet.student_roll_number || "—"}</p></td><td className="p-4">{sheet.original_filename}<p className="text-slate-500">{formatSize(sheet.file_size)}</p></td><td className="p-4">{new Date(sheet.uploaded_at).toLocaleString()}</td><td className="p-4 capitalize">{sheet.status.replace("_", " ")}</td><td className="flex gap-2 p-4">{sheet.status === "uploaded" || sheet.status === "failed" ? <button disabled={processingId === sheet.id} onClick={() => void processSheet(sheet)} className="border border-blue-200 text-blue-700">{processingId === sheet.id ? "Processing…" : "Process / Extract"}</button> : null}<button onClick={() => void deleteSheet(sheet)} className="border border-red-200 text-red-700 hover:bg-red-50">Delete</button></td></tr>)}</tbody></table></div>}
      </section>
    </ExamShell>
  );
}
