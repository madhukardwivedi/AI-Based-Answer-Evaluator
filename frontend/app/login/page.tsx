"use client";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, User } from "@/lib/api-client";
export default function LoginPage() {
  const router = useRouter(); const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [error, setError] = useState(""); const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setLoading(true); setError(""); try { await api<User>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }); router.replace("/dashboard"); } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to sign in"); } finally { setLoading(false); } }
  return <main className="grid min-h-screen place-items-center p-6"><form onSubmit={submit} className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-8 shadow-sm"><h1 className="text-2xl font-semibold">Evaluator sign in</h1><p className="mt-2 text-sm text-slate-600">Use the evaluator account created locally by your administrator.</p>{error && <p className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}<label className="mt-6 block text-sm font-medium">Email<input className="mt-1" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></label><label className="mt-4 block text-sm font-medium">Password<input className="mt-1" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label><button disabled={loading} className="mt-6 w-full bg-blue-700 text-white hover:bg-blue-800">{loading ? "Signing in…" : "Sign in"}</button></form></main>;
}

