"use client";

import type { ReactNode } from "react";

import { RequireAuth } from "@/lib/auth/RequireAuth";

import { RagProvider } from "./RagContext";
import { RagShell } from "./RagShell";

export function RagFrame({ children }: { children: ReactNode }) {
  return (
    <RequireAuth>
      <RagProvider>
        <RagShell>{children}</RagShell>
      </RagProvider>
    </RequireAuth>
  );
}
