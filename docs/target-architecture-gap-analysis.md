# Badgers MVP 目标架构与当前实现差距分析

## 1. 文档说明

本文用于配合 `docs/current-system-architecture.md` 阅读。

- `current-system-architecture.md`：描述当前代码已经实现了什么
- 本文：描述目标架构应该是什么，以及当前代码距离目标架构还差什么
- `architecture-execution-task-list.md`：基于本文整理出的可执行任务清单

本文的目标基线来源于：

- `.claude/PRD.md`
- 当前仓库中的模块边界与已有代码

本文不会把 PRD 直接当成“已经实现”，而是只把它当成 **目标架构基线**。

---

## 2. 目标架构基线

按 PRD 和当前代码意图，系统目标架构应当是下面这条完整主链：

```text
用户
  -> Frontend
  -> Backend
  -> Conversation（讨论）
  -> Task（明确创建）
  -> TaskRun（一次执行）
  -> Queue / 调度层
  -> Worker
  -> Sandbox
  -> Tool execution
  -> Artifact
  -> Run events
  -> Frontend 实时展示
  -> 用户保存结果到 Project
```

在这个目标架构里，最关键的边界是：

1. **Conversation 与 Task 分离**
   - Conversation 负责讨论
   - Task 负责执行目标

2. **Task 与 TaskRun 分离**
   - Task 负责逻辑定义
   - TaskRun 负责一次执行实例

3. **Artifact 与 Project 文件分离**
   - Artifact 是执行产物
   - Project 文件是用户显式保存后的长期文件

4. **Worker 与 Backend 分离**
   - Backend 是控制平面
   - Worker 是执行平面

5. **Sandbox 隔离工具执行**
   - 工具应尽可能在沙箱中运行，而不是直接在 worker 宿主环境运行

---

## 3. 目标架构的模块视图

## 3.1 Frontend 目标

目标前端应当覆盖：

- 项目列表与项目详情
- 对话页
- 任务创建流
- Run 详情页
- 实时执行时间线
- Artifact 预览/下载/保存到项目
- 项目文件浏览器

## 3.2 Backend 目标

目标后端应当承担：

- 资源生命周期管理
- 任务与运行状态写入
- 明确的 Task / Run API 边界
- 文件与 Artifact 存储协调
- WebSocket / SSE 事件中转
- RAG 与 Memory 的 API 边界

## 3.3 Worker 目标

目标 worker 应当承担：

- 消费待执行任务
- 创建和销毁 sandbox
- 运行 agent 主循环
- 调度模型调用和工具调用
- 产出 Artifact
- 广播执行事件

## 3.4 Infrastructure 目标

目标基础设施应当支持：

- PostgreSQL
- MinIO / S3
- Docker sandbox
- Redis 或其他任务队列
- 一键启动开发环境

---

## 4. 当前实现与目标架构的差距总览

| 模块 | 目标状态 | 当前状态 | 差距级别 |
|---|---|---|---|
| Frontend 页面覆盖 | 覆盖 Project/Conversation/Task/Run/Artifact | 当前只有 `/projects` 真正落地 | 高 |
| Task 调度 | API 创建 Run 后进入队列 | 当前是 worker 轮询数据库 | 中 |
| Worker 主链闭环 | 模型、工具、技能接口一致 | 当前存在模型双轨和工具双轨 | 高 |
| 实时事件 | Worker 广播运行步骤、工具调用、Artifact 事件 | 当前仅 `cancel_run` 会广播 | 高 |
| RAG 接入 | 上传文件自动索引，搜索 API 可用 | 当前 index/search API 是 stub | 高 |
| Artifact 生命周期 | 运行产出自动入 Artifact，支持保存到项目 | 当前仅手动上传 Artifact，缺少 save-to-project | 高 |
| Sandbox 隔离 | 工具主要在 sandbox 内执行 | 当前仅 PythonTool 明确在 sandbox 内执行 | 高 |
| Docker Compose | 一键起全栈 | 当前只起基础设施 | 中 |
| 配置一致性 | env 命名统一 | 当前 `minio_*` 与 `S3_*` 并存 | 中 |

---

## 5. 模块级差距分析

## 5.1 Frontend 差距

### 当前已具备

- React Query 基础设施
- 项目列表页
- 项目创建表单
- 任务运行查看组件
- 文件上传/文件列表组件

### 距离目标还差

1. **项目详情页缺失**
   - `ProjectCard` 已跳转 `/projects/{id}`
   - 但该路由不存在

2. **对话视图缺失**
   - 后端已有 `Conversation` / `Message` API
   - 前端没有页面和数据流

3. **任务创建视图缺失**
   - 前端没有真正的 task creation flow
   - 也没有 skill/model 选择界面

4. **Run 页面未挂载**
   - `TaskRunViewer` 存在
   - 但没有页面使用它

5. **Artifact 与 Memory 页面缺失**
   - API 已有一部分
   - 但前端没有任何消费界面

### 影响

- 当前前端只能验证“项目管理”这一小段业务
- 无法从 UI 验证完整的 AI 任务执行闭环

---

## 5.2 Backend 差距

### 当前已具备

- 主要资源的 CRUD API
- Run 查询与取消
- Artifact 上传/下载/删除
- Memory 摘要与向量写入
- RAG chunk 列表和删除

### 距离目标还差

1. **Task.current_run_id 未维护**
   - 目标上 Task 应该能指向当前活跃 Run
   - 当前创建 Run 时未更新这个字段

2. **缺少 Retry API**
   - PRD 目标中有 retry
   - 当前只有 `POST /tasks/{task_id}/runs`
   - 但没有显式 retry 入口

3. **Run 日志 API 不完整**
   - `TaskRun.logs` 字段存在
   - 但缺少成体系的日志写入与读取能力

4. **RAG 的 index/search 未接入实现**
   - `backend/app/routers/rag.py` 仍是 stub

5. **Artifact 缺少 save-to-project**
   - 目标设计里 Artifact 与项目文件之间有显式流转
   - 当前没有这条 API

6. **事件流只做了连接层，没有执行层数据源**
   - `event_broadcaster.py` 已有
   - 但没有真实执行过程去持续推送事件

### 影响

- 后端资源模型存在，但很多“状态演进”逻辑还未落地

---

## 5.3 Worker 差距

这是当前距离目标架构最远的一层。

### 当前已具备

- 主循环
- 数据库轮询
- sandbox 创建/销毁
- 技能加载
- Agent 结构
- 模型层、工具层、sandbox 层、RAG 层的基础模块

### 距离目标还差

1. **模型接口未统一**
   - `factory.py` 返回的是 `generate/stream` 风格 provider
   - `Agent` 依赖的是 `chat_completion/tool_calls` 风格 provider

2. **工具接口未统一**
   - `Agent` 期望 `tools.tool_base.Tool`
   - `get_all_tools()` 返回 `BaseTool` 风格实现

3. **文件工具未注册到默认工具集**
   - `worker/tools/file.py` 存在
   - 但 `get_all_tools()` 没有把它们加进去

4. **缺少 final answer / completion tool**
   - 目标架构中需要明确任务完成出口
   - 当前没有单独的 final answer tool

5. **缺少 Artifact 自动产出链**
   - 工具执行后没有自动把成果提取为 Artifact

6. **缺少事件广播**
   - Worker 没有把 step / tool / result / artifact / completed 事件发给 backend

7. **缺少 RAG / Memory 在执行主链中的整合**
   - 当前 worker 主循环没有真正注入：
     - 项目上下文检索结果
     - conversation summary
     - project memories

### 影响

- 当前 worker 具备“框架外观”，但还不是一个可靠可跑通的执行平面

---

## 5.4 Tool 层差距

### 目标状态

工具层应当：

- 使用统一的 Tool 协议
- 明确哪些工具在 sandbox 中执行
- 明确哪些工具会产出 Artifact
- 能稳定返回可序列化结果

### 当前差距

1. BrowserTool 和 WebFetchTool 在 worker 宿主进程执行
2. 只有 PythonTool 明确借助 sandbox 执行
3. 文件工具存在但未纳入主链
4. 工具结果还没有统一的 Artifact 抽取逻辑

### 影响

- 当前“隔离执行”的目标只实现了一部分

---

## 5.5 RAG 与 Memory 差距

### 当前 Memory 层

相对接近目标：

- 能生成 conversation summary
- 能生成 project memory embedding
- 能做 project memory semantic search

### 当前 RAG 层

明显落后于目标：

1. 上传文件不会自动索引
2. 公共 API 只有壳，没有真正接到 `DocumentIndexer` / `DocumentRetriever`
3. backend 与 worker 下各有一套 RAG 实现，边界未整理

### 影响

- Memory 更像“已接入的增强能力”
- RAG 更像“已放入仓库但尚未成为系统能力”

---

## 5.6 Infrastructure 差距

### 当前已具备

- PostgreSQL
- Redis
- MinIO
- Docker sandbox 基础镜像目录

### 距离目标还差

1. **docker-compose 不起 backend / worker / frontend**
2. **Redis 未接入主执行流**
3. **环境变量命名不统一**
4. **一键开发环境仍然依赖手动操作**

### 影响

- 当前基础设施更像“依赖准备完成”
- 不是“全栈一键运行完成”

---

## 6. 当前设计中应该保留的部分

虽然存在差距，但下面这些结构建议保留，不应推倒重来。

## 6.1 保留 Task / TaskRun 分层

这是当前最有价值的设计之一，应继续沿用。

## 6.2 保留 Worker 独立进程

执行平面与控制平面分离是正确方向，后续只需要把队列和事件接好。

## 6.3 保留技能 Markdown 化

技能定义与 agent 代码解耦，扩展成本低。

## 6.4 保留独立 Sandbox 模块

`SandboxManager` + `DockerBackend` 的分层合理，应继续深化，而不是把 Docker 调用重新散到业务代码里。

## 6.5 保留 Artifact / ProjectNode 分层

即使当前 save-to-project 未实现，这个分层本身仍是对的。

---

## 7. 从当前实现走向目标架构的推荐改造顺序

如果按最低风险、最高收益排序，建议这样推进。

## 第 1 步：统一 worker 的模型协议

先解决：

- `factory.py`
- `Agent`
- `openai_provider.py`
- `anthropic_provider.py`
- `openai_compat.py`
- `anthropic_native.py`

目标：

- 只保留一套 `chat_completion + tool_calls` 协议
- 让 `Agent` 与 provider 真正可接通

## 第 2 步：统一 worker 的工具协议

再解决：

- `BaseTool`
- `Tool`
- `get_all_tools()`
- `BrowserTool`
- `WebFetchTool`
- `PythonTool`
- `File*Tool`

目标：

- 只保留一套工具接口
- 把文件工具纳入默认工具集

## 第 3 步：接通任务执行闭环

目标：

- `POST /tasks/{task_id}/runs` 后，worker 能稳定消费
- Run 能从 `pending -> running -> completed/failed`
- `Task.current_run_id` 正确维护

这里可以二选一：

1. 保持数据库轮询
2. 改成 Redis 队列

如果目标是先尽快闭环，建议先保留数据库轮询，不要先切 Redis。

## 第 4 步：补上执行事件流

目标：

- worker 每轮执行都推送：
  - run_started
  - step
  - tool_call
  - tool_result
  - artifact_created
  - run_completed / run_failed

这样前端已有的 `TaskRunViewer` 才真正有价值。

## 第 5 步：补上 Artifact 自动产出链

目标：

- 文件工具写出的结果能被识别为 Artifact
- 支持下载
- 支持 save-to-project

## 第 6 步：接通 RAG

目标：

- 项目文件上传后自动索引
- 搜索 API 真正可用
- worker 执行时能拿到项目相关上下文

## 第 7 步：补齐前端业务页面

最后再把 UI 补齐：

- 项目详情页
- 对话页
- 任务创建页
- Run 详情页
- Artifact 与文件管理页

---

## 8. 两条关键链路的“目标态”示意

## 8.1 目标任务执行链

```text
Frontend 创建 Task
  -> Backend 写入 Task
  -> Frontend 创建 Run
  -> Backend 写入 TaskRun 并标记 Task.current_run_id
  -> Worker 消费 Run
  -> 创建 Sandbox
  -> Agent 调模型
  -> 模型决定调用工具
  -> 工具在统一协议下执行
  -> 结果写回 Agent 上下文
  -> 产生 Artifact
  -> Worker 广播事件
  -> Backend WebSocket 转发
  -> Frontend 实时展示
```

## 8.2 目标文件/RAG链

```text
Frontend 上传项目文件
  -> Backend 存储文件
  -> Backend / Worker 触发文档索引
  -> DocumentChunk 入库
  -> 后续 TaskRun 执行时按 goal 检索相关 chunk
  -> 检索结果进入 Agent system prompt / context
```

---

## 9. 结论

当前项目距离目标架构 **不是缺模块，而是缺收口**。

更具体地说：

- 前端缺页面挂载
- 后端缺状态演进逻辑和部分 API 收尾
- worker 缺统一协议与事件闭环
- RAG 缺接线

因此最合理的后续策略不是“大重写”，而是：

1. 保留现有模块边界
2. 优先统一 worker 协议
3. 再打通 Run 执行闭环
4. 最后补前端页面和 RAG/Artifact 增强能力
