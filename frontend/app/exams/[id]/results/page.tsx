"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { ExamShell } from "@/components/exam-shell";
import { api, ApiError, Exam, StudentResult } from "@/lib/api-client";

export default function ResultsPage() {
  const { id } = useParams<{ id: string }>();
  const [exam, setExam] = useState<Exam | null>(null);
  const [rows, setRows] = useState<StudentResult[]>([]);
  const [error, setError] = useState("");
  useEffect(() => { void Promise.all([api<Exam>(`/api/exams/${id}`), api<StudentResult[]>(`/api/exams/${id}/results`)]).then(([loadedExam, results]) => { setExam(loadedExam); setRows(results); }).catch((requestError) => setError(requestError instanceof ApiError ? requestError.message : "Unable to load results.")); }, [id]);

  return <ExamShell examId={id} examName={exam?.name ?? null}>
    {error && <p className="mb-4 rounded bg-red-50 p-3 text-red-700">{error}</p>}
    <div className="mb-4 flex gap-2"><a className="inline-block border p-2" href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/exams/${id}/results.csv`}>Download CSV</a><a className="inline-block border p-2" href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/exams/${id}/results.xlsx`}>Download XLSX</a></div>
    <div className="overflow-hidden rounded border bg-white"><table className="w-full text-left text-sm"><thead><tr><th className="p-3">Student</th><th>Question-wise</th><th>Total</th><th>Percentage</th><th>Status</th></tr></thead><tbody>{rows.map((row) => <tr key={row.submission_id} className="border-t align-top"><td className="p-3">{row.student_name}<p>{row.roll_number || "—"}</p></td><td className="py-3">{row.questions.map((question) => <div className="mr-2" key={question.question_number}><b>{question.question_number}</b>: AI {question.ai_marks ?? "—"} · Faculty {question.faculty_marks ?? "—"} · Final {question.final_marks ?? "—"}/{question.maximum_marks}</div>)}</td><td className="py-3">{row.total_marks}/{row.maximum_marks}</td><td className="py-3">{Number(row.percentage).toFixed(1)}%</td><td className="py-3 capitalize">{row.status.replaceAll("_", " ")}</td></tr>)}</tbody></table></div>
  </ExamShell>;
}
