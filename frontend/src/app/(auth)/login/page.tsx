import type { Metadata } from "next";

import { AuthPage } from "@/features/auth/AuthPage";

export const metadata: Metadata = {
  title: "登录 - Manus Clone",
};

export default function LoginPage() {
  return <AuthPage mode="login" />;
}

