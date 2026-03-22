"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { useAuth } from "./AuthContext";

export function RequireAuth({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { ready, isAuthenticated } = useAuth();
  const pathname = usePathname();

  useEffect(() => {
    if (!ready || isAuthenticated) return;
    const next =
      pathname && pathname !== "/login" ? `?next=${encodeURIComponent(pathname)}` : "";
    router.replace(`/login${next}`);
  }, [isAuthenticated, pathname, ready, router]);

  if (!ready || !isAuthenticated) return null;

  return <>{children}</>;
}
