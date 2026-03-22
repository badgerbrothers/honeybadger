import Link from "next/link";

import { AuthLogo } from "@/features/auth/AuthLogo";
import { AuthOAuthButtons } from "@/features/auth/AuthOAuthButtons";

export type AuthMode = "login" | "register";

interface AuthPageProps {
  mode: AuthMode;
}

export function AuthPage({ mode }: AuthPageProps) {
  const isLogin = mode === "login";

  return (
    <main className="auth-page">
      <section className="auth-card">
        <AuthLogo />
        <h1 className="auth-title">{isLogin ? "欢迎回来" : "创建账号"}</h1>
        <p className="auth-subtitle">
          {isLogin ? "登录您的 Manus Agent 工作台" : "注册您的 Manus Agent 工作台"}
        </p>

        <form action="/dashboard" method="GET">
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
              />
            </div>
          ) : null}

          <button type="submit" className="auth-btnPrimary">
            {isLogin ? "登录" : "注册"}
          </button>
        </form>

        <div className="auth-divider">或</div>

        <AuthOAuthButtons />

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

