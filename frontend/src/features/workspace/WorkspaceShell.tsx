"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { workspaceNavItems } from "./nav";

interface WorkspaceShellProps {
  title: string;
  action?: ReactNode;
  children: ReactNode;
  subtle?: boolean;
  fluid?: boolean;
}

export function WorkspaceShell({
  title,
  action,
  children,
  subtle = false,
  fluid = false,
}: WorkspaceShellProps) {
  const pathname = usePathname();

  return (
    <div className="manus-workspace">
      <aside className="manus-sidebar">
        <div className="manus-sidebar-header">Manus 工作台</div>
        <nav>
          {workspaceNavItems.map((item) => {
            const Icon = item.icon;
            const active =
              pathname === item.href ||
              (item.href !== "/" && pathname.startsWith(`${item.href}/`));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`manus-nav-item ${active ? "active" : ""}`}
              >
                <Icon size={18} />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <main className={`manus-main-content ${subtle ? "subtle" : ""}`}>
        <header className="manus-page-header">
          <h1 className="manus-page-title">{title}</h1>
          {action ?? <div />}
        </header>
        <div className={`manus-content-area ${fluid ? "fluid" : ""}`}>{children}</div>
      </main>
    </div>
  );
}
