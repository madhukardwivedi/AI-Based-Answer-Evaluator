"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";
export function PortalShell({ title, children }: Readonly<{ title: string; children: React.ReactNode }>) {
  const router = useRouter();
  async function logout() { await api<void>("/api/auth/logout", { method: "POST" }); router.push("/login"); }
  return <main className="min-h-screen"><header className="border-b border-slate-200 bg-white"><div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4"><Link href="/dashboard" className="font-semibold text-slate-900">Answer Evaluator</Link><nav className="flex items-center gap-4"><Link href="/exams" className="text-sm text-slate-600 hover:text-slate-900">Exams</Link><button onClick={logout} className="border border-slate-300 bg-white text-slate-700 hover:bg-slate-50">Sign out</button></nav></div></header><section className="mx-auto max-w-6xl px-6 py-8"><h1 className="mb-6 text-2xl font-semibold">{title}</h1>{children}</section></main>;
}

