import "./workspace.css";

import type { ReactNode } from "react";

import { WorkspaceFrame } from "@/features/workspace/WorkspaceFrame";

export default function WorkspaceLayout({ children }: { children: ReactNode }) {
  return <WorkspaceFrame>{children}</WorkspaceFrame>;
}
