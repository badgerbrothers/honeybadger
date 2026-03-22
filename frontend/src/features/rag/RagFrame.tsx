"use client";

import type { ReactNode } from "react";

import { RagProvider } from "./RagContext";
import { RagShell } from "./RagShell";

export function RagFrame({ children }: { children: ReactNode }) {
  return (
    <RagProvider>
      <RagShell>{children}</RagShell>
    </RagProvider>
  );
}

