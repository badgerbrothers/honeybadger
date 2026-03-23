# Badgers 模块全景讲解与面试问答手册

> 版本：v1.0（完整版）  
> 更新日期：2026-03-23  
> 代码基线：`services/* + worker/* + frontend/* + nginx + docker-compose.yml`

---

## 0. 先看全局：系统到底怎么跑

Badgers 当前是“单仓库 + 多服务 + 双 worker + 网关”的形态，真实运行入口不是 legacy `backend/`，而是 `docker-compose.yml` 里定义的服务。

### 0.1 对外入口与内部服务

- 浏览器只需要访问：
  - `http://localhost`（nginx 网关）
  - `http://localhost:3000`（前端开发服务）
- 网关再把 `/api/*` 按前缀转发到不同服务：
  - `project-service`
  - `task-service`
  - `rag-service`
  - `storage-service`
  - `auth-service`

### 0.2 两条核心业务链

1. 任务执行链（TaskRun）
- 前端创建 task/run
- `task-service` 发布 `task-runs` 队列消息
- `worker-taskrun` 消费并执行
- worker 回传 run 事件到 `task-service`
- `task-service` 通过 WebSocket 推流给前端

2. 知识索引链（IndexJob / RAG）
- 上传项目文件或 RAG 文件
- `project-service`/`rag-service` 创建索引任务
- 发布 `index-jobs` 队列消息
- `worker-indexjob` 消费并执行切分、向量化、入库

### 0.3 关键状态机（必须背）

- `Task.queue_status`: `scheduled -> queued -> in_progress -> done`
- `TaskRun.status`: `pending -> running -> completed/failed/cancelled`
- `DocumentIndexJob.status`: `pending -> running -> completed/failed`

---

## 1. 模块一：`docker-compose + 基础设施`

### 1.1 职责

`docker-compose.yml` 负责把整个系统拉起来，既包含业务服务，也包含中间件。

当前编排的基础设施：
- PostgreSQL（含 pgvector）
- Redis
- RabbitMQ
- MinIO

### 1.2 你要掌握的知识点

- 容器启动顺序和健康检查不是一回事
- `depends_on.condition: service_healthy` 需要配合 `healthcheck`
- 容器内地址（`task-service:8000`）与宿主机地址（`localhost:8002`）的区别
- 环境变量分层：`.env` -> compose -> service config
- volume 挂载对开发效率和一致性的影响

### 1.3 对应代码入口

- `/docker-compose.yml`
- `/.env.example`
- `/README.md`

### 1.4 结合本项目的重点

- `worker-taskrun` 和 `worker-indexjob` 都挂了队列配置与 DB/S3 配置
- `worker-taskrun` 还挂载了 docker sock，用于创建沙箱容器
- 前端通过 `NEXT_PUBLIC_API_URL=http://localhost/api` 与网关通信

### 1.5 常见故障

- 某服务“能启动但不可用”：通常是健康检查命令不对
- 服务间地址写成 `localhost`：容器内应改成服务名
- RabbitMQ 未 ready 导致服务启动即报错：看 queue connect retry

---

## 2. 模块二：`nginx API 网关`

### 2.1 职责

- 统一入口
- 路由分发
- 处理跨域头
- 处理 WebSocket 升级

### 2.2 你要掌握的知识点

- 反向代理与 upstream
- hop-by-hop 头（`Upgrade`、`Connection`）为什么要显式透传
- WebSocket 代理超时和连接保活
- 预检请求（`OPTIONS`）统一处理

### 2.3 对应代码入口

- `/nginx/nginx.conf`

### 2.4 结合本项目的重点

- `/api/runs` 这组路由开启了 WebSocket 升级配置
- `map $http_upgrade $connection_upgrade` 是标准写法
- 网关是“系统边界”，前端不直接打内部服务

### 2.5 常见故障

- WebSocket 一直 400/426：一般是没带 `Upgrade/Connection`
- 长连接断开：`proxy_read_timeout` 太短
- CORS 预检失败：`OPTIONS` 未放行或 header 白名单不匹配

---

## 3. 模块三：`auth-service`（Spring Boot）

### 3.1 职责

- 用户注册/登录
- access token + refresh token
- 注销与会话刷新
- `users/me` 鉴权信息

### 3.2 你要掌握的知识点

- Spring Security Filter Chain
- 无状态认证（JWT）
- `SessionCreationPolicy.STATELESS`
- Refresh Token 持久化与吊销
- 密码哈希（Argon2）

### 3.3 对应代码入口

- `/services/auth-service/src/main/java/com/badgers/auth/config/SecurityConfig.java`
- `/services/auth-service/src/main/java/com/badgers/auth/controller/AuthController.java`
- `/services/auth-service/src/main/java/com/badgers/auth/service/JwtService.java`
- `/services/auth-service/src/main/resources/application.yml`
- `/services/auth-service/src/main/resources/db/migration/V1__create_auth_tables.sql`

### 3.4 结合本项目的重点

- `SecurityConfig` 放行了 `/api/auth/*` 相关端点
- 密码编码器用 `Argon2PasswordEncoder.defaultsForSpringSecurity_v5_8()`
- JWT 参数（issuer/audience/secret）通过环境变量注入

### 3.5 常见故障

- 401 但 token 看似合法：`aud` 或 `iss` 不匹配
- refresh 失败：refresh token 过期/被吊销
- 启动失败：Flyway 与数据库版本或连接配置冲突

---

## 4. 模块四：`project-service`

### 4.1 职责

- 项目 CRUD
- 会话 CRUD
- 项目文件上传/删除
- 项目与 RAG collection 绑定

### 4.2 你要掌握的知识点

- FastAPI Router + Depends
- owner_user_id 多租户隔离
- 服务间调用（HTTP client）
- 文件元数据入库与对象存储分离
- 上传后触发索引任务（经 rag-service）

### 4.3 对应代码入口

- `/services/project-service/app/main.py`
- `/services/project-service/app/routers/projects.py`
- `/services/project-service/app/routers/conversations.py`
- `/services/project-service/app/routers/project_rag.py`
- `/services/project-service/app/security/auth.py`
- `/services/project-service/app/services/storage.py`
- `/services/project-service/app/services/rag_client.py`

### 4.4 结合本项目的重点

- 上传文件限制：大小 50MB、扩展名白名单
- 若项目绑定了 `active_rag_collection_id`，上传后会调度索引
- 全部查询都按 `owner_user_id` 做过滤

### 4.5 常见故障

- 文件上传成功但检索不到：项目未绑定 RAG collection
- 404 project not found：token 用户与资源 owner 不一致
- 文件存在 DB 不存在对象：中间步骤失败导致不一致，需要补偿

---

## 5. 模块五：`task-service`

### 5.1 职责

- 任务/运行/产物管理
- 发布任务到 RabbitMQ
- 接收 worker 事件并推送前端
- 定时器推进任务队列状态

### 5.2 你要掌握的知识点

- QueueStatus 与 RunStatus 的双状态系统
- 任务发布失败回滚策略
- WebSocket 广播器管理连接集合
- 内部服务 token 鉴权（machine-to-machine）
- APScheduler 周期任务

### 5.3 对应代码入口

- `/services/task-service/app/main.py`
- `/services/task-service/app/models/task.py`
- `/services/task-service/app/routers/tasks.py`
- `/services/task-service/app/routers/runs.py`
- `/services/task-service/app/routers/artifacts.py`
- `/services/task-service/app/services/queue_service.py`
- `/services/task-service/app/services/task_scheduler.py`
- `/services/task-service/app/services/event_broadcaster.py`
- `/services/task-service/app/security/auth.py`

### 5.4 结合本项目的重点

- `create_task_run` 会先落库 run，再 publish 消息
- publish 失败时 run 会置为 failed，避免“僵尸 pending”
- worker 上报事件接口 `/api/runs/{run_id}/events` 只接受内部 token
- 前端订阅 `/api/runs/{run_id}/stream?token=...`

### 5.5 常见故障

- 前端 run 卡 pending：队列没发布成功或 worker 未消费
- stream 无事件：token 不合法、run ownership 校验失败、WS 路由被代理错
- 任务重复执行：重试策略与幂等设计没处理好

---

## 6. 模块六：`worker`（taskrun/indexjob）

### 6.1 职责

- 消费 `task-runs`，执行 agent + tool + sandbox
- 消费 `index-jobs`，执行文档解析与向量化
- 回传运行事件
- 自动上传产物

### 6.2 你要掌握的知识点

- RabbitMQ ack/nack/reject 语义
- prefetch 与并发控制
- Agent ReAct 循环
- 模型路由（OpenAI/Anthropic）
- Docker 沙箱生命周期
- 事件与日志一致性

### 6.3 对应代码入口

- `/worker/worker_taskrun.py`
- `/worker/worker_indexjob.py`
- `/worker/queueing/rabbitmq_client.py`
- `/worker/main.py`
- `/worker/orchestrator/agent.py`
- `/worker/models/factory.py`
- `/worker/services/backend_client.py`
- `/worker/sandbox/manager.py`

### 6.4 结合本项目的重点

- payload 格式：taskrun 取 `task_run_id`，indexjob 取 `job_id`
- payload 缺字段会 `reject(requeue=False)`，避免死循环
- 执行异常会 `nack(requeue=True)`，让消息重试
- tool 产物会通过 task-service 的内部接口上传

### 6.5 常见故障

- 一直重试同一消息：业务异常导致 nack + requeue 循环
- 沙箱创建失败：镜像不存在、docker sock 权限问题
- run 事件丢失：回传接口不可达或内部 token 错误

---

## 7. 模块七：`rag-service`

### 7.1 职责

- RAG collection CRUD
- RAG 文件上传
- 索引任务调度
- 检索接口（向量、混合检索、重排、query rewrite）

### 7.2 你要掌握的知识点

- collection 与 file 的数据建模
- index job 与 chunk 的生命周期
- 向量检索与阈值过滤
- hybrid 检索 + reranker + query rewrite 组合
- 与 worker 的异步解耦

### 7.3 对应代码入口

- `/services/rag-service/app/main.py`
- `/services/rag-service/app/routers/rag_collections.py`
- `/services/rag-service/app/routers/rag.py`
- `/services/rag-service/app/services/rag_service.py`
- `/services/rag-service/app/services/queue_service.py`
- `/services/rag-service/app/models/document_index_job.py`
- `/services/rag-service/app/models/rag_collection.py`

### 7.4 结合本项目的重点

- project 维度索引与 global RAG collection 索引都走 `DocumentIndexJob`
- 检索默认可开关 `use_hybrid/use_reranker/use_query_rewrite`
- 索引消息发布失败时会把 job 标记为 failed

### 7.5 常见故障

- 上传成功但状态一直 pending：index worker 没消费到 `index-jobs`
- 命中率低：chunk 参数、embedding 模型、threshold 未调优
- 检索慢：索引策略与数据库资源不匹配

---

## 8. 模块八：`storage-service`

### 8.1 职责

- 作为 MinIO 的 HTTP 代理层
- 提供统一上传/下载/删除/复制 API
- 统一 object 命名和 bucket 访问

### 8.2 你要掌握的知识点

- S3 兼容接口思想
- 对象存储路径设计
- 内容类型与流式返回
- “元数据在 DB，二进制在对象存储”的分层设计

### 8.3 对应代码入口

- `/services/storage-service/app/main.py`
- `/services/project-service/app/services/storage.py`
- `/services/task-service/app/services/storage.py`

### 8.4 结合本项目的重点

- 上传由业务服务代理调用 storage-service，而不是直连 MinIO
- artifact 保存到项目是“对象复制”而非二次上传
- 下载统一走 artifact API，前端感知不到底层对象存储细节

### 8.5 常见故障

- 404 object not found：DB 记录路径和对象实际路径不一致
- bucket 不存在：首次写入前 bucket check/create 失败
- 大文件超时：服务端/代理层 timeout 配置不足

---

## 9. 模块九：`frontend`（Next.js + React Query）

### 9.1 职责

- 登录/注册与 token 生命周期管理
- 项目/会话/任务/运行 UI
- 上传文件、发消息、创建任务、查看 run stream
- artifact 下载

### 9.2 你要掌握的知识点

- Next.js App Router 路由组织
- Client Component 与状态边界
- React Query 缓存与失效
- AuthContext（access/refresh）
- WebSocket 客户端重连与心跳

### 9.3 对应代码入口

- `/frontend/src/lib/auth/AuthContext.tsx`
- `/frontend/src/lib/auth/RequireAuth.tsx`
- `/frontend/src/lib/api/client.ts`
- `/frontend/src/lib/api/endpoints.ts`
- `/frontend/src/features/workspace/WorkspaceContext.tsx`
- `/frontend/src/lib/ws/runStream.ts`
- `/frontend/src/app/(workspace)/conversation/page.tsx`
- `/frontend/src/app/(workspace)/dashboard/page.tsx`
- `/frontend/src/app/(workspace)/runs/[runId]/page.tsx`

### 9.4 结合本项目的重点

- `apiFetch` 遇到 401 会自动触发 refresh 再重试一次
- `WorkspaceContext.sendMessage` 会串行做：创建 message -> 创建 task -> 创建 run
- run 页面把历史 logs 与实时 stream 事件合并展示

### 9.5 常见故障

- 一直跳登录页：refresh 失败后被 `router.replace('/login')`
- 数据不刷新：query key 设计或 invalidate 时机错误
- WS 连接秒断：token 过期或网关 WS 转发异常

---

## 10. 模块十：`shared + legacy backend`

### 10.1 职责

- `shared/`：跨服务复用的数据结构与模型（迁移过程中）
- `backend/`：历史单体代码，当前 compose 不作为主运行面

### 10.2 你要掌握的知识点

- 迁移期“并存代码”识别方法
- 如何避免误改 legacy 入口
- 共享模型的版本演进与兼容

### 10.3 对应代码入口

- `/shared/*`
- `/backend/app/main.py`
- `/README.md`（关于 legacy backend 的说明）

### 10.4 结合本项目的重点

- 开发主线应优先 `services/*`、`worker/*`、`frontend/*`
- 若修改 legacy backend，需要明确是兼容目标还是历史清理目标

---

## 11. 模块十一：测试与质量保障（建议单独强化）

### 11.1 测试分层

- 单元/契约测试：关注 API 行为与边界
- 集成测试：关注数据库、队列、存储联动
- 端到端联调：关注用户路径（创建项目->发消息->run->artifact）

### 11.2 对应代码入口

- `/docs/testing-guidelines.md`
- `/backend/tests/*`（历史但测试覆盖较全）
- `/worker/tests/*`
- `/services/*/tests/*`
- `/frontend/vitest.config.ts`

### 11.3 结合本项目的重点

- Worker 测试数量最多，适合作为系统行为回归基线
- 服务拆分后，建议补“跨服务契约测试”，避免 schema 漂移
- 对 run stream 与 artifact 流转应有集成测试覆盖

---

## 12. 面试问答模块（八股 + 本项目实战）

> 说明：本章按“面试官会怎么问”组织。每题都给“标准答 + 本项目落地 + 追问方向”。

### A. 容器与编排

**Q1：`depends_on` 能保证依赖服务可用吗？**  
A：短语法只能保证“先启动”，不保证“业务已 ready”；要保证 ready，需要 `healthcheck + condition: service_healthy`。  
结合本项目：`docker-compose.yml` 多个服务都用了 `service_healthy` 条件。  
追问：如果健康检查写得太宽松会怎样？

**Q2：容器间为什么不用 `localhost` 通信？**  
A：容器内 `localhost` 指向自己，不是其它服务；应使用 compose service name。  
结合本项目：`task-service` 在 worker 里使用 `http://task-service:8000`。  
追问：宿主机访问为什么又用 `localhost:8002`？

**Q3：健康检查和重启策略的关系？**  
A：健康检查负责暴露状态，不直接“修复”；修复通常靠 restart 策略或上层编排。  
结合本项目：healthcheck 主要用于启动依赖顺序与可观测性。  
追问：如果健康检查命令依赖数据库，会不会造成连锁失败？

### B. 网关与 WebSocket

**Q4：为什么 Nginx 代理 WebSocket 必须手动传 `Upgrade/Connection`？**  
A：这两个是 hop-by-hop 头，默认不会透传，需显式设置。  
结合本项目：`nginx.conf` 使用了 `proxy_set_header Upgrade $http_upgrade` 与 `Connection $connection_upgrade`。  
追问：为什么还要 `proxy_http_version 1.1`？

**Q5：WebSocket 为什么常在 60 秒左右断开？**  
A：常见是代理 `proxy_read_timeout` 默认值触发。  
结合本项目：run stream 依赖长连接，应按业务调大超时或使用 ping/pong。  
追问：客户端如何做心跳与断线重连？

### C. 鉴权与 JWT

**Q6：JWT 里 `exp`、`nbf`、`iat` 分别是什么？**  
A：`exp` 到期时间，`nbf` 生效前不可用，`iat` 签发时间。校验时应考虑少量时钟偏移。  
结合本项目：Python 微服务统一在 `security/auth.py` 校验 token。  
追问：为什么只验签不够，还要验 `aud`/`iss`？

**Q7：JWT 安全实践最容易踩什么坑？**  
A：算法混淆、弱密钥、未校验 audience/issuer、把不可信 claim 当可信事实。  
结合本项目：服务端要求 `jwt_secret + issuer + audience`。  
追问：refresh token 与 access token 的风险差异？

**Q8：Spring Security 里 `STATELESS` 的意义？**  
A：不创建、不使用 HttpSession 获取 SecurityContext，典型用于 token 鉴权。  
结合本项目：`auth-service` 的 `sessionCreationPolicy(STATELESS)`。  
追问：那 refresh 会话信息存哪？

**Q9：为什么密码哈希常用 Argon2？**  
A：抗暴力破解能力更强，内存成本高，属于自适应单向函数。  
结合本项目：`Argon2PasswordEncoder.defaultsForSpringSecurity_v5_8()`。  
追问：线上参数如何调优（延迟与安全平衡）？

### D. FastAPI 与服务设计

**Q10：FastAPI 的 `Depends` 在 WebSocket 里也能用吗？**  
A：可以，WebSocket 端点同样支持 `Depends/Security/Header/Query` 等依赖机制。  
结合本项目：run stream 使用 token 校验模式（query 参数）。  
追问：为什么 WebSocket 场景通常抛 `WebSocketException` 而不是 `HTTPException`？

**Q11：`@app.on_event('startup')` 现在还推荐吗？**  
A：FastAPI 官方更推荐 `lifespan`，`on_event` 是可用但偏旧方式。  
结合本项目：当前服务仍广泛用 startup/shutdown 做 DB 与 queue 初始化。  
追问：迁移到 lifespan 时要注意什么？

**Q12：为什么要分 project-service/task-service/rag-service？**  
A：按领域拆分，降低单服务复杂度，隔离故障域，便于独立扩展。  
结合本项目：任务执行与索引执行已异步化，队列解耦明显。  
追问：拆分后如何避免接口契约漂移？

### E. RabbitMQ 与任务系统

**Q13：`ack`、`nack`、`reject` 有什么区别？**  
A：`ack` 确认成功可删除；`nack/reject` 是否 requeue 决定重投还是丢弃/死信。  
结合本项目：payload 错误 `reject(requeue=False)`，执行异常 `nack(requeue=True)`。  
追问：什么时候需要 DLQ？

**Q14：`prefetch_count` 有什么用？**  
A：限制未确认消息数，防止消费者被压垮，影响吞吐与公平分发。  
结合本项目：worker channel 设置 `prefetch_count=1`，偏“稳态串行”。  
追问：吞吐上不去时如何调参？

**Q15：为什么发布任务要“先落库再发消息”？**  
A：保证可追踪性与失败补偿；发失败可把 run 标记 failed。  
结合本项目：`create_task_run` 失败会回写 `queue_publish_failed`。  
追问：如何做到更强一致（outbox）？

**Q16：消费者幂等为什么重要？**  
A：消息可能重复投递，业务处理必须可重复执行而不破坏状态。  
结合本项目：TaskRun 状态机与 current_run_id 能做一定防重，但还可继续加强。  
追问：你会如何设计幂等键？

### F. Worker / Agent / Sandbox

**Q17：为什么要 Docker 沙箱执行工具调用？**  
A：隔离风险、限制资源、减少对宿主环境污染。  
结合本项目：worker 为每个 run 创建 sandbox 容器，结束后销毁。  
追问：如果沙箱超时或崩溃，如何回收？

**Q18：Agent 主循环一般怎么停？**  
A：工具调用耗尽或模型返回 stop；同时设置 max iterations 防止死循环。  
结合本项目：`max_iterations=20`。  
追问：如何给模型“更可控”的工具调用边界？

**Q19：为什么要把运行事件落库再推送？**  
A：WebSocket 是瞬时链路，落库保证可追溯和断线补读。  
结合本项目：run logs 持久化后再 broadcaster fan-out。  
追问：高并发时日志 JSON 字段会有什么问题？

### G. RAG 与向量检索

**Q20：RAG 的核心链路是什么？**  
A：文档解析 -> chunk -> embedding -> 向量检索 -> 上下文注入。  
结合本项目：index worker 消费 `index-jobs`，查询时支持 hybrid/reranker/rewrite。  
追问：为什么检索要阈值过滤？

**Q21：pgvector 常见距离函数与索引策略？**  
A：常用 cosine/L2，索引可用 HNSW/IVFFlat，不同场景做召回-延迟权衡。  
结合本项目：代码采用 cosine 相似度公式并可扩展索引类型。  
追问：何时需要重排模型（reranker）？

**Q22：为什么要把索引任务异步化？**  
A：索引耗时高，若同步执行会阻塞用户请求，影响接口 SLA。  
结合本项目：上传后只创建 job，实际索引由 worker 异步完成。  
追问：如何向用户展示索引进度？

### H. 对象存储与产物管理

**Q23：为什么 artifact 不直接存数据库 BLOB？**  
A：大文件更适合对象存储，DB 存元数据即可，扩展与成本更优。  
结合本项目：artifact 元数据在 task-service，二进制在 MinIO。  
追问：删除元数据成功但删除对象失败怎么办？

**Q24：`copy_object` 的价值是什么？**  
A：对象服务端复制，避免客户端二次下载上传，节省带宽与时间。  
结合本项目：`save-to-project` 就是把 run artifact 复制到项目目录。  
追问：跨 bucket/跨 region 复制怎么做？

### I. 前端工程与状态管理

**Q25：React Query 的 `staleTime` 是什么？**  
A：数据“新鲜期”；在 staleTime 内通常不会自动 refetch。  
结合本项目：Provider 中把 staleTime 设为 5 秒，平衡实时性与请求量。  
追问：为什么 mutation 后要 `invalidateQueries`？

**Q26：React Query 默认失败重试策略是什么？**  
A：默认失败重试 3 次并指数退避。  
结合本项目：项目里 mutation retry=0，query retry=1，做了定制。  
追问：哪些接口不应该自动重试？

**Q27：Next.js App Router 的关键特性？**  
A：文件系统路由、layout 嵌套、默认 Server Components。  
结合本项目：按 `(workspace)/(auth)` 分区路由，layout 做统一壳层。  
追问：哪些组件必须 `use client`？

**Q28：为什么 run 详情页要“历史日志 + 实时流”合并？**  
A：确保断线重连/刷新后仍能看到完整事件链。  
结合本项目：`initialLogs + streamEvents` merge。  
追问：如何做事件去重？

### J. 测试与质量

**Q29：单测、契约测、集成测怎么分？**  
A：单测测函数与边界；契约测测接口输入输出；集成测测跨组件联动。  
结合本项目：worker 测试较多，跨服务契约仍可继续补强。  
追问：队列与对象存储如何做可重复测试？

**Q30：为什么说“可观测性”也是面试重点？**  
A：分布式系统没有可观测性就没有可维护性。日志、事件、状态机必须可追踪。  
结合本项目：run logs、index job 状态、healthcheck 都是可观测入口。  
追问：你会先加 metrics 还是 tracing？

---

## 13. 这份手册如何用于面试准备

建议按三轮复习：

1. 第一轮（系统图）
- 能口述两条核心链路
- 能说清每个服务边界与数据流向

2. 第二轮（深挖）
- 熟悉每个模块的关键文件
- 每个模块至少准备 3 个故障案例

3. 第三轮（八股 + 实战）
- 按第 12 章做问答演练
- 每题要能落到“本项目是怎么做的”

---

## 14. WebSearch 参考依据（官方优先）

> 检索时间：2026-03-23。以下来源用于本手册“八股问答”与概念校准。

### 基础设施 / 网关

- [W1] Docker Compose `services` / `depends_on`：  
  https://docs.docker.com/reference/compose-file/services/
- [W2] NGINX WebSocket proxying：  
  https://nginx.org/en/docs/http/websocket.html

### 消息队列 / 消费语义

- [W3] RabbitMQ Consumer Acknowledgements & Publisher Confirms：  
  https://www.rabbitmq.com/docs/confirms
- [W4] RabbitMQ Consumer Prefetch：  
  https://www.rabbitmq.com/docs/consumer-prefetch

### FastAPI / Python 服务

- [W5] FastAPI WebSockets（含 Depends）：  
  https://fastapi.tiangolo.com/advanced/websockets/
- [W6] FastAPI Lifespan Events：  
  https://fastapi.tiangolo.com/advanced/events/
- [W7] FastAPI CORS（中文）：  
  https://fastapi.tiangolo.com/zh/tutorial/cors/
- [W8] SQLAlchemy AsyncIO / async_sessionmaker：  
  https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- [W9] APScheduler Interval Trigger：  
  https://apscheduler.readthedocs.io/en/latest/modules/triggers/interval.html
- [W10] APScheduler Base Scheduler / add_job：  
  https://apscheduler.readthedocs.io/en/3.x/modules/schedulers/base.html
- [W11] aio-pika 总览（robust reconnect 等）：  
  https://docs.aio-pika.com/

### 安全与认证

- [W12] Spring Security Architecture（FilterChain）：  
  https://docs.spring.io/spring-security/reference/servlet/architecture.html
- [W13] Spring Security `authorizeHttpRequests`：  
  https://docs.spring.io/spring-security/reference/servlet/authorization/authorize-http-requests.html
- [W14] Spring Security Session Management（含 STATELESS 示例）：  
  https://docs.spring.io/spring-security/reference/servlet/authentication/session-management.html
- [W15] Spring Security Password Storage / Argon2：  
  https://docs.spring.io/spring-security/reference/features/authentication/password-storage.html
- [W16] SessionCreationPolicy API（STATELESS 定义）：  
  https://docs.spring.io/spring-security/site/docs/4.0.x/apidocs/org/springframework/security/config/http/SessionCreationPolicy.html
- [W17] RFC 7519（JWT）：  
  https://www.rfc-editor.org/rfc/rfc7519
- [W18] RFC 8725（JWT BCP）：  
  https://www.rfc-editor.org/rfc/rfc8725.pdf

### 前端与数据层

- [W19] Next.js App Router Glossary：  
  https://nextjs.org/docs/app/glossary
- [W20] TanStack Query Important Defaults：  
  https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults

### 向量与对象存储

- [W21] pgvector（`CREATE EXTENSION vector`、距离函数、索引 ops）：  
  https://github.com/pgvector/pgvector
- [W22] MinIO SDKs / Python API reference 索引页：  
  https://docs.min.io/enterprise/aistor-object-store/developers/sdk/

---

## 15. 下一步（建议）

如果你继续按“一个一个来”，推荐从这三节先开讲：

1. 模块 5（task-service）+ 模块 6（worker）联动
2. 模块 3（auth-service）和前端 AuthContext 的 token 刷新链
3. 模块 7（rag-service）索引与检索参数调优

我可以下一步直接给你“模块 5 的逐函数讲解版（带调用时序图）”。
