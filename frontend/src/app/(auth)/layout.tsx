import "@/features/auth/auth.css";

import type { ReactNode } from "react";

export default function AuthLayout({ children }: { children: ReactNode }) {
  // Auth pages render their own centered shell; layout exists to load auth CSS.
  return <>{children}</>;
}
