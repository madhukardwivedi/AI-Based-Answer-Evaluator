"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { PortalShell } from "@/components/portal-shell";

const tabs = [
  { label: "Questions", path: "" },
  { label: "Students", path: "/students" },
  { label: "Answer Sheets", path: "/answer-sheets" },
  { label: "Question Paper", path: "/question-paper" },
  { label: "Extraction", path: "/extraction" },
  { label: "Evaluation", path: "/evaluation" },
  { label: "Results", path: "/results" },
] as const;

export function ExamShell({ examId, examName, children }: Readonly<{ examId: string; examName: string | null; children: React.ReactNode }>) {
  const pathname = usePathname();
  const basePath = `/exams/${examId}`;

  return <PortalShell title={examName ?? "Exam"}>
    <div className="mb-6 border-b border-slate-200">
      <nav className="overflow-x-auto pb-4" aria-label="Exam sections">
        <div className="flex min-w-max gap-2 text-sm">
          {tabs.map((tab) => {
            const href = `${basePath}${tab.path}`;
            const active = pathname === href;
            return <Link key={tab.path} href={href} aria-current={active ? "page" : undefined} className={active ? "rounded-md bg-slate-900 px-3 py-2 font-medium text-white" : "rounded-md px-3 py-2 text-slate-700 hover:bg-slate-100"}>{tab.label}</Link>;
          })}
        </div>
      </nav>
    </div>
    {children}
  </PortalShell>;
}
