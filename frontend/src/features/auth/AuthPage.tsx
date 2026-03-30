"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";

import { AuthLogo } from "@/features/auth/AuthLogo";
// import { AuthOAuthButtons } from "@/features/auth/AuthOAuthButtons";
import { useAuth } from "@/lib/auth/AuthContext";

export type AuthMode = "login" | "register";

interface AuthPageProps {
  mode: AuthMode;
}

export function AuthPage({ mode }: AuthPageProps) {
  const isLogin = mode === "login";
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") || "/conversation";

  const { login, register } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = useMemo(() => {
    if (!email.trim() || !password) return false;
    if (!isLogin && password.length < 8) return false;
    if (!isLogin && password !== confirmPassword) return false;
    return true;
  }, [confirmPassword, email, isLogin, password]);

  return (
    <main className="auth-page">
      <section className="auth-card">
        <AuthLogo />
        <h1 className="auth-title">{isLogin ? "欢迎回来" : "创建账号"}</h1>
        <p className="auth-subtitle">
          {isLogin ? "登录您的 Manus Agent 工作台" : "注册您的 Manus Agent 工作台"}
        </p>

        <form
          onSubmit={async (e) => {
            e.preventDefault();
            if (!canSubmit || submitting) return;
            setSubmitting(true);
            setError(null);
            try {
              if (isLogin) {
                await login(email.trim(), password);
              } else {
                await register(email.trim(), password);
              }
              router.replace(next);
            } catch (err) {
              const message =
                err instanceof Error ? err.message : "Authentication failed";
              setError(message);
            } finally {
              setSubmitting(false);
            }
          }}
        >
          <div className="auth-formGroup">
            <label className="auth-label" htmlFor="auth-email">
              邮箱地址
            </label>
            <input
              id="auth-email"
              name="email"
              type="email"
              className="auth-input"
              placeholder="you@company.com"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div className="auth-formGroup">
            {isLogin ? (
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
                <label className="auth-label" htmlFor="auth-password" style={{ marginBottom: 0 }}>
                  密码
                </label>
                <a className="auth-forgotLink" href="#">
                  忘记密码?
                </a>
              </div>
            ) : (
              <label className="auth-label" htmlFor="auth-password">
                密码
              </label>
            )}
            <input
              id="auth-password"
              name="password"
              type="password"
              className="auth-input"
              placeholder="••••••••"
              required
              minLength={isLogin ? undefined : 8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {!isLogin ? <p className="auth-hint">建议 8 位以上，包含字母与数字。</p> : null}
          </div>

          {!isLogin ? (
            <div className="auth-formGroup">
              <label className="auth-label" htmlFor="auth-confirm-password">
                确认密码
              </label>
              <input
                id="auth-confirm-password"
                name="confirmPassword"
                type="password"
                className="auth-input"
                placeholder="••••••••"
                required
                minLength={8}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
              />
            </div>
          ) : null}

          {error ? (
            <div
              style={{
                border: "1px solid #fecaca",
                background: "#fef2f2",
                color: "#991b1b",
                padding: "0.6rem 0.75rem",
                borderRadius: "0.75rem",
                fontSize: "0.9rem",
              }}
              role="alert"
            >
              {error}
            </div>
          ) : null}

          <button type="submit" className="auth-btnPrimary" disabled={!canSubmit || submitting}>
            {isLogin ? "登录" : "注册"}
          </button>
        </form>

        {/* <div className="auth-divider">或</div>

        <AuthOAuthButtons /> */}

        <p className="auth-footer">
          {isLogin ? (
            <>
              还没有账号？ <Link href="/register">免费注册</Link>
            </>
          ) : (
            <>
              已有账号？ <Link href="/login">去登录</Link>
            </>
          )}
        </p>
      </section>
    </main>
  );
}
