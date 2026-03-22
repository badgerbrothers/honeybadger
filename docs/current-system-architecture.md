# Badgers MVP 当前系统架构（以代码为准）

本文档描述的是仓库 **当前代码与 `docker-compose.yml` 的实际运行形态**（以 `master` 工作区为准）。如与历史 PRD/旧文档冲突，以代码与 compose 配置为准。

## 1. 总览

系统是单仓多服务（domain-split microservices）：

- **Frontend**: Next.js (`frontend/`)
- **API Gateway**: Nginx (`nginx/`) 对外唯一入口 `http://localhost`
- **Auth Service**: Spring Boot JWT 认证 (`services/auth-service/`)
- **Project Service**: 项目/会话等资源 (`services/project-service/`)
- **Task Service**: 任务/运行/产物 + 运行事件 WebSocket (`services/task-service/`)
- **RAG Service**: RAG collection + 检索 + 索引作业调度 (`services/rag-service/`)
- **Storage Service**: MinIO/S3 对象存储代理 (`services/storage-service/`)
- **Workers**: RabbitMQ 消费者，负责实际执行（Docker sandbox）与索引 (`worker/`)

基础设施依赖：

- PostgreSQL + pgvector（数据与向量）
- MinIO（S3 兼容对象存储）
- RabbitMQ（任务/索引作业队列）
- Redis（仍在 compose 中，更多作为缓存/预留能力；队列基线是 RabbitMQ）

## 2. Compose 实际启动形态

当前 [docker-compose.yml](/F:/Programs/project_4/docker-compose.yml) 会启动完整链路（非仅 infra）：

- `postgres`, `redis`, `minio`, `rabbitmq`
- `auth-service`
- `project-service`, `task-service`, `rag-service`, `storage-service`
- `api-gateway`
- `worker-taskrun`, `worker-indexjob`
- `frontend`

常用端口（以 compose 为准）：

- Gateway: `80`
- Frontend: `3000`
- Auth service: `8080`
- Project service: `8001`
- Task service: `8002`
- RAG service: `8003`
- Storage service: `8005`
- Postgres: `5432`
- Redis: `6379`
- RabbitMQ: `5672`, 管理台 `15672`
- MinIO: `9000`, Console `9001`

## 3. 关键调用链（以当前实现为准）

### 3.1 对外请求流

```
Browser -> Next.js frontend
  -> http://localhost/api/* (nginx gateway)
     -> auth-service / project-service / task-service / rag-service / storage-service
```

### 3.2 TaskRun 执行链（RabbitMQ 基线）

```
task-service 创建/调度 run
  -> publish 到 RabbitMQ 队列 task-runs
worker-taskrun 消费 task-runs
  -> 创建每次 run 的 Docker sandbox
  -> 执行 agent/tools
  -> POST /api/runs/{run_id}/events 上报事件到 task-service
task-service
  -> WS /api/runs/{run_id}/stream 将事件 fan-out 给前端
```

### 3.3 RAG 索引链

```
rag-service: RAG collection CRUD + 文件上传
  -> 上传成功后调度 indexing job（写入 DB，并 publish 到 RabbitMQ index-jobs）
worker-indexjob 消费 index-jobs
  -> 拉取文件（MinIO/S3）
  -> chunk + embedding + 写入 pgvector
```

## 4. 代码边界与“遗留/兼容”说明

- 仓库仍包含 `backend/`（旧的单体 FastAPI 结构），但 compose/runtime baseline 以 `services/*` 为主。
- `worker/main.py` 里仍保留了“轮询 DB”的主循环实现，但 compose 运行的 worker 入口是 RabbitMQ 模式（`worker/worker_taskrun.py`、`worker/worker_indexjob.py`）。

## 5. 推荐阅读顺序（快速定位真实入口）

1. [docker-compose.yml](/F:/Programs/project_4/docker-compose.yml)
2. [README.md](/F:/Programs/project_4/README.md)
3. `nginx/nginx.conf`（gateway 路由）
4. `services/*/app/main.py`（各服务入口）
5. `worker/worker_taskrun.py`、`worker/worker_indexjob.py`（worker 入口）

