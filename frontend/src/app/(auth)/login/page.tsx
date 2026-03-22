import type { Metadata } from "next";
import { Suspense } from "react";

import { AuthPage } from "@/features/auth/AuthPage";

export const metadata: Metadata = {
  title: "登录 - Manus Clone",
};

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <AuthPage mode="login" />
    </Suspense>
  );
}
