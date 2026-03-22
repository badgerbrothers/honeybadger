import "./rag.css";

import type { ReactNode } from "react";

import { RagFrame } from "@/features/rag/RagFrame";

export default function RagLayout({ children }: { children: ReactNode }) {
  return <RagFrame>{children}</RagFrame>;
}

