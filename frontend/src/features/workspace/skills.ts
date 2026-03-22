export type SkillTool = "browser" | "shell" | "python" | "fileio";

export interface WorkspaceSkill {
  id: string;
  name: string;
  summary: string;
  description: string;
  iconKind: "browser" | "terminal" | "python" | "file";
  tools: SkillTool[];
  usage: string[];
  markdown: string;
}

export const workspaceSkills: WorkspaceSkill[] = [
  {
    id: "code-review-report",
    name: "Code Review 报告",
    summary: "扫描变更、识别风险并生成结构化 Markdown 报告。",
    description:
      "聚合代码差异、目录结构和关键日志，自动提炼高风险问题、测试缺口和修复建议，输出可直接发送的审查报告。",
    iconKind: "file",
    tools: ["fileio", "shell"],
    usage: [
      "读取当前分支改动并定位高风险文件",
      "执行静态检查命令并汇总失败项",
      "生成包含严重级别的 Markdown 报告",
    ],
    markdown: `# Code Review 报告

## 概述
扫描变更、识别风险并生成结构化 Markdown 报告。

## 使用的工具
- File I/O
- Shell

## 步骤
1. 读取当前分支改动并定位高风险文件
2. 执行静态检查命令并汇总失败项
3. 生成包含严重级别的 Markdown 报告
`,
  },
  {
    id: "research-brief",
    name: "竞品研究简报",
    summary: "抓取公开资料，整理成对比结论和行动建议。",
    description:
      "基于网络信息源抽取核心指标，输出可追溯引用的竞品对比摘要，适合周报或方案评审前的快速预研。",
    iconKind: "browser",
    tools: ["browser", "fileio"],
    usage: [
      "检索指定行业或产品的最新公开资料",
      "提炼功能、定价与发布时间线",
      "汇总为简报并落盘到工作区文档",
    ],
    markdown: `# 竞品研究简报

## 概述
抓取公开资料，整理成对比结论和行动建议。

## 使用的工具
- Web Browser
- File I/O

## 步骤
1. 检索指定行业或产品的最新公开资料
2. 提炼功能、定价与发布时间线
3. 汇总为简报并落盘到工作区文档
`,
  },
  {
    id: "data-cleaning",
    name: "数据清洗与图表",
    summary: "读取 CSV，完成清洗、统计并输出图表结论。",
    description:
      "自动执行缺失值处理、字段标准化与基础统计分析，并生成可直接复用的图表和简要说明。",
    iconKind: "python",
    tools: ["python", "fileio"],
    usage: [
      "读取并清洗原始 CSV 数据",
      "生成关键指标统计和趋势图",
      "导出结果文件与分析结论",
    ],
    markdown: `# 数据清洗与图表

## 概述
读取 CSV，完成清洗、统计并输出图表结论。

## 使用的工具
- Python
- File I/O

## 步骤
1. 读取并清洗原始 CSV 数据
2. 生成关键指标统计和趋势图
3. 导出结果文件与分析结论
`,
  },
];

export function getWorkspaceSkill(skillId: string) {
  return workspaceSkills.find((skill) => skill.id === skillId) ?? null;
}
