"use client";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, Exam } from "@/lib/api-client";
import { PortalShell } from "@/components/portal-shell";
export default function NewExamPage() {
  const router = useRouter(); const [error, setError] = useState(""); const [saving, setSaving] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const form = new FormData(event.currentTarget); setSaving(true); setError(""); try { const exam = await api<Exam>("/api/exams", { method: "POST", body: JSON.stringify({ name: form.get("name"), subject: form.get("subject"), class_name: form.get("class_name"), description: form.get("description") || null, total_marks: form.get("total_marks"), status: "draft" }) }); router.push("/exams/" + exam.id); } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to create exam"); } finally { setSaving(false); } }
  return <PortalShell title="Create exam"><form onSubmit={submit} className="max-w-2xl rounded-lg border bg-white p-6"><div className="grid gap-4 sm:grid-cols-2"><label className="text-sm font-medium">Exam name<input className="mt-1" name="name" required /></label><label className="text-sm font-medium">Subject<input className="mt-1" name="subject" required /></label><label className="text-sm font-medium">Class<input className="mt-1" name="class_name" required /></label><label className="text-sm font-medium">Total marks<input className="mt-1" name="total_marks" type="number" min="0" step="0.01" required /></label></div><label className="mt-4 block text-sm font-medium">Description<textarea className="mt-1" name="description" rows={3} /></label>{error && <p className="mt-4 text-sm text-red-700">{error}</p>}<button disabled={saving} className="mt-6 bg-blue-700 text-white hover:bg-blue-800">{saving ? "Creating…" : "Create exam"}</button></form></PortalShell>;
}

