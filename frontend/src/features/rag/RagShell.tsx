"use client";

import type { ReactNode } from "react";

import { RagSidebar } from "./RagSidebar";

export function RagShell({ children }: { children: ReactNode }) {
  return (
    <div className="manus-workspace rag-workspace">
      <RagSidebar />
      <main className="manus-main-content">{children}</main>
    </div>
  );
}
