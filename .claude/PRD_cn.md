# Badgers MVP - 产品需求文档

## 1. 执行摘要

Badgers MVP 是一个 AI 驱动的任务执行平台，使用户能够将复杂的多步骤工作流委托给自主代理。与传统聊天机器人不同，Badgers 为每个任务创建隔离的执行环境（沙箱），允许代理使用真实工具——浏览器、代码解释器、文件系统——来完成目标，如生成研究报告、构建网页或分析文档。

核心创新是任务执行循环：用户通过对话发起任务，系统创建专用沙箱，代理使用可用工具执行多个步骤，结果被捕获为持久保存在项目目录中的工件。这将 AI 从对话助手转变为能够产生有形交付成果的自主工作者。

MVP 验证单代理执行模型是否能够可靠地端到端完成现实世界的任务，为未来的多代理协作和企业功能奠定基础。

## 2. 使命

**使命宣言：** 赋能用户将复杂的多步骤任务委托给 AI 代理，这些代理可以使用真实工具自主执行工作流，产生超越对话的有形工件。

**核心原则：**

1. **以任务为中心，而非以聊天为中心：** 对话是任务启动的界面；核心产品是具有可观察进度和持久结果的可靠任务执行。

2. **默认隔离：** 每个任务运行在自己的沙箱中操作，具有独立状态，防止干扰并实现安全实验。

3. **工件优于临时响应：** 任务输出是结构化工件（报告、代码、数据文件），保存到项目目录，而不仅仅是滚动消失的聊天消息。

4. **可观察执行：** 用户看到逐步进度、工具调用和中间结果，通过透明度建立信任。

5. **模型无关架构：** 系统抽象模型提供商，支持 OpenAI 兼容 API、Anthropic 和未来的本地/自托管模型，而不将业务逻辑耦合到特定 SDK。

## 3. 目标用户

### 主要角色：技术专业人员

**简介：**
- 软件开发人员、数据分析师、研究人员、产品经理
- 熟悉技术概念但希望卸载重复或耗时的任务
- 从事需要研究、代码生成、数据分析或内容创建的项目
- 重视自动化但需要了解 AI 正在做什么

**技术舒适度：**
- 理解文件系统、API、基本编程概念
- 熟悉 markdown、JSON、命令行工具
- 可能不是 AI/ML 专家，但理解 LLM 的能力和局限性

**关键需求：**
- 委托多步骤工作流而无需编写自定义脚本
- 查看 AI 在每个步骤中正在做什么（透明度）
- 获取结构化输出（文件、报告、代码）而不仅仅是文本响应
- 在具有持久文件存储的项目中组织工作
- 重试失败的任务而不丢失上下文

**痛点：**
- 当前的 AI 聊天工具不产生持久的结构化输出
- 无法让 AI 访问真实工具（浏览器、代码执行）
- 难以跟踪 AI 在多个步骤中做了什么
- 对话结束时结果消失
- 无法以结构化方式在先前工作的基础上构建

## 4. MVP 范围

### ✅ 范围内

**核心功能：**
- ✅ 创建和管理具有目录结构的项目
- ✅ 通过对话界面发起任务
- ✅ 单代理多步骤任务执行循环
- ✅ 每个任务运行独立沙箱（基于 Docker）
- ✅ 实时任务状态更新（待处理、运行中、成功、失败、已取消）
- ✅ 具有新运行实例的任务重试能力
- ✅ 工件生成并导出到项目目录
- ✅ 查看任务执行日志和工具调用历史

**工具系统：**
- ✅ 浏览器自动化（打开、点击、输入、提取、截图）
- ✅ 文件操作（列出、读取、写入）
- ✅ Python 代码执行
- ✅ Web 内容获取
- ✅ 最终答案/结果提交

**数据与上下文：**
- ✅ 项目文件的轻量级 RAG（PDF、Markdown、TXT、Web 内容）
- ✅ 项目范围的文档检索
- ✅ 三层内存：对话摘要、项目事实、任务工作内存
- ✅ 文件上传到项目

**技术：**
- ✅ 统一模型抽象层（OpenAI 兼容 + Anthropic 原生）
- ✅ 基本模型路由（默认主模型、默认嵌入模型、每任务覆盖）
- ✅ WebSocket 或 SSE 用于实时任务事件
- ✅ 结构化日志记录以实现可观察性

**技能：**
- ✅ 轻量级技能模板（研究报告、网页生成、文件分析）
- ✅ 特定技能的系统提示和工具限制

### ❌ 范围外（未来阶段）

**协作：**
- ❌ 多代理并行执行
- ❌ 团队协作功能
- ❌ 组织/权限管理
- ❌ 实时多用户编辑

**平台：**
- ❌ 插件市场
- ❌ 完整的 MCP 生态系统集成
- ❌ 移动/桌面原生客户端
- ❌ 网站托管/部署平台
- ❌ 复杂的审批工作流

**高级功能：**
- ❌ 多线程对话
- ❌ 复杂的长期记忆网络
- ❌ 高级模型路由（自动回退、成本优化）
- ❌ 视觉模型能力（图像生成、视觉）

## 5. 用户故事

### 主要用户故事

**US-1: 研究报告生成**
- **作为** 研究人员
- **我想要** 要求系统调查一个主题并生成综合报告
- **以便** 我可以节省数小时的手动研究并获得结构化的引用发现
- **示例：** "研究特斯拉 2025 年第四季度财报并创建包含关键指标的摘要报告"

**US-2: 网页创建**
- **作为** 开发人员
- **我想要** 请求一个着陆页或 Web 组件
- **以便** 我可以快速原型化想法而无需编写样板 HTML/CSS/JS
- **示例：** "创建一个包含三个层级和比较表的定价页面"

**US-3: 文档分析**
- **作为** 分析师
- **我想要** 上传 PDF 或文档并询问有关其内容的问题
- **以便** 我可以提取见解而无需手动阅读数百页
- **示例：** "分析此合同 PDF 并列出所有付款条款和截止日期"

**US-4: 任务进度监控**
- **作为** 用户
- **我想要** 在代理执行每个步骤时看到实时更新
- **以便** 我了解正在发生什么并可以在需要时进行干预
- **示例：** 看到"打开浏览器 → 搜索数据 → 提取表格 → 生成报告"

**US-5: 失败后任务重试**
- **作为** 用户
- **我想要** 重试失败的任务而无需重新解释目标
- **以便** 我可以从瞬态错误或超时问题中恢复
- **示例：** 任务因网络超时而失败；点击"重试"创建新运行

**US-6: 项目组织**
- **作为** 用户
- **我想要** 在项目目录结构中组织所有任务输出
- **以便** 我可以查找和重用先前任务的工件
- **示例：** 所有研究报告保存到 `/reports/`，网页保存到 `/sites/`

**US-7: 上下文感知的后续任务**
- **作为** 用户
- **我想要** 发起基于先前项目文件构建的新任务
- **以便** 我可以迭代开发复杂的交付成果
- **示例：** "向您之前创建的着陆页添加联系表单"

**US-8: 多步骤自动化**
- **作为** 用户
- **我想要** 委托需要多个工具（浏览器 + 代码 + 文件）的任务
- **以便** 我可以自动化手动需要数小时的工作流
- **示例：** "抓取竞争对手定价，使用 Python 分析，生成比较图表"

## 6. 核心架构与模式

### 高层架构

**模块化单体方法：**
- 具有清晰模块边界的单一代码库
- 控制平面（API）与执行平面（工作器）分离
- 基于队列编排的异步任务执行
- 无状态 API 层，有状态工作器进程

**关键组件：**

```
┌─────────────┐
│   Frontend  │ (Next.js)
│   (Web UI)  │
└──────┬──────┘
       │ HTTP/WebSocket
┌──────▼──────────────────────────────────────┐
│         FastAPI Backend (Control Plane)      │
│  - Project API                               │
│  - Conversation API                          │
│  - Task API                                  │
│  - Artifact API                              │
│  - WebSocket/SSE event streaming             │
└──────┬──────────────────────────────────────┘
       │ Redis Queue
┌──────▼──────────────────────────────────────┐
│      Python Worker (Execution Plane)         │
│  - Agent Orchestrator                        │
│  - Tool System                               │
│  - Sandbox Manager                           │
│  - Model Router                              │
└──────┬──────────────────────────────────────┘
       │
┌──────▼──────┐  ┌──────────┐  ┌──────────┐
│   Docker    │  │ Postgres │  │  MinIO   │
│  Sandboxes  │  │ +pgvector│  │ (S3-like)│
└─────────────┘  └──────────┘  └──────────┘
```

### 目录结构

```
badgers-mvp/
├── frontend/                 # Next.js 应用
│   ├── src/
│   │   ├── app/             # App router 页面
│   │   ├── components/      # 可重用 UI 组件
│   │   ├── features/        # 功能模块
│   │   │   ├── projects/
│   │   │   ├── conversations/
│   │   │   ├── tasks/
│   │   │   └── artifacts/
│   │   ├── lib/             # 工具、API 客户端
│   │   └── hooks/           # 自定义 React hooks
│   └── package.json
│
├── backend/                  # FastAPI 应用
│   ├── app/
│   │   ├── main.py          # FastAPI 入口点
│   │   ├── config.py        # 配置管理
│   │   ├── database.py      # 数据库连接
│   │   ├── models/          # SQLAlchemy 模型
│   │   ├── schemas/         # Pydantic 模式
│   │   ├── routers/         # API 端点
│   │   │   ├── projects.py
│   │   │   ├── conversations.py
│   │   │   ├── tasks.py
│   │   │   └── artifacts.py
│   │   ├── services/        # 业务逻辑
│   │   └── dependencies.py  # FastAPI 依赖项
│   └── pyproject.toml
│
├── worker/                   # 任务执行工作器
│   ├── orchestrator/        # 代理编排
│   │   ├── agent.py         # 主代理循环
│   │   ├── planner.py       # 任务规划
│   │   └── executor.py      # 步骤执行
│   ├── tools/               # 工具实现
│   │   ├── base.py          # 工具接口
│   │   ├── browser.py       # 浏览器自动化
│   │   ├── file.py          # 文件操作
│   │   ├── python.py        # 代码执行
│   │   └── web.py           # Web 获取
│   ├── sandbox/             # 沙箱管理
│   │   ├── manager.py       # 生命周期管理
│   │   └── docker_backend.py
│   ├── models/              # 模型抽象
│   │   ├── base.py          # 统一接口
│   │   ├── openai_compat.py
│   │   └── anthropic.py
│   ├── rag/                 # RAG 系统
│   │   ├── indexer.py       # 文档索引
│   │   ├── retriever.py     # 相似性搜索
│   │   └── parsers/         # 文档解析器
│   ├── memory/              # 内存系统
│   │   ├── conversation.py
│   │   ├── project.py
│   │   └── working.py
│   └── skills/              # 技能模板
│       ├── research.py
│       ├── webpage.py
│       └── analysis.py
│
├── shared/                   # 共享工具
│   ├── schemas/             # 共享数据模型
│   └── utils/
│
└── docker/                   # Docker 配置
    ├── sandbox-base/        # 基础沙箱镜像
    └── docker-compose.yml
```

### 关键设计模式

**1. 任务-运行分离：**
- `Task` = 逻辑目标（例如，"研究特斯拉财报"）
- `Run` = 具有自己沙箱和日志的执行实例
- 实现重试而不重复任务定义

**2. 工具接口模式：**
```python
class Tool(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    async def execute(self, params: dict) -> ToolResult:
        pass
```

**3. 沙箱生命周期：**
- 创建 → 挂载工作目录 → 执行工具 → 捕获工件 → 销毁
- 每个运行获得隔离的文件系统和网络命名空间

**4. 事件流：**
- 工作器发出事件（step_started、tool_called、artifact_created）
- API 通过 WebSocket/SSE 将事件流式传输到前端
- 前端实时更新 UI

**5. 工件流：**
```
沙箱临时文件 → 工件（S3/MinIO）→ 项目目录（用户发起保存）
```

### 核心边界与资源模型

本节定义系统概念之间的关键边界，以防止实现过程中的架构混淆。

#### Conversation vs Task 边界

**Conversation（对话）** 是用户-系统对话的**交互容器**：
- 用户可以讨论想法、提问、澄清需求
- 多轮来回交流而不创建任务
- 显示任务结果并允许后续讨论
- 一个对话可以随时间产生多个任务

**Task（任务）** 是具有明确目标的**执行单元**：
- 仅在用户明确发起执行时创建（按钮点击、明确命令）
- 不是为每条消息创建任务
- 具有明确的开始/结束、成功/失败状态
- 产生具体工件

**创建流程：**
1. 用户在对话中发送消息（不创建任务）
2. 用户点击"执行"或说"开始任务" → 创建任务
3. 任务独立执行
4. 结果发布回对话
5. 用户可以讨论结果而不创建新任务

**API 分离：**
- `POST /conversations/{id}/messages` - 发送消息（不创建任务）
- `POST /tasks` - 明确创建任务（带 conversation_id 引用）

#### Task vs Run 边界

**Task（任务）** 代表**逻辑目标**（要完成什么）：
- 目标描述
- 技能模板选择
- 项目/对话关联
- 创建元数据

**Run（运行）** 代表**单次执行尝试**（如何执行）：
- 执行状态（pending/running/success/failed）
- 沙箱实例
- 执行日志和步骤
- 工具调用和结果
- 生成的工件
- 时间信息
- 错误详情

**资源归属规则：**

| 资源 | 归属于 | 原因 |
|------|--------|------|
| 目标、技能、模型配置 | Task | 定义要做什么 |
| 状态（running/failed） | Run | 每次执行都会变化 |
| 沙箱会话 | Run | 每次尝试一个沙箱 |
| 执行日志 | Run | 每次尝试不同 |
| 步骤记录 | Run | 执行特定 |
| 工具调用历史 | Run | 执行特定 |
| 工件 | Run | 由特定执行产生 |
| 开始/结束时间戳 | Run | 执行特定 |
| 错误消息 | Run | 执行特定 |

**重试行为：**
- 重试创建具有相同 Task 目标的**新 Run**
- 新 Run 获得新沙箱、干净日志
- 之前 Run 的工件和日志保持可访问
- Task 跟踪"current_run_id"用于活动执行

#### Artifact 三层模型

系统区分三种具有不同生命周期的文件类型：

**第一层：沙箱临时文件**
- **位置：** Docker 容器内的 `/sandbox/{run_id}/workspace/`
- **生命周期：** 执行期间创建，沙箱终止时销毁
- **目的：** 代理的工作文件（中间数据、临时脚本）
- **访问：** 仅在执行期间在沙箱内可访问
- **清理：** 运行完成后 N 小时删除（可配置，默认 2 小时）

**第二层：工件（Artifacts）**
- **位置：** MinIO/S3 对象存储（`s3://badgers-artifacts/{run_id}/{filename}`）
- **生命周期：** 任务完成时从沙箱提取，保留 30 天
- **目的：** 值得保留的交付成果（报告、截图、生成的代码）
- **访问：** 通过 API（`GET /artifacts/{artifact_id}/download`）
- **元数据：** 存储在数据库（artifact 表）中，包含 run_id、类型、大小、创建时间
- **清理：** 如果未保存到项目，30 天后自动删除

**第三层：项目文件**
- **位置：** 项目目录结构（数据库：project_node 表）
- **生命周期：** 永久（直到用户删除）
- **目的：** 正式项目资产，可跨任务重用
- **访问：** 通过项目文件 API，由 RAG 索引
- **创建：** 用户通过"保存到项目"操作明确保存工件

**流程示例：**
1. 代理在沙箱中写入 `/workspace/report.md`（第一层）
2. 任务完成，系统提取 `report.md` → 创建 Artifact（第二层）
3. 用户点击"保存到项目" → 复制到 `/reports/tesla-q4.md`（第三层）
4. 沙箱销毁，临时文件消失
5. 工件保留 30 天
6. 项目文件永久保留，可通过 RAG 用于未来任务

## 7. 工具/功能

### 工具系统设计

每个工具遵循统一接口，具有一致的参数结构和返回格式。所有工具执行都被记录，结果可在前端显示。

#### 浏览器工具

**目的：** 启用 Web 自动化、数据提取和截图捕获。

**操作：**

1. **browser.open**
   - 在无头浏览器中打开 URL
   - 返回：页面标题、URL、成功状态
   - 示例：`{"url": "https://example.com", "wait_for": "networkidle"}`

2. **browser.click**
   - 通过选择器点击元素
   - 返回：成功状态、元素文本
   - 示例：`{"selector": "button.submit", "wait_for_navigation": true}`

3. **browser.type**
   - 在输入字段中输入文本
   - 返回：成功状态
   - 示例：`{"selector": "input[name='search']", "text": "Tesla earnings"}`

4. **browser.extract**
   - 从页面提取结构化数据
   - 返回：提取的内容（文本、表格、链接）
   - 示例：`{"selector": "table.data", "format": "json"}`

5. **browser.screenshot**
   - 捕获页面截图
   - 返回：图像工件引用
   - 示例：`{"full_page": true, "format": "png"}`

**关键特性：**
- 基于 Playwright 的自动化
- 自动等待页面加载
- 元素可见性检查
- 截图工件保存到 S3

#### 文件工具

**目的：** 在沙箱工作空间内读取、写入和管理文件。

**范围：** 代理只能访问沙箱内的文件（`/workspace/` 目录）。项目文件通过 RAG 上下文只读访问。要将结果保存到项目，代理必须创建工件，用户通过"保存到项目"操作明确保存。

**操作：**

1. **file.list**
   - 列出沙箱目录中的文件
   - 返回：文件路径、大小、修改时间
   - 示例：`{"path": "/workspace", "recursive": true}`

2. **file.read**
   - 从沙箱读取文件内容
   - 返回：文件内容（文本或二进制的 base64）
   - 示例：`{"path": "/workspace/data.json"}`

3. **file.write**
   - 将内容写入沙箱中的文件
   - 返回：成功状态、文件路径
   - 示例：`{"path": "/workspace/report.md", "content": "# Report..."}`

**关键特性：**
- 沙箱文件系统隔离（无直接项目写入权限）
- 支持文本和二进制文件
- 沙箱内自动目录创建
- 安全的文件大小限制

#### Python 执行工具

**目的：** 执行 Python 代码进行数据处理、分析和计算。

**操作：**

1. **python.run**
   - 在沙箱中执行 Python 代码
   - 返回：stdout、stderr、执行时间
   - 示例：`{"code": "import pandas as pd\ndf = pd.read_csv('data.csv')\nprint(df.describe())"}`

**关键特性：**
- 隔离的 Python 环境
- 预装常用库（pandas、numpy、requests、beautifulsoup4）
- 超时保护（默认 30 秒）
- Stdout/stderr 捕获

#### Web 获取工具

**目的：** 在不使用完整浏览器自动化的情况下获取 Web 内容。

**操作：**

1. **web.fetch**
   - 通过 HTTP 获取 URL 内容
   - 返回：HTML/JSON 内容、状态码、标头
   - 示例：`{"url": "https://api.example.com/data", "method": "GET"}`

**关键特性：**
- 简单请求的快速浏览器替代方案
- 支持 GET/POST 方法
- 自定义标头和身份验证
- JSON 响应解析

#### 最终答案工具

**目的：** 发出任务完成信号并提交最终结果。

**操作：**

1. **final.answer**
   - 提交最终任务结果
   - 返回：任务完成状态
   - 示例：`{"answer": "Research complete. Report saved to /reports/tesla-q4.md", "artifacts": ["report-123", "chart-456"]}`

**关键特性：**
- 标记任务为完成
- 将工件链接到任务结果
- 提供面向用户的摘要

### 技能系统

技能是轻量级任务模板，为特定任务类型配置代理的行为。

**技能结构：**
```python
class Skill:
    name: str
    description: str
    system_prompt: str
    allowed_tools: List[str]
    output_format: str
    example_tasks: List[str]
```

**内置技能：**

1. **研究报告技能**
   - 系统提示："您是研究助手。搜索信息，提取关键事实，并生成带引用的结构化 markdown 报告。"
   - 允许的工具：browser.*、web.fetch、file.write、final.answer
   - 输出格式：带章节的 Markdown 报告（执行摘要、发现、来源）

2. **网页生成技能**
   - 系统提示："您是 Web 开发人员。遵循现代最佳实践生成干净、响应式的 HTML/CSS/JS 代码。"
   - 允许的工具：file.write、python.run（用于模板化）、final.answer
   - 输出格式：带嵌入式 CSS/JS 的 HTML 文件或单独文件

3. **文件分析技能**
   - 系统提示："您是数据分析师。读取文件，提取见解，并生成摘要报告。"
   - 允许的工具：file.read、python.run、file.write、final.answer
   - 输出格式：带关键发现和可视化的分析报告

## 8. 技术栈

### 后端

**核心框架：**
- **FastAPI 0.110+** - 具有自动 OpenAPI 文档的现代异步 Web 框架
- **Python 3.11+** - 类型提示、性能改进

**数据库：**
- **PostgreSQL 15+** - 主关系数据库
- **pgvector** - RAG 的向量相似性搜索
- **SQLAlchemy 2.0+** - 具有异步支持的 ORM
- **Alembic** - 数据库迁移

**任务队列：**
- **Redis 7+** - 消息代理和缓存
- **Celery** 或 **ARQ** - 异步任务队列（ARQ 更适合简单的 async/await）

**对象存储：**
- **MinIO** - S3 兼容的工件对象存储
- **boto3** - S3 客户端库

**沙箱：**
- **Docker Engine** - 容器运行时
- **docker-py** - Python Docker SDK

**浏览器自动化：**
- **Playwright** - 无头浏览器自动化

**AI/ML：**
- **OpenAI Python SDK** - OpenAI 兼容 API 客户端
- **Anthropic Python SDK** - Claude API 客户端
- **sentence-transformers** - 嵌入生成（可选，用于本地嵌入）

**工具：**
- **Pydantic 2.0+** - 数据验证和序列化
- **structlog** - 结构化日志记录
- **httpx** - 异步 HTTP 客户端
- **python-multipart** - 文件上传支持
- **python-jose** - JWT 处理（未来身份验证）

### 前端

**核心框架：**
- **Next.js 14+** - 具有 App Router 的 React 框架
- **React 18+** - UI 库
- **TypeScript 5+** - 类型安全

**状态管理：**
- **TanStack Query (React Query) 5+** - 服务器状态管理
- **Zustand** - 客户端状态管理（轻量级）

**UI 组件：**
- **Tailwind CSS 3+** - 实用优先的 CSS
- **shadcn/ui** - 可访问的组件库
- **Radix UI** - 无头 UI 原语
- **Lucide React** - 图标库

**实时：**
- **Socket.IO Client** 或 **原生 WebSocket** - 实时任务更新

**工具：**
- **Zod** - 模式验证
- **date-fns** - 日期操作
- **react-hook-form** - 表单处理

### 基础设施

**容器化：**
- **Docker** - 应用容器
- **Docker Compose** - 本地开发编排

**反向代理：**
- **Nginx** - API 网关和静态文件服务

**监控（MVP 可选）：**
- **Prometheus** - 指标收集
- **Grafana** - 指标可视化

### 开发工具

- **uv** - 快速 Python 包管理器
- **pytest** - Python 测试
- **Vitest** - 前端单元测试
- **Playwright** - E2E 测试
- **ESLint** - JavaScript 代码检查
- **Prettier** - 代码格式化
- **Ruff** - Python 代码检查和格式化

## 9. 安全与配置

### 身份验证与授权

**MVP 方法：**
- **无身份验证** - 单用户本地部署
- **未来：** 基于 JWT 的身份验证与用户账户

**沙箱安全：**
- 每个任务运行在隔离的 Docker 容器中执行
- 通过 Docker 网络控制网络访问
- 使用挂载卷的文件系统隔离
- 资源限制（CPU、内存、磁盘）
- 任务完成后自动清理

### 配置管理

**环境变量：**
```bash
# 数据库
DATABASE_URL=postgresql://user:pass@localhost:5432/badgers
POSTGRES_USER=badgers
POSTGRES_PASSWORD=<secure-password>

# Redis
REDIS_URL=redis://localhost:6379/0

# 对象存储
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=<access-key>
S3_SECRET_KEY=<secret-key>
S3_BUCKET=badgers-artifacts

# 模型提供商
OPENAI_API_KEY=<key>
OPENAI_BASE_URL=https://api.openai.com/v1  # 或兼容端点
ANTHROPIC_API_KEY=<key>

# 默认模型
DEFAULT_MAIN_MODEL=gpt-4-turbo-preview
DEFAULT_EMBEDDING_MODEL=text-embedding-3-small

# 沙箱
DOCKER_HOST=unix:///var/run/docker.sock
SANDBOX_TIMEOUT=300  # 秒
SANDBOX_MEMORY_LIMIT=2g
SANDBOX_CPU_LIMIT=2.0

# 应用
LOG_LEVEL=INFO
ENVIRONMENT=development
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
```

**配置文件：**
- `backend/config.py` - 类型安全配置的 Pydantic Settings
- `.env.example` - 环境变量模板
- `docker-compose.yml` - 服务编排

### 安全范围

**✅ 范围内：**
- 每个任务运行的沙箱隔离
- 沙箱资源限制
- 网络访问控制
- 安全凭证存储（环境变量）
- 所有 API 端点的输入验证
- SQL 注入防护（SQLAlchemy ORM）

**❌ 范围外（MVP）：**
- 用户身份验证和授权
- API 速率限制
- 审计日志
- 静态加密
- RBAC（基于角色的访问控制）
- OAuth/SSO 集成

### 部署考虑

**MVP 部署：**
- Docker Compose 用于本地/单服务器部署
- 所有服务在单个主机上
- SQLite 或 PostgreSQL 用于数据库
- 本地文件系统或 MinIO 用于对象存储

**生产就绪（未来）：**
- Kubernetes 编排
- 托管数据库（RDS、Cloud SQL）
- 托管对象存储（S3、GCS）
- 负载均衡
- 自动扩展工作器
- 分布式追踪

## 10. API 规范

### 基础 URL
```
http://localhost:8000/api/v1
```

### 身份验证
MVP：无需身份验证。未来：Authorization 标头中的 Bearer token。

### 核心端点

#### 项目

**POST /projects**
- 创建新项目
- 请求：
```json
{
  "name": "My Research Project",
  "description": "Q4 2025 market analysis"
}
```
- 响应：201 Created
```json
{
  "id": "proj_abc123",
  "name": "My Research Project",
  "description": "Q4 2025 market analysis",
  "created_at": "2026-03-10T17:45:35Z",
  "updated_at": "2026-03-10T17:45:35Z"
}
```

**GET /projects/{project_id}**
- 获取项目详情
- 响应：200 OK（与 POST 响应结构相同）

**GET /projects/{project_id}/files**
- 列出项目文件和目录结构
- 响应：200 OK
```json
{
  "nodes": [
    {
      "id": "node_123",
      "name": "reports",
      "type": "directory",
      "path": "/reports",
      "parent_id": null
    },
    {
      "id": "node_124",
      "name": "tesla-q4.md",
      "type": "file",
      "path": "/reports/tesla-q4.md",
      "size": 15420,
      "parent_id": "node_123",
      "created_at": "2026-03-10T18:00:00Z"
    }
  ]
}
```

**GET /projects/{project_id}/nodes/{node_id}/content**
- 通过节点 ID 下载文件内容
- 响应：200 OK 带文件内容

**GET /projects/{project_id}/files/download**
- 通过路径下载文件内容（替代方案）
- 查询参数：`?path=/reports/tesla-q4.md`
- 响应：200 OK 带文件内容

**POST /projects/{project_id}/files**
- 上传文件到项目
- 请求：multipart/form-data 带文件和路径
- 响应：201 Created

#### 对话

**POST /conversations**
- 创建新对话
- 请求：
```json
{
  "project_id": "proj_abc123",
  "title": "Research Tasks"
}
```
- 响应：201 Created
```json
{
  "id": "conv_xyz789",
  "project_id": "proj_abc123",
  "title": "Research Tasks",
  "created_at": "2026-03-10T17:45:35Z"
}
```

**GET /conversations/{conversation_id}**
- 获取对话详情和消息
- 响应：200 OK
```json
{
  "id": "conv_xyz789",
  "project_id": "proj_abc123",
  "title": "Research Tasks",
  "messages": [
    {
      "id": "msg_001",
      "role": "user",
      "content": "Research Tesla Q4 earnings",
      "created_at": "2026-03-10T17:46:00Z"
    },
    {
      "id": "msg_002",
      "role": "assistant",
      "content": "I'll research Tesla's Q4 earnings and create a report.",
      "created_at": "2026-03-10T17:46:05Z"
    }
  ]
}
```

**POST /conversations/{conversation_id}/messages**
- 向对话发送消息（不创建任务）
- 请求：
```json
{
  "content": "我想研究特斯拉 Q4 2025 财报",
  "role": "user"
}
```
- 响应：201 Created
```json
{
  "message_id": "msg_003",
  "content": "我想研究特斯拉 Q4 2025 财报",
  "role": "user",
  "created_at": "2026-03-10T17:46:10Z"
}
```

**注意：** 要创建任务，请单独使用 `POST /tasks` 端点。这保持了对话（交互）和任务（执行）之间的清晰分离。

#### 任务

**POST /tasks**
- 手动创建任务
- 请求：
```json
{
  "conversation_id": "conv_xyz789",
  "project_id": "proj_abc123",
  "goal": "Research Tesla Q4 2025 earnings",
  "skill": "research_report",
  "model": "gpt-4-turbo-preview"
}
```
- 响应：201 Created
```json
{
  "id": "task_456",
  "conversation_id": "conv_xyz789",
  "project_id": "proj_abc123",
  "goal": "Research Tesla Q4 2025 earnings",
  "status": "pending",
  "skill": "research_report",
  "created_at": "2026-03-10T17:46:10Z"
}
```

**GET /tasks/{task_id}**
- 获取任务详情（仅任务级属性）
- 响应：200 OK
```json
{
  "id": "task_456",
  "conversation_id": "conv_xyz789",
  "project_id": "proj_abc123",
  "goal": "Research Tesla Q4 2025 earnings",
  "skill": "research_report",
  "model": "gpt-4-turbo-preview",
  "current_run_id": "run_789",
  "created_at": "2026-03-10T17:46:10Z"
}
```

**注意：** 要获取执行状态、时间戳或日志，请查询运行：`GET /runs/{run_id}`

**GET /tasks/{task_id}/runs**
- 列出任务的所有运行
- 响应：200 OK
```json
{
  "runs": [
    {
      "id": "run_789",
      "task_id": "task_456",
      "status": "running",
      "started_at": "2026-03-10T17:46:15Z",
      "sandbox_id": "sandbox_abc"
    }
  ]
}
```

**POST /tasks/{task_id}/retry**
- 为任务创建新运行
- 响应：201 Created
```json
{
  "run_id": "run_790",
  "status": "pending"
}
```

#### 运行

**GET /runs/{run_id}**
- 获取运行详情
- 响应：200 OK
```json
{
  "id": "run_789",
  "task_id": "task_456",
  "status": "running",
  "started_at": "2026-03-10T17:46:15Z",
  "sandbox_id": "sandbox_abc",
  "step_count": 3
}
```

**POST /runs/{run_id}/cancel**
- 取消特定运行
- 响应：200 OK
```json
{
  "run_id": "run_789",
  "status": "cancelled",
  "cancelled_at": "2026-03-10T17:50:00Z"
}
```

**GET /runs/{run_id}/logs**
- 获取特定运行的执行日志
- 响应：200 OK 带日志条目

#### 运行事件（WebSocket）

**WS /runs/{run_id}/events**
- 特定运行的实时执行事件
- 事件：
```json
{
  "type": "run_started",
  "run_id": "run_789",
  "timestamp": "2026-03-10T17:46:15Z"
}

{
  "type": "step_started",
  "step_number": 1,
  "description": "Searching for Tesla Q4 earnings information",
  "timestamp": "2026-03-10T17:46:16Z"
}

{
  "type": "tool_called",
  "tool": "browser.open",
  "params": {"url": "https://ir.tesla.com"},
  "timestamp": "2026-03-10T17:46:17Z"
}

{
  "type": "tool_result",
  "tool": "browser.open",
  "result": {"success": true, "title": "Tesla Investor Relations"},
  "timestamp": "2026-03-10T17:46:20Z"
}

{
  "type": "artifact_created",
  "artifact_id": "art_123",
  "name": "tesla-q4-report.md",
  "type": "markdown",
  "timestamp": "2026-03-10T17:50:00Z"
}

{
  "type": "run_completed",
  "run_id": "run_789",
  "status": "success",
  "result": "Report generated successfully",
  "artifacts": ["art_123"],
  "timestamp": "2026-03-10T17:50:05Z"
}
```

#### 工件

**GET /artifacts/{artifact_id}**
- 获取工件元数据
- 响应：200 OK
```json
{
  "id": "art_123",
  "task_run_id": "run_789",
  "name": "tesla-q4-report.md",
  "type": "markdown",
  "size": 15420,
  "url": "/api/v1/artifacts/art_123/download",
  "created_at": "2026-03-10T17:50:00Z"
}
```

**GET /artifacts/{artifact_id}/download**
- 下载工件内容
- 响应：200 OK 带文件内容

**POST /artifacts/{artifact_id}/save-to-project**
- 将工件保存到项目目录
- 请求：
```json
{
  "project_id": "proj_abc123",
  "path": "/reports/tesla-q4.md"
}
```
- 响应：201 Created

## 11. 成功标准

### MVP 成功定义

如果 MVP **验证了核心产品假设**，则 MVP 成功：用户可以将复杂的多步骤任务委托给 AI 代理，该代理在隔离环境中自主执行任务，产生持久保存在项目目录中的有价值工件。

成功通过**假设验证**来衡量，而不是功能完整性。

### 需要验证的核心假设

#### 假设 1：用户理解并采用任务委托模型

**假设：** 用户可以理解"将任务委托给代理"而不是"与 AI 聊天"的概念，并将相应地使用系统。

**验证方法：**
- 观察 5 个测试用户尝试创建和执行他们的第一个任务
- 测量首次成功创建任务的时间
- 要求用户解释对话和任务之间的区别

**成功标准：**
- ✅ 5 个用户中有 4 个在 5 分钟内成功创建任务
- ✅ 5 个用户中有 4 个可以表达"对话用于讨论，任务用于执行"
- ✅ 用户自然点击"创建任务"按钮，而不是期望每条消息都执行

**失败信号：**
- 用户对何时创建任务感到困惑
- 用户期望每条消息都立即执行
- 用户不理解为什么对话和任务是分开的

#### 假设 2：代理可以可靠地完成典型任务

**假设：** 具有可用工具的单代理执行循环可以成功完成常见任务类型（研究、网页生成、文件分析），成功率至少为 80%。

**验证方法：**
- 跨三个类别执行 30 个任务（每个 10 个）：
  - 研究报告（例如，"研究公司 X 并创建报告"）
  - 网页生成（例如，"创建带定价的落地页"）
  - 文件分析（例如，"分析此 CSV 并总结发现"）
- 跟踪成功率、失败原因、执行时间

**成功标准：**
- ✅ 总体成功率 ≥ 80%（30 个中 24+ 个成功）
- ✅ 研究任务平均执行时间 < 5 分钟
- ✅ 网页生成平均执行时间 < 3 分钟
- ✅ 失败是由于外部因素（网络、API 限制），而不是系统错误

**失败信号：**
- 成功率 < 70%
- 代理陷入循环或没有进展
- 工具执行频繁失败
- 沙箱崩溃或超时很常见

#### 假设 3：用户可以理解和信任执行过程

**假设：** 实时逐步更新提供足够的透明度，让用户理解代理正在做什么并信任该过程。

**验证方法：**
- 向 5 个用户展示带有实时更新的运行任务
- 任务完成后，要求用户描述代理做了什么
- 测量用户对结果的信心

**成功标准：**
- ✅ 5 个用户中有 4 个可以准确描述代理采取的主要步骤
- ✅ 5 个用户中有 4 个对结果表示信心（"我信任这个输出"）
- ✅ 用户可以识别代理何时卡住或出错
- ✅ 用户理解工具调用（例如，"代理打开浏览器并搜索"）

**失败信号：**
- 用户说"我不知道它在做什么"
- 用户无法解释执行过程
- 用户不信任结果，需要手动验证
- 实时更新过于技术化或过于模糊

#### 假设 4：工件有价值并被保存到项目

**假设：** 任务产生的工件足够有价值，用户会将它们保存到项目目录并在未来工作中引用它们。

**验证方法：**
- 跟踪 30 个已完成任务的工件保存率
- 跟踪保存的项目文件在后续任务中被引用的频率
- 询问用户工件是否符合他们的期望

**成功标准：**
- ✅ 工件保存率 ≥ 60%（用户保存 30 个中的 18+ 个工件）
- ✅ 保存的项目文件在 ≥ 40% 的后续任务中被引用
- ✅ 5 个用户中有 4 个说工件"有用"或"非常有用"
- ✅ 用户将工件组织到项目目录中（不只是转储到根目录）

**失败信号：**
- 保存率 < 40%（用户不认为工件有价值）
- 保存的文件再也不会被引用
- 用户手动重新创建内容而不是使用工件
- 用户抱怨工件质量或格式

### 最小可行功能集

要验证上述假设，MVP 必须包括：

**必要功能：**
- ✅ 项目创建和目录结构
- ✅ 对话界面（与任务执行分离）
- ✅ 明确的任务创建流程
- ✅ 每个任务运行的隔离沙箱
- ✅ 实时执行更新（逐步）
- ✅ 工具系统（浏览器、文件、python、web）
- ✅ 工件生成和下载
- ✅ 将工件保存到项目目录
- ✅ 任务重试（创建新运行）
- ✅ 项目文件的基本 RAG

**MVP 可接受的限制：**
- 仅单代理（无多代理）
- 有限的技能模板（3 种类型）
- 基本错误处理（无自动恢复）
- 简单内存（无复杂知识图谱）
- 手动任务创建（无自动任务检测）

## 12. 实施阶段

### 阶段 1：基础（第 1-2 周）

**目标：** 建立核心基础设施和基本任务执行循环。

**交付成果：**
- ✅ 数据库模式和模型（project、conversation、message、task、task_run、sandbox_session、artifact）
- ✅ 具有项目和对话基本 CRUD 端点的 FastAPI 后端
- ✅ 具有项目创建和对话 UI 的 Next.js 前端
- ✅ 具有生命周期管理的 Docker 沙箱管理器
- ✅ 具有计划-执行循环的基本代理编排器
- ✅ 文件工具实现（列出、读取、写入）
- ✅ Redis 任务队列设置
- ✅ 从队列消费任务的工作器进程

**验证：**
- 可以通过 API 创建项目
- 可以通过 API 创建对话
- 可以创建生成沙箱的任务
- 代理可以在沙箱中执行简单的文件操作
- 任务完成后沙箱清理

### 阶段 2：工具系统与实时更新（第 3-4 周）

**目标：** 实现完整的工具套件和实时任务监控。

**交付成果：**
- ✅ 使用 Playwright 的浏览器工具（打开、点击、输入、提取、截图）
- ✅ 具有常用库的 Python 执行工具
- ✅ 用于 HTTP 请求的 Web 获取工具
- ✅ 用于任务完成的最终答案工具
- ✅ 用于任务事件的 WebSocket/SSE 端点
- ✅ 前端实时任务状态显示
- ✅ 工具调用日志记录和可视化
- ✅ MinIO/S3 中的工件存储

**验证：**
- 代理可以打开浏览器、导航和提取数据
- 代理可以执行 Python 代码并捕获输出
- 前端显示实时步骤更新
- 用户可以查看工具调用参数和结果
- 截图和文件保存为工件

### 阶段 3：RAG、内存与技能（第 5-6 周）

**目标：** 添加上下文感知和任务模板。

**交付成果：**
- ✅ PDF、Markdown、TXT 的文档解析器
- ✅ pgvector 集成用于相似性搜索
- ✅ RAG 索引器和检索器
- ✅ 文件上传到项目
- ✅ 对话摘要生成
- ✅ 项目内存存储和检索
- ✅ 任务工作内存
- ✅ 三个技能模板（研究、网页、分析）
- ✅ 任务创建中的技能选择

**验证：**
- 用户可以上传 PDF 并询问有关它的问题
- 代理从项目文件中检索相关上下文
- N 条消息后生成对话摘要
- 技能适当地自定义代理行为
- 后续任务引用先前的工件

### 阶段 4：模型抽象与完善（第 7-8 周）

**目标：** 多模型支持和生产就绪。

**交付成果：**
- ✅ 统一模型接口抽象
- ✅ OpenAI 兼容提供商实现
- ✅ Anthropic 原生提供商实现
- ✅ 嵌入提供商抽象
- ✅ 模型配置和路由
- ✅ 任务重试功能
- ✅ 任务取消
- ✅ 错误处理和用户友好消息
- ✅ 具有保存工件流程的项目文件浏览器
- ✅ 用于轻松部署的 Docker Compose 设置
- ✅ 文档和设置指南

**验证：**
- 可以在 OpenAI 和 Anthropic 模型之间切换
- 可以通过环境变量配置默认模型
- 任务重试使用新沙箱创建新运行
- 用户可以取消长时间运行的任务
- 完整的端到端工作流顺利运行
- Docker Compose 启动整个堆栈

## 13. 未来考虑

### MVP 后增强

**多代理协作：**
- 多个代理的并行任务执行
- 代理间通信协议
- 任务委托和协调
- 专业代理角色（研究员、编码员、分析师）

**团队功能：**
- 用户身份验证和授权
- 项目共享和权限
- 团队工作区
- 活动源和通知
- 对任务和工件的评论

**高级内存：**
- 基于图的知识表示
- 跨项目内存共享
- 自动事实提取和链接
- 内存衰减和相关性评分

**增强的 RAG：**
- 多模态文档理解（图像、表格、图表）
- 语义分块策略
- 混合搜索（关键字 + 向量）
- 引用跟踪和来源验证

**平台功能：**
- 自定义工具的插件市场
- MCP（模型上下文协议）深度集成
- Webhook 集成（Slack、GitHub 等）
- 计划/定期任务
- 任务模板和工作流

**部署与托管：**
- 一键网站部署
- 自定义域支持
- CDN 集成
- 工件的预览环境
- 项目文件的版本控制

### 集成机会

**开发工具：**
- GitHub 集成（创建 PR、问题）
- GitLab、Bitbucket 支持
- Jira/Linear 任务同步
- VS Code 扩展

**通信：**
- 用于任务启动的 Slack 机器人
- Discord 集成
- 电子邮件通知
- 任务完成的短信提醒

**数据源：**
- Google Drive、Dropbox 文件同步
- Notion、Confluence 知识库
- 数据库连接器（MySQL、MongoDB）
- API 集成（REST、GraphQL）

**AI/ML 服务：**
- 图像生成（DALL-E、Midjourney）
- 语音转文本用于语音任务
- 视频处理能力
- 自定义模型微调

## 14. 风险与缓解措施

### 风险 1：沙箱逃逸或安全漏洞

**影响：** 高 - 可能危及主机系统或泄露敏感数据

**缓解措施：**
- 使用具有严格安全配置文件的 Docker（无特权模式）
- 实施资源限制（CPU、内存、磁盘、网络）
- 定期对沙箱配置进行安全审计
- 使用基于白名单的出口规则进行网络隔离
- 超时后自动终止沙箱
- 监控沙箱行为异常

### 风险 2：模型 API 成本失控

**影响：** 中 - 长时间运行或低效任务导致意外成本

**缓解措施：**
- 实施每个任务的 token 限制
- 在 UI 中跟踪并显示估计成本
- 设置云提供商的计费警报
- 在适当的地方缓存常见响应
- 优化提示以减少 token 使用
- 在任务执行前提供成本估算

### 风险 3：代理陷入无限循环

**影响：** 中 - 浪费资源并提供糟糕的用户体验

**缓解措施：**
- 任务执行的硬超时（例如，10 分钟）
- 每个任务的最大步骤数（例如，50 步）
- 检测具有相同参数的重复工具调用
- 为失败的工具实施断路器
- 允许用户随时取消任务
- 记录循环检测事件以进行调试

### 风险 4：任务成功率低破坏用户信任

**影响：** 高 - 如果任务经常失败，用户会放弃产品

**缓解措施：**
- 从明确定义的技能模板开始
- 向用户提供清晰的任务目标指南
- 在工具中实施强大的错误处理
- 显示详细的错误消息和恢复建议
- 启用使用修改参数轻松重试任务
- 收集失败分析以改进代理提示
- 对代理能力设定现实期望

### 风险 5：工件存储成本无限增长

**影响：** 中 - 随着用户生成工件，存储成本增加

**缓解措施：**
- 实施工件保留策略（例如，未保存的 30 天）
- 尽可能压缩工件
- 去重相同的工件
- 为工件清理提供用户控制
- 将旧工件归档到更便宜的存储层
- 为每个项目设置存储配额

## 15. 附录

### 相关文档

- **原始需求：** `docs/badgers-mvp-requirements.md` - 详细的中文需求文档
- **架构图：** 将在阶段 1 创建
- **API 文档：** 通过 FastAPI OpenAPI 在 `/docs` 自动生成
- **用户指南：** 将在阶段 4 创建

### 关键依赖

**核心基础设施：**
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Python Web 框架
- [Next.js](https://nextjs.org/) - 具有 App Router 的 React 框架
- [PostgreSQL](https://www.postgresql.org/) - 关系数据库
- [pgvector](https://github.com/pgvector/pgvector) - 向量相似性搜索
- [Redis](https://redis.io/) - 任务队列和缓存
- [Docker](https://www.docker.com/) - 容器运行时

**AI/ML：**
- [OpenAI API](https://platform.openai.com/docs/api-reference) - LLM 提供商
- [Anthropic API](https://docs.anthropic.com/) - Claude 模型
- [Playwright](https://playwright.dev/) - 浏览器自动化

**存储：**
- [MinIO](https://min.io/) - S3 兼容对象存储
- [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) - AWS SDK for Python

### 仓库结构

```
badgers-mvp/
├── README.md                 # 项目概述和设置
├── docker-compose.yml        # 本地开发堆栈
├── .env.example              # 环境变量模板
├── docs/                     # 文档
│   ├── badgers-mvp-requirements.md
│   ├── architecture.md
│   └── api.md
├── frontend/                 # Next.js 应用
├── backend/                  # FastAPI 应用
├── worker/                   # 任务执行工作器
├── shared/                   # 共享工具
└── docker/                   # Docker 配置
```

### 数据模型摘要

**核心实体：**
1. `project` - 用于组织任务和文件的工作区
2. `project_node` - 项目树中的文件/目录
3. `conversation` - 用于任务启动的聊天界面
4. `message` - 单个聊天消息
5. `task` - 逻辑任务定义
6. `task_run` - 任务的执行实例
7. `sandbox_session` - 隔离的执行环境
8. `artifact` - 生成的文件或输出
9. `project_memory` - 项目级事实和上下文
10. `conversation_summary` - 对话历史摘要
11. `document_chunk` - RAG 索引内容
12. `model_provider` - 模型 API 配置
13. `model_profile` - 模型能力和设置

**关键关系：**
- `conversation` → 多个 `task`
- `project` → 多个 `task`
- `task` → 多个 `task_run`
- `task_run` → 一个 `sandbox_session`
- `task_run` → 多个 `artifact`
- `project` → 多个 `project_node`
- `project` → 多个 `document_chunk`

### 术语表

- **工件（Artifact）：** 任务执行期间生成的文件或输出（报告、截图、代码文件）
- **对话（Conversation）：** 用户与系统交互并发起任务的聊天界面
- **项目（Project）：** 包含文件、任务和上下文的长期工作区
- **运行（Run）：** 具有自己沙箱的任务的单个执行实例
- **沙箱（Sandbox）：** 任务工具执行的隔离 Docker 容器
- **技能（Skill）：** 具有预定义提示、工具和输出格式的任务模板
- **任务（Task）：** 由代理执行的面向目标的工作单元
- **工具（Tool）：** 代理可以使用的能力（浏览器、文件操作、代码执行）
- **RAG：** 检索增强生成 - 从文档中检索相关上下文
- **工作内存（Working Memory）：** 任务执行期间维护的临时上下文

---

**文档版本：** 1.0
**最后更新：** 2026-03-10
**状态：** 审查草案
