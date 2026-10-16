import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "Answer Evaluator", description: "Evaluator exam configuration portal" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }

