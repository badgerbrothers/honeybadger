import type { Metadata } from "next";
import { Suspense } from "react";

import { AuthPage } from "@/features/auth/AuthPage";

export const metadata: Metadata = {
  title: "注册 - Manus Clone",
};

export default function RegisterPage() {
  return (
    <Suspense fallback={null}>
      <AuthPage mode="register" />
    </Suspense>
  );
}
