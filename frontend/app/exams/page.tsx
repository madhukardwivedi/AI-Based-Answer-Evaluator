"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, Exam } from "@/lib/api-client";
import { PortalShell } from "@/components/portal-shell";
export default function ExamsPage() {
  const router = useRouter(); const [exams, setExams] = useState<Exam[]>([]); const [error, setError] = useState("");
  useEffect(() => { api<Exam[]>("/api/exams").then(setExams).catch(() => { setError("Unable to load exams."); router.replace("/login"); }); }, [router]);
  return <PortalShell title="Exams"><div className="mb-5 flex justify-end"><Link href="/exams/new" className="bg-blue-700 text-white hover:bg-blue-800">Create exam</Link></div>{error && <p className="text-red-700">{error}</p>}{exams.length === 0 ? <div className="rounded-lg border border-dashed bg-white p-10 text-center text-slate-600">No exams yet. Create your first exam to begin.</div> : <div className="overflow-hidden rounded-lg border bg-white"><table className="w-full text-left text-sm"><thead className="bg-slate-50 text-slate-600"><tr><th className="p-4">Exam</th><th className="p-4">Class</th><th className="p-4">Marks</th><th className="p-4">Status</th></tr></thead><tbody>{exams.map((exam) => <tr key={exam.id} className="border-t"><td className="p-4"><Link className="font-medium text-blue-700" href={"/exams/" + exam.id}>{exam.name}</Link><p className="text-slate-500">{exam.subject}</p></td><td className="p-4">{exam.class_name}</td><td className="p-4">{exam.total_marks}</td><td className="p-4 capitalize">{exam.status}</td></tr>)}</tbody></table></div>}</PortalShell>;
}

