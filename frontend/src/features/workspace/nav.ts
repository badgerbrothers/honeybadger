import type { LucideIcon } from "lucide-react";
import {
  BookOpenText,
  Boxes,
  ClipboardList,
  LayoutDashboard,
  MessageSquare,
  Settings,
  Wrench,
} from "lucide-react";

export interface WorkspaceNavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

export const workspaceNavItems: WorkspaceNavItem[] = [
  { href: "/", label: "工作区会话", icon: MessageSquare },
  { href: "/dashboard", label: "任务看板", icon: LayoutDashboard },
  { href: "/tasks/kanban", label: "任务队列看板", icon: ClipboardList },
  { href: "/runs/demo", label: "执行画板", icon: Boxes },
  { href: "/artifacts", label: "产出物库", icon: BookOpenText },
  { href: "/knowledge", label: "知识库与记忆", icon: BookOpenText },
  { href: "/tools", label: "工具与技能", icon: Wrench },
  { href: "/settings", label: "系统设置", icon: Settings },
];
