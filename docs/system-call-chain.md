# Badgers MVP 系统调用链详解

本文档详细说明 Badgers MVP 从用户操作到任务完成的完整调用链，涵盖前端、后端、Worker、沙箱的每一个环节。

## 目录

1. [创建项目流程](#1-创建项目流程)
2. [上传文件流程](#2-上传文件流程)
3. [创建对话流程](#3-创建对话流程)
4. [发送消息创建任务](#4-发送消息创建任务)
5. [Worker 执行任务](#5-worker-执行任务)
6. [Agent 执行循环](#6-agent-执行循环)
7. [LLM 调用详细过程](#7-llm-调用详细过程)
8. [工具执行详细过程](#8-工具执行详细过程)
9. [后续迭代示例](#9-后续迭代示例)
10. [文件写入和 Artifact 创建](#10-文件写入和-artifact-创建)
11. [任务完成](#11-任务完成)
12. [前端接收实时更新](#12-前端接收实时更新)
13. [下载 Artifact](#13-下载-artifact)
14. [完整调用链总结](#14-完整调用链总结)

---

## 1. 创建项目流程

```
前端 (CreateProjectForm.tsx)
  ↓ 用户填写表单，点击创建
  ↓ useCreateProject hook
  ↓ POST /api/projects

后端 (backend/app/routers/projects.py)
  ↓ create_project(project: ProjectCreate)
  ↓ Project(**project.model_dump())
  ↓ db.add(db_project)
  ↓ db.commit()
  ↓ 返回 ProjectResponse

前端
  ↓ TanStack Query 缓存更新
  ↓ 页面显示新项目
```

## 2. 上传文件流程

```
前端 (FileUploadZone.tsx)
  ↓ 用户拖拽文件
  ↓ useUploadFile hook
  ↓ POST /api/projects/{id}/files (multipart/form-data)

后端 (backend/app/routers/projects.py)
  ↓ upload_file(project_id, file: UploadFile)
  ↓ 验证项目存在
  ↓ 读取文件内容
  ↓ storage_service.upload_file() → MinIO
  ↓
  ↓ 触发 RAG 索引
  ↓ rag.indexer.index_document()
  ↓   ↓ parser.parse(file) → 解析文档
  ↓   ↓ chunker.chunk(content) → 分块
  ↓   ↓ embeddings.embed(chunks) → OpenAI API
  ↓   ↓ 保存到 document_chunks 表（pgvector）
  ↓
  ↓ 创建 ProjectFile 记录
  ↓ db.commit()
  ↓ 返回 ProjectFileResponse

前端
  ↓ 文件列表更新
```

## 3. 创建对话流程

```
前端
  ↓ 用户点击"新建对话"
  ↓ POST /api/conversations
  ↓ body: { project_id, title }

后端 (backend/app/routers/conversations.py)
  ↓ create_conversation(conversation: ConversationCreate)
  ↓ Conversation(**conversation.model_dump())
  ↓ db.add(db_conversation)
  ↓ db.commit()
  ↓ 返回 ConversationResponse

前端
  ↓ 跳转到对话页面
```

## 4. 发送消息创建任务

```
前端 (ConversationPage.tsx)
  ↓ 用户输入消息："研究特斯拉 Q4 财报"
  ↓ 点击发送
  ↓
  ↓ Step 1: 保存用户消息
  ↓ POST /api/conversations/{id}/messages
  ↓ body: { role: "user", content: "研究特斯拉 Q4 财报" }

后端 (conversations.py:create_message)
  ↓ Message(conversation_id, role, content)
  ↓ db.add(db_message)
  ↓ db.commit()
  ↓ 返回 MessageResponse

前端
  ↓ Step 2: 创建任务
  ↓ POST /api/tasks
  ↓ body: {
  ↓   conversation_id: uuid,
  ↓   project_id: uuid,
  ↓   goal: "研究特斯拉 Q4 财报",
  ↓   skill: "research_report",
  ↓   model: "gpt-4-turbo-preview"
  ↓ }

后端 (tasks.py:create_task)
  ↓ Task(**task.model_dump())
  ↓ db.add(db_task)
  ↓ db.commit()
  ↓ 返回 TaskResponse { id: task_id }

前端
  ↓ Step 3: 创建任务运行
  ↓ POST /api/tasks/{task_id}/runs

后端 (tasks.py:create_task_run)
  ↓ TaskRun(task_id, status=PENDING)
  ↓ db.add(db_run)
  ↓ db.commit()
  ↓ 返回 TaskRunResponse { id: run_id }
  ↓
  ↓ Step 4: 发送到 Redis 队列
  ↓ redis.lpush("task_queue", run_id)

前端
  ↓ Step 5: 建立 WebSocket 连接
  ↓ WS /api/runs/{run_id}/events
  ↓ 等待实时更新...
```

## 5. Worker 执行任务

```
Worker 进程 (worker/main.py)
  ↓ 监听 Redis 队列
  ↓ run_id = redis.rpop("task_queue")
  ↓
  ↓ 从数据库加载任务信息
  ↓ task_run = db.query(TaskRun).get(run_id)
  ↓ task = task_run.task
  ↓ project = task.project
  ↓
  ↓ Step 1: 创建 Docker 沙箱
  ↓ sandbox_manager.create_sandbox()

worker/sandbox/manager.py
  ↓ docker_backend.create_container()

worker/sandbox/docker_backend.py
  ↓ docker_client.containers.run(
  ↓   image="badgers-sandbox",
  ↓   mem_limit="2g",
  ↓   cpu_quota=200000,
  ↓   network_mode="bridge",
  ↓   detach=True
  ↓ )
  ↓ 返回 container_id

worker/sandbox/manager.py
  ↓ SandboxSession(
  ↓   task_run_id=run_id,
  ↓   container_id=container_id
  ↓ )
  ↓ db.add(sandbox_session)
  ↓ db.commit()
  ↓
  ↓ 发送 WebSocket 事件
  ↓ event_broadcaster.send({
  ↓   type: "sandbox_created",
  ↓   container_id: container_id
  ↓ })
```

## 6. Agent 执行循环

```
worker/orchestrator/agent.py
  ↓ Step 2: 初始化 Agent
  ↓ agent = Agent(
  ↓   task_run_id=run_id,
  ↓   model=model_provider,
  ↓   tools=[browser, python, file, web],
  ↓   skill=skill
  ↓ )
  ↓
  ↓ Step 3: 加载上下文
  ↓
  ↓ 3a. 检索项目文件（RAG）
  ↓ rag.retriever.retrieve(
  ↓   query=task.goal,
  ↓   project_id=project.id,
  ↓   top_k=5
  ↓ )

backend/rag/retriever.py
  ↓ embeddings.embed(query) → OpenAI API
  ↓ query_vector = [0.123, 0.456, ...]
  ↓
  ↓ SELECT * FROM document_chunks
  ↓ ORDER BY embedding <=> query_vector
  ↓ LIMIT 5
  ↓
  ↓ 返回相关文档片段

worker/orchestrator/agent.py
  ↓ 3b. 加载记忆
  ↓ memory_service.get_relevant_memories(
  ↓   project_id=project.id,
  ↓   conversation_id=conversation.id
  ↓ )
  ↓ 返回对话摘要和项目知识
  ↓
  ↓ 3c. 构建系统提示
  ↓ system_prompt = f"""
  ↓ {skill.system_prompt}
  ↓
  ↓ 项目上下文：
  ↓ {rag_context}
  ↓
  ↓ 记忆：
  ↓ {memories}
  ↓
  ↓ 可用工具：
  ↓ {tool_descriptions}
  ↓ """
  ↓
  ↓ Step 4: 开始执行循环
  ↓ agent.run(goal=task.goal, system_prompt=system_prompt)
  ↓
  ↓ messages = [
  ↓   {role: "system", content: system_prompt},
  ↓   {role: "user", content: "研究特斯拉 Q4 财报"}
  ↓ ]
  ↓
  ↓ iteration = 0
  ↓ while iteration < 20:
  ↓   iteration += 1
  ↓
  ↓   发送 WebSocket 事件
  ↓   event_broadcaster.send({
  ↓     type: "iteration_start",
  ↓     iteration: iteration
  ↓   })
  ↓
  ↓   调用 LLM...
```

## 7. LLM 调用详细过程

```
worker/models/router.py
  ↓ model_provider = get_model_provider(
  ↓   model_name="gpt-4-turbo-preview"
  ↓ )

worker/models/openai_provider.py
  ↓ OpenAIProvider.chat_completion()
  ↓
  ↓ 转换消息格式
  ↓ openai_messages = [
  ↓   {"role": "system", "content": "..."},
  ↓   {"role": "user", "content": "研究特斯拉 Q4 财报"}
  ↓ ]
  ↓
  ↓ 转换工具格式
  ↓ openai_tools = [
  ↓   {
  ↓     "type": "function",
  ↓     "function": {
  ↓       "name": "browser.open",
  ↓       "description": "Open a URL in browser",
  ↓       "parameters": {...}
  ↓     }
  ↓   },
  ↓   ...
  ↓ ]
  ↓
  ↓ 调用 OpenAI API
  ↓ response = openai_client.chat.completions.create(
  ↓   model="gpt-4-turbo-preview",
  ↓   messages=openai_messages,
  ↓   tools=openai_tools,
  ↓   temperature=0.7
  ↓ )
  ↓
  ↓ OpenAI API 返回
  ↓ {
  ↓   "choices": [{
  ↓     "message": {
  ↓       "role": "assistant",
  ↓       "content": "我需要搜索特斯拉财报信息",
  ↓       "tool_calls": [{
  ↓         "id": "call_abc123",
  ↓         "type": "function",
  ↓         "function": {
  ↓           "name": "browser.open",
  ↓           "arguments": "{\"url\":\"https://google.com\"}"
  ↓         }
  ↓       }]
  ↓     }
  ↓   }]
  ↓ }
  ↓
  ↓ 转换为内部格式
  ↓ CompletionResponse(
  ↓   content="我需要搜索特斯拉财报信息",
  ↓   tool_calls=[
  ↓     ToolCall(
  ↓       id="call_abc123",
  ↓       name="browser.open",
  ↓       arguments={"url": "https://google.com"}
  ↓     )
  ↓   ]
  ↓ )
```

## 8. 工具执行详细过程

```
worker/orchestrator/agent.py
  ↓ 收到 tool_calls
  ↓
  ↓ 保存 assistant 消息
  ↓ messages.append({
  ↓   role: "assistant",
  ↓   content: "我需要搜索特斯拉财报信息",
  ↓   tool_calls: [...]
  ↓ })
  ↓
  ↓ 发送 WebSocket 事件
  ↓ event_broadcaster.send({
  ↓   type: "tool_call_start",
  ↓   tool: "browser.open",
  ↓   arguments: {"url": "https://google.com"}
  ↓ })
  ↓
  ↓ 执行工具
  ↓ for tool_call in tool_calls:
  ↓   result = await _execute_tool(
  ↓     tool_name="browser.open",
  ↓     arguments={"url": "https://google.com"}
  ↓   )

worker/tools/browser.py
  ↓ BrowserTool.execute(url="https://google.com")
  ↓
  ↓ 在沙箱中执行 Playwright
  ↓ sandbox.exec_run(
  ↓   cmd=["python", "-c", """
  ↓     from playwright.sync_api import sync_playwright
  ↓     with sync_playwright() as p:
  ↓       browser = p.chromium.launch()
  ↓       page = browser.new_page()
  ↓       page.goto('https://google.com')
  ↓       content = page.content()
  ↓       print(content)
  ↓   """]
  ↓ )
  ↓
  ↓ 返回结果
  ↓ ToolResult(
  ↓   success=True,
  ↓   output="<html>...</html>"
  ↓ )

worker/orchestrator/agent.py
  ↓ 发送 WebSocket 事件
  ↓ event_broadcaster.send({
  ↓   type: "tool_call_complete",
  ↓   tool: "browser.open",
  ↓   success: True,
  ↓   output: "<html>...</html>"
  ↓ })
  ↓
  ↓ 保存工具结果到消息历史
  ↓ messages.append({
  ↓   role: "user",
  ↓   content: "Tool browser.open result: <html>...</html>",
  ↓   tool_call_id: "call_abc123"
  ↓ })
  ↓
  ↓ 继续下一次迭代...
```

## 9. 后续迭代示例

```
═══════════════════════════════════
迭代 2: 搜索特斯拉
═══════════════════════════════════

LLM 思考 → 需要在搜索框输入
  ↓ tool_call: browser.type(selector="#search", text="Tesla Q4 2025 earnings")
  ↓ tool_call: browser.click(selector="button[type=submit]")
  ↓ 执行工具 → 返回结果
  ↓ messages.append(tool_results)

═══════════════════════════════════
迭代 3: 打开财报链接
═══════════════════════════════════

LLM 思考 → 找到财报链接
  ↓ tool_call: browser.open(url="https://ir.tesla.com/...")
  ↓ 执行工具 → 返回页面内容

═══════════════════════════════════
迭代 4: 提取关键数据
═══════════════════════════════════

LLM 思考 → 提取营收、利润等数据
  ↓ tool_call: browser.extract(
  ↓   selector=".financial-data",
  ↓   fields=["revenue", "profit", "eps"]
  ↓ )
  ↓ 执行工具 → 返回结构化数据

═══════════════════════════════════
迭代 5: 生成报告
═══════════════════════════════════

LLM 思考 → 整理信息生成报告
  ↓ tool_call: file.write(
  ↓   path="tesla_q4_report.md",
  ↓   content="# 特斯拉 Q4 财报分析\n\n## 摘要\n..."
  ↓ )
```

## 10. 文件写入和 Artifact 创建

```
worker/tools/file.py
  ↓ FileTool.execute(
  ↓   path="tesla_q4_report.md",
  ↓   content="# 特斯拉 Q4 财报..."
  ↓ )
  ↓
  ↓ Step 1: 在沙箱中写入文件
  ↓ sandbox.exec_run(
  ↓   cmd=["sh", "-c", "cat > /workspace/tesla_q4_report.md"],
  ↓   stdin=content
  ↓ )
  ↓
  ↓ Step 2: 从沙箱复制文件
  ↓ file_data = sandbox.get_archive("/workspace/tesla_q4_report.md")
  ↓
  ↓ Step 3: 上传到 MinIO
  ↓ storage_path = f"projects/{project_id}/runs/{run_id}/tesla_q4_report.md"
  ↓ storage_service.upload_file(
  ↓   bucket="badgers-artifacts",
  ↓   path=storage_path,
  ↓   data=file_data
  ↓ )
  ↓
  ↓ Step 4: 创建 Artifact 记录
  ↓ artifact = Artifact(
  ↓   project_id=project_id,
  ↓   task_run_id=run_id,
  ↓   name="tesla_q4_report.md",
  ↓   artifact_type=ArtifactType.REPORT,
  ↓   storage_path=storage_path,
  ↓   size=len(file_data),
  ↓   mime_type="text/markdown"
  ↓ )
  ↓ db.add(artifact)
  ↓ db.commit()
  ↓
  ↓ Step 5: 发送 WebSocket 事件
  ↓ event_broadcaster.send({
  ↓   type: "artifact_created",
  ↓   artifact_id: artifact.id,
  ↓   name: "tesla_q4_report.md",
  ↓   type: "report"
  ↓ })
  ↓
  ↓ 返回 ToolResult(success=True, output="File written")
```

## 11. 任务完成

```
═══════════════════════════════════
迭代 6: 提交最终答案
═══════════════════════════════════

LLM 思考 → 任务完成
  ↓ tool_call: final.answer(
  ↓   result="已完成特斯拉 Q4 财报分析，报告已保存"
  ↓ )
  ↓ 或者 finish_reason="stop"

worker/orchestrator/agent.py
  ↓ 检测到任务完成
  ↓ return final_result

worker/main.py
  ↓ Step 1: 更新 TaskRun 状态
  ↓ task_run.status = TaskStatus.COMPLETED
  ↓ task_run.completed_at = datetime.now()
  ↓ db.commit()
  ↓
  ↓ Step 2: 清理沙箱
  ↓ sandbox_manager.terminate_sandbox(container_id)
  ↓ docker_client.containers.get(container_id).stop()
  ↓ docker_client.containers.get(container_id).remove()
  ↓
  ↓ sandbox_session.terminated_at = datetime.now()
  ↓ db.commit()
  ↓
  ↓ Step 3: 保存对话摘要（记忆系统）
  ↓ memory_service.save_conversation_summary(
  ↓   conversation_id=conversation.id,
  ↓   summary="用户请求分析特斯拉 Q4 财报，Agent 完成研究并生成报告"
  ↓ )
  ↓
  ↓ Step 4: 发送完成事件
  ↓ event_broadcaster.send({
  ↓   type: "task_completed",
  ↓   run_id: run_id,
  ↓   result: final_result,
  ↓   artifacts: [artifact_ids]
  ↓ })
  ↓
  ↓ Step 5: 关闭 WebSocket 连接
  ↓ websocket.close()
```

## 12. 前端接收实时更新

```
前端 (TaskRunViewer.tsx)
  ↓ useTaskRunStream(run_id)
  ↓
  ↓ WebSocket 连接建立
  ↓ ws = new WebSocket(`ws://localhost:8000/api/runs/${run_id}/events`)
  ↓
  ↓ 接收事件流：
  ↓
  ↓ Event 1: { type: "sandbox_created", container_id: "abc123" }
  ↓   → 显示 "沙箱已创建"
  ↓
  ↓ Event 2: { type: "iteration_start", iteration: 1 }
  ↓   → 显示 "迭代 1"
  ↓
  ↓ Event 3: { type: "tool_call_start", tool: "browser.open", ... }
  ↓   → 显示 "正在打开浏览器..."
  ↓
  ↓ Event 4: { type: "tool_call_complete", tool: "browser.open", success: true }
  ↓   → 显示 "✓ 浏览器已打开"
  ↓
  ↓ Event 5: { type: "artifact_created", name: "tesla_q4_report.md" }
  ↓   → 显示 "📄 生成报告: tesla_q4_report.md"
  ↓
  ↓ Event 6: { type: "task_completed", result: "..." }
  ↓   → 显示 "✓ 任务完成"
  ↓   → 显示下载按钮
```

## 13. 下载 Artifact

```
前端
  ↓ 用户点击下载按钮
  ↓ GET /api/artifacts/{artifact_id}/download

后端 (artifacts.py)
  ↓ download_artifact(artifact_id)
  ↓
  ↓ Step 1: 查询 Artifact
  ↓ artifact = db.query(Artifact).get(artifact_id)
  ↓
  ↓ Step 2: 从 MinIO 下载
  ↓ file_data = storage_service.download_file(
  ↓   bucket="badgers-artifacts",
  ↓   path=artifact.storage_path
  ↓ )
  ↓
  ↓ Step 3: 返回文件流
  ↓ return StreamingResponse(
  ↓   content=file_data,
  ↓   media_type=artifact.mime_type,
  ↓   headers={
  ↓     "Content-Disposition": f"attachment; filename={artifact.name}"
  ↓   }
  ↓ )

前端
  ↓ 浏览器触发下载
  ↓ 文件保存到本地
```

## 14. 完整调用链总结

```
用户操作
  ↓
前端 React 组件
  ↓
TanStack Query / API Client
  ↓
FastAPI Backend (HTTP/WebSocket)
  ↓
PostgreSQL (数据持久化)
  ↓
Redis Queue (任务队列)
  ↓
Worker 进程
  ↓
Docker Sandbox Manager
  ↓
Agent Orchestrator
  ↓
Model Provider (OpenAI/Anthropic API)
  ↓
Tool System (Browser/Python/File/Web)
  ↓
Docker Container (隔离执行)
  ↓
MinIO (文件存储)
  ↓
WebSocket (实时事件)
  ↓
前端更新 UI
  ↓
用户看到结果
```

---

## 关键技术点

### 1. 异步处理
- 前端通过 Redis 队列异步提交任务
- Worker 独立进程处理任务
- WebSocket 实时推送进度

### 2. 隔离执行
- 每个 TaskRun 独立的 Docker 容器
- 资源限制（CPU、内存）
- 超时自动终止

### 3. RAG 增强
- 文件上传自动索引到 pgvector
- 任务执行前检索相关上下文
- OpenAI embeddings 向量化

### 4. 记忆系统
- 对话摘要持久化
- 项目知识积累
- 跨会话上下文保持

### 5. 多模型支持
- 统一的 ModelProvider 接口
- 支持 OpenAI、Anthropic
- 工具格式自动转换

### 6. 实时反馈
- WebSocket 双向通信
- 事件驱动架构
- 前端响应式更新

---

**文档版本**: 1.0
**最后更新**: 2026-03-13
**维护者**: Badgers MVP Team
```
