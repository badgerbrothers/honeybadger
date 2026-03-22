import type { Metadata } from "next";

import { AuthPage } from "@/features/auth/AuthPage";

export const metadata: Metadata = {
  title: "注册 - Manus Clone",
};

export default function RegisterPage() {
  return <AuthPage mode="register" />;
}

