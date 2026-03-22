# PRD: Auth Service + User-Owned Projects/Conversations

## 1. Executive Summary

当前 Badgers 系统已经完成了项目、会话、任务、运行、RAG、Artifact 的微服务化基础能力，但仍缺少用户身份体系和数据隔离能力。系统现状是默认单用户信任模型，无法保证不同用户之间的资源隔离。

本 PRD 定义一个面向 MVP 的用户管理与认证方案：新增独立 `auth-service`（Java 技术栈），通过 JWT 统一身份传递，在现有 `project-service`、`task-service`、`rag-service` 中落地基于资源归属的权限校验。核心归属边界定义为 `projects.owner_user_id`，并通过项目归属向下约束 conversation/task/run/artifact/rag 访问。

MVP 目标是在不重写现有 Python 执行链路的前提下，快速实现可用、可验证、可扩展的多用户隔离能力，并为后续 RBAC、项目协作和企业身份集成打基础。

## 2. Mission

### Mission Statement

为 Badgers 提供安全、清晰、可扩展的用户身份与资源归属体系，确保每个用户只能访问自己的项目和会话。

### Core Principles

- 最小改动原则：优先新增 `auth-service`，避免破坏现有任务执行链路。
- 归属单一事实源：以 `projects.owner_user_id` 作为资源权限根。
- 服务自治验签：各业务服务本地验签，不把每次鉴权都耦合到 auth-service。
- 安全默认值：密码强哈希、短期 access token、可轮换 refresh token。
- 向后兼容迁移：对历史数据做可回填策略，保证升级可执行。

## 3. Target Users

### Primary Personas

- 产品使用者（个人/小团队）
  - 技术水平：中等
  - 诉求：安全地管理自己的项目与会话，不与他人混淆

- 运维/开发者
  - 技术水平：高
  - 诉求：可部署、可观测、可扩展的认证架构，不影响现有 worker 与队列

### Key Pain Points

- 当前没有登录态和用户身份。
- 通过 UUID 可潜在访问非本人资源。
- 无法支持未来多用户协作与权限扩展。

## 4. MVP Scope

### In Scope

#### Core Functionality

- [x] 新增 `auth-service`（Java）提供注册、登录、刷新、登出、当前用户信息。
- [x] JWT access/refresh 双 token 机制。
- [x] `projects.owner_user_id` 归属字段与数据回填。
- [x] `project-service` 按当前用户过滤项目与会话访问。
- [x] `task-service` 和 `rag-service` 按项目归属做权限校验。

#### Technical

- [x] API Gateway 新增 `/api/auth`、`/api/users` 路由。
- [x] 各服务统一 JWT 验签配置（secret/issuer/audience）。
- [x] worker 到 task-service 的内部回调接口增加内部服务令牌校验。

#### Integration

- [x] 前端登录页接入真实登录 API。
- [x] 前端请求带 `Authorization: Bearer <token>`。

#### Deployment

- [x] `docker-compose.yml` 增加 `auth-service` 容器。
- [x] 增加必要环境变量与健康检查。

### Out of Scope

#### Core Functionality

- [ ] 组织/团队/项目成员协作模型（`project_members`）。
- [ ] 细粒度 RBAC/ABAC 权限模型。
- [ ] 多租户计费与配额系统。

#### Integration

- [ ] 第三方身份登录（Google/GitHub/SSO/SAML/OIDC）。
- [ ] MFA/2FA。

#### Deployment

- [ ] 零停机蓝绿认证迁移流程自动化。

## 5. User Stories

1. As a 新用户, I want to 注册账号, so that 我可以拥有独立工作空间。  
   例：输入邮箱和密码后，成功创建用户并返回登录态。

2. As a 用户, I want to 登录并获取 token, so that 我可以访问受保护资源。  
   例：登录成功后进入 dashboard，后续 API 自动带 Bearer Token。

3. As a 用户, I want to 只看到自己的项目列表, so that 我不会看到其他用户数据。  
   例：`GET /api/projects` 仅返回 `owner_user_id = current_user_id`。

4. As a 用户, I want to 在自己的项目下创建会话, so that 我的执行上下文与他人隔离。  
   例：创建 conversation 前先验证 project 归属。

5. As a 用户, I want to 访问 task/run/artifact 时自动鉴权, so that 不会被越权访问。  
   例：非本人 run_id 请求返回 404/403。

6. As a 已登录用户, I want to 无感刷新 token, so that 长会话不频繁中断。  
   例：access token 过期后 refresh 接口换取新 access token。

7. As an 运维, I want to 独立部署 auth-service, so that 认证域与业务域解耦。  
   例：auth-service 故障可独立排查，不影响 DB 结构清晰度。

8. As a worker system, I want to 使用内部服务令牌访问事件接口, so that 不依赖用户态 token。  
   例：worker 上报 run 事件不走用户会话，但仍受服务级安全保护。

## 6. Core Architecture & Patterns

### High-Level Architecture

- `auth-service`（Java）负责身份认证与 token 签发。
- `api-gateway` 将 `/api/auth`、`/api/users` 转发至 auth-service。
- `project-service`、`task-service`、`rag-service` 本地验签并提取 `current_user_id`。
- 所有用户资源访问最终基于 `projects.owner_user_id` 判断归属。

### Data Ownership Pattern

- `users 1 -> n projects`
- `projects 1 -> n conversations`
- `conversations 1 -> n tasks`
- `tasks 1 -> n runs`

权限规则：
- 创建 project：写入 `owner_user_id = current_user_id`
- 创建/读取/修改 conversation/task/run/artifact/rag：必须可追溯到归属项目且 owner 为当前用户

### Directory Pattern (Proposed)

```text
services/
  auth-service/
    app/
      controller/
      service/
      domain/
      repository/
      security/
      config/
```

### Key Design Patterns

- Token-based stateless auth（access token）
- Refresh session persistence（refresh token rotation）
- Resource ownership guard dependency（Python services）
- Internal service token for machine-to-machine endpoints

## 7. Tools/Features

### Feature A: Authentication APIs

- Register
- Login
- Refresh
- Logout
- Me

### Feature B: Ownership Enforcement

- 项目列表/详情默认只返回本人资源
- conversation 创建时验证 project ownership
- task/run/artifact/rag 统一校验链路

### Feature C: Internal Callback Security

- worker 上报事件与 artifact 上传走内部令牌
- 防止匿名外部请求伪造 run 事件

### Feature D: Frontend Session Handling

- 登录后存储 access/refresh（策略见安全章节）
- API 客户端自动附带 Bearer
- 过期后触发 refresh，再失败则登出

## 8. Technology Stack

### Auth Service (New)

- Java 21
- Spring Boot 3.x
- Spring Security 6
- JWT: Nimbus JOSE/JWT 或 JJWT
- Spring Data JPA + PostgreSQL Driver
- Flyway Migration
- Bean Validation
- JUnit 5 + Testcontainers

### Existing Services (Remain)

- Python 3.11 + FastAPI + SQLAlchemy async
- RabbitMQ + Worker (Python)
- Nginx API Gateway
- Next.js Frontend

### Third-Party Integrations

- PostgreSQL（认证与业务表共享或逻辑分域）
- Docker Compose（本地/开发部署）

## 9. Security & Configuration

### Authentication & Authorization

- Access token：短时效（建议 15-30 分钟）
- Refresh token：长时效（建议 7-30 天），支持轮换与撤销
- Password hashing：Argon2id（推荐）或 BCrypt（兼容）
- 服务验签：`issuer`、`audience`、`exp`、`token_type` 必检

### Configuration (Env)

建议新增：

```bash
JWT_SECRET=replace-me
JWT_ALGORITHM=HS256
JWT_ISSUER=badgers-auth
JWT_AUDIENCE=badgers-services
JWT_ACCESS_EXPIRE_MINUTES=30
JWT_REFRESH_EXPIRE_DAYS=7
INTERNAL_SERVICE_TOKEN=replace-me
AUTH_SERVICE_URL=http://auth-service:8080
```

### Security Scope

In scope:
- 用户登录认证
- 资源归属校验
- 内部接口服务令牌保护

Out of scope:
- MFA
- 风险控制/设备指纹
- 审计中心与 SIEM 集成

## 10. API Specification

### Auth Endpoints

#### POST /api/auth/register

Request:

```json
{
  "email": "user@example.com",
  "password": "StrongPassword123!"
}
```

Response `201`:

```json
{
  "user": { "id": "uuid", "email": "user@example.com" },
  "access_token": "jwt",
  "refresh_token": "jwt",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### POST /api/auth/login

Request:

```json
{
  "email": "user@example.com",
  "password": "StrongPassword123!"
}
```

Response `200`: same as register response.

#### POST /api/auth/refresh

Request:

```json
{
  "refresh_token": "jwt"
}
```

Response `200`:

```json
{
  "access_token": "jwt",
  "refresh_token": "jwt",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### POST /api/auth/logout

Request:

```json
{
  "refresh_token": "jwt"
}
```

Response `204`.

#### GET /api/users/me

Header:

```text
Authorization: Bearer <access_token>
```

Response `200`:

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "created_at": "2026-03-20T00:00:00Z"
}
```

### Protected Existing Endpoints (Behavior Update)

- `GET /api/projects` -> only current user's projects
- `POST /api/conversations` -> project must belong to current user
- `POST /api/tasks` -> project/conversation must belong to current user
- `GET /api/runs/{id}` -> run must belong to current user

### Internal Endpoints

- `POST /api/runs/{run_id}/events`
- `POST /api/artifacts/upload`

Required header:

```text
X-Internal-Service-Token: <INTERNAL_SERVICE_TOKEN>
```

## 11. Success Criteria

### MVP Success Definition

系统支持至少两个独立用户并发使用，且任意用户无法访问他人 project/conversation/task/run/artifact/rag 数据。

### Functional Requirements

- [x] 用户可注册/登录/刷新/登出
- [x] 登录后可获取当前用户信息
- [x] 创建项目自动绑定 owner
- [x] 项目和会话列表按 owner 过滤
- [x] task/run/artifact/rag 访问遵循 owner 规则
- [x] worker 回调链路在安全增强后仍可用

### Quality Indicators

- [x] 所有新增关键接口具备自动化测试
- [x] 主要鉴权失败场景返回一致错误码
- [x] 无明显性能回退（P95 增量可控）

### UX Goals

- [x] 登录流程可在 1 分钟内完成
- [x] token 过期刷新对用户透明（成功场景）

## 12. Implementation Phases

### Phase 1: Auth Service Foundation (3-5 days)

Goal: 产出可独立运行的认证服务。

Deliverables:
- [x] auth-service 工程骨架
- [x] users/refresh_tokens 数据模型
- [x] register/login/refresh/logout/me API
- [x] 基础单元测试与集成测试

Validation:
- 登录与刷新链路可跑通
- 失效 token 被拒绝

### Phase 2: Ownership Data Model (2-3 days)

Goal: 引入项目归属主键并完成历史数据兼容。

Deliverables:
- [x] `projects.owner_user_id` 字段与索引
- [x] 用户表及关联迁移
- [x] 历史项目数据回填脚本/迁移逻辑

Validation:
- 迁移可在有存量数据环境执行
- 回滚与重放可用

### Phase 3: Service Authorization Integration (4-6 days)

Goal: 在 project/task/rag 服务中完成资源级鉴权。

Deliverables:
- [x] 统一 JWT 验签依赖
- [x] 项目根归属校验接入所有核心路由
- [x] worker 内部回调令牌校验

Validation:
- 双用户隔离测试通过
- worker 执行链路不回归

### Phase 4: Gateway + Frontend + Hardening (3-4 days)

Goal: 完成端到端用户体验与发布准备。

Deliverables:
- [x] gateway 新路由
- [x] 前端登录态与自动带 token
- [x] 配置文档与运维说明

Validation:
- 本地 compose 全链路验证通过
- 手工 E2E 用例通过

## 13. Future Considerations

- RBAC（admin/editor/viewer）
- 项目分享与成员管理（`project_members`）
- 第三方身份集成（OIDC）
- 审计日志与安全告警
- 令牌黑名单与设备管理

## 14. Risks & Mitigations

1. 风险：迁移和现有 `create_all` 行为冲突  
   缓解：以 Flyway/Alembic 迁移为准，发布前先执行迁移检查。

2. 风险：worker 回调被误拦截导致任务链路中断  
   缓解：区分用户接口和内部接口，内部接口走服务令牌。

3. 风险：前端重构中导致登录态管理重复实现  
   缓解：抽象统一 API client 和 auth store，不散落在页面组件。

4. 风险：JWT 参数（iss/aud/secret）多服务不一致  
   缓解：集中配置模板，启动自检并打印关键校验配置摘要（脱敏）。

5. 风险：权限错误暴露资源存在性  
   缓解：跨用户资源默认返回 404（或统一策略），避免 IDOR 探测信号。

## 15. Appendix

### Related Docs

- `F:\Programs\project_4\.claude\PRD.md`
- `F:\Programs\project_4\README.md`
- `F:\Programs\project_4\.agents\plans\add-auth-service-user-owned-projects-conversations.md`

### Key Existing Files

- `F:\Programs\project_4\services\project-service\app\routers\projects.py`
- `F:\Programs\project_4\services\project-service\app\routers\conversations.py`
- `F:\Programs\project_4\services\task-service\app\routers\tasks.py`
- `F:\Programs\project_4\services\task-service\app\routers\runs.py`
- `F:\Programs\project_4\services\rag-service\app\routers\rag.py`
- `F:\Programs\project_4\worker\services\backend_client.py`
- `F:\Programs\project_4\nginx\nginx.conf`
- `F:\Programs\project_4\docker-compose.yml`

### Assumptions

- 本 PRD 假设 `auth-service` 采用 Java 技术栈，其他现有服务保持 Python。
- 本 PRD 假设短期继续使用共享 PostgreSQL（按服务逻辑分域），后续再评估物理拆库。
- 本 PRD 假设前端当前原型页面会继续演进，认证接入以通用 API 层为主。

